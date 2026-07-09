from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from src.auth.models import User
from src.auth.schemas import UserCreateRequest, CreateTokensRequest, UserInfo
from src.auth.exceptions import (
    EmailAlreadyExistsError,
    UserNotFoundError,
    CodeNotFoundError,
    IncorrectCodeError,
    TooManyVerificationAttemptsError,
    IncorrectPasswordError,
    UserNotVerifiedError,
    InvalidTokenError,
    RefreshTokenRevokedError
)
from src.exceptions import RedisStorageError, DatabaseError
from src.auth.queries import (
    get_user_by_email,
    create_user,
    get_user_by_id,
    get_refresh_tokens,
    get_refresh_token_by_hash
)
from src.auth.redis_helpers import create_verification_keys, create_tokens
from src.auth.email_utils import generate_code
from src.auth.utils import hash_password, verify_password, _DUMMY_HASH
from src.logger import logger
from src.workers.queue import queue


async def register_user_service(
    user_data: UserCreateRequest,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str | int]:
    """Service for registration users."""

    existing_user = await get_user_by_email(user_data.email, db_session)

    if existing_user:
        if existing_user.is_verified:
            raise EmailAlreadyExistsError()
        else:
            try:
                if not verify_password(existing_user.password_hash, user_data.password.get_secret_value()):
                    existing_user.password_hash = hash_password(user_data.password.get_secret_value())
                    await db_session.commit()

                code = generate_code()
                await create_verification_keys(existing_user.id, existing_user.email, code, redis_client)
            except SQLAlchemyError as e:
                await db_session.rollback()
                raise DatabaseError("An occured error with refreshing password in database.") from e
            except RedisError as e:
                raise RedisStorageError("Redis creating verification keys error") from e

            return {"status": "Code was successfully sent.", "user_id": existing_user.id}

    code = generate_code()

    try:
        user = await create_user(user_data, db_session)

        await create_verification_keys(
            user.id,
            user.email,
            code,
            redis_client,
            code_type="verification",
            task_name='send_mail_verification'
        )

        await db_session.commit()
        await db_session.refresh(user)
    except SQLAlchemyError as e:
        await db_session.rollback()
        raise DatabaseError("An occured error with creating user in database.") from e
    except RedisError as e:
        await db_session.rollback()
        raise RedisStorageError("An occured error with creating verify user keys in database.") from e
    
    return {"status": "Code was successfully sent.", "user_id": user.id}


async def login_user_request_service(
    user_data: UserCreateRequest,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str | int]:
    """User authorization service"""

    user = await get_user_by_email(user_data.email, db_session)

    if not user:
        raise UserNotFoundError()
    
    if not user.is_verified:
        verify_password(_DUMMY_HASH, user_data.password.get_secret_value())
        raise UserNotVerifiedError()
    
    if not verify_password(user.password_hash, user_data.password.get_secret_value()):
        raise IncorrectPasswordError()
    
    code = generate_code()
    
    try:
        await create_verification_keys(
            user.id,
            user.email, code,
            redis_client,
            code_type="verification",
            task_name='send_mail_verification'
        )
    except RedisError as e:
        raise RedisStorageError("Error with creating verification keys in redis.") from e
    
    return {"status": "Code was successfully sent.", "user_id": user.id}


async def create_tokens_service(
    user_data: CreateTokensRequest,
    user_info: UserInfo,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str]:
    """Service for verification user"""

    try:
        user = await get_user_by_id(user_data.user_id, db_session)
    except SQLAlchemyError as e:
        raise DatabaseError("Error with finding user in database.") from e

    if not user:
        raise UserNotFoundError()
    
    try:
        verif_code_redis = await redis_client.get(f"email:verification:{user_data.user_id}:code")
        verif_attempts_redis = await redis_client.get(f"email:verification:{user_data.user_id}:attempts")
    except RedisError as e:
        raise RedisStorageError("Error with getting verif user code or attempts from redis.") from e

    if not verif_code_redis:
        raise CodeNotFoundError()

    if not verif_attempts_redis:
        logger.error(
            "Attempts key not found, but code key exists",
            user_id=user_data.user_id
        )
        raise RedisStorageError("Error with getting key with attempts counter from redis.")

    if int(verif_attempts_redis) >= 5:
        try:
            await redis_client.delete(f"email:verification:{user_data.user_id}:code")
            await redis_client.delete(f"email:verification:{user_data.user_id}:attempts")
        except RedisError as e:
            logger.exception(
                msg="error with deleting key code for verification from redis",
                error=str(e)
            )
        raise TooManyVerificationAttemptsError()
    
    if str(verif_code_redis) == user_data.code:
        try:
            tokens = await create_tokens(
                db_session=db_session,
                redis_client=redis_client,
                user_id=user_data.user_id,
                ip_address=user_info.ip_address,
                user_agent=user_info.user_agent
            )

            if not user.is_verified:
                user.is_verified = True

            await db_session.commit()
        except SQLAlchemyError as e:
            await db_session.rollback()

            try:
                await redis_client.delete(f'access_token:{tokens['access_token']}')
                await redis_client.delete(f'user_session:{user.id}')
            except RedisError as e:
                logger.exception(
                    msg='error with deleting tokens from redis',
                    error=str(e)
                )

            raise DatabaseError("Error with creating new values in database.") from e
        except RedisError as e:
            await db_session.rollback()
            raise RedisStorageError("Error with creating access token key in redis.") from e
        
        try:
            await redis_client.delete(f"email:verification:{user_data.user_id}:code")
            await redis_client.delete(f"email:verification:{user_data.user_id}:attempts")
        except RedisError as e:
            logger.exception(
                msg="error deleting keys in redis",
                error=str(e)
            )

        return {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token']
        }
        
    else:
        try:
            await redis_client.incr(f"email:verification:{user_data.user_id}:attempts")
            raise IncorrectCodeError()
        except RedisError as e:
            raise RedisStorageError("Error with incrementing verify attempts in redis.") from e
        

async def refresh_tokens_service(
    inputed_refresh_token: str,
    user: User,
    user_info: UserInfo,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str]:
    try:
        refresh_token = await get_refresh_token_by_hash(inputed_refresh_token, db_session)
    except SQLAlchemyError as e:
        raise DatabaseError('Error with getting refresh token from database.') from e
    
    if not refresh_token:
        raise InvalidTokenError()
    
    if refresh_token.is_revoked:
        await queue.enqueue(
            "send_mail_suspicious_activity",
            email=user.email,
            ip_address=user_info.ip_address,
            user_agent=user_info.user_agent
        )
        raise RefreshTokenRevokedError()

    try:
        refresh_tokens = await get_refresh_tokens(user.id, db_session)

        for refresh_token in refresh_tokens:
            refresh_token.is_revoked = True

        tokens = await create_tokens(
            db_session,
            redis_client,
            user.id,
            user_info.ip_address,
            user_info.user_agent
        )

        await db_session.commit()
    except SQLAlchemyError as e:
        await db_session.rollback()

        try:
            await redis_client.delete(f"access_token:{tokens['access_token']}")
            await redis_client.delete(f'user_session:{user.id}')
        except RedisError as e:
            logger.exception(
                msg='error with deleting tokens from redis',
                error=str(e)
            )

        raise DatabaseError("Error with creating refresh token in database.") from e
    except RedisError as e:
        await db_session.rollback()
        raise RedisStorageError('Error with creating tokens in redis.') from e
    
    return {
        'access_token': tokens['access_token'],
        'refresh_token': tokens['refresh_token']
    }


async def revoke_tokens_service(
    access_token: str,
    transferred_refresh_token: str,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str]:
    try:
        refresh_token = await get_refresh_token_by_hash(transferred_refresh_token, db_session)

        if refresh_token:
            refresh_token.is_revoked = True

        await redis_client.delete(f"access_token:{access_token}")
        await db_session.commit()
    except SQLAlchemyError as e:
        await db_session.rollback()
        raise DatabaseError('Error with setting status revoked for refresh token in database.') from e
    except RedisError as e:
        await db_session.rollback()
        raise RedisStorageError('Error with deleting key from redis.') from e
    
    return {'status': 'Logouted.'}


async def change_password_or_email_request_service(
    user: User,
    redis_client: Redis,
    *,
    code_type: str,
    task_name: str
) -> dict[str, str | int]:
    """Service for sending code for changing password or email"""
    code = generate_code()

    try:
        await create_verification_keys(
            user.id,
            user.email,
            code,
            redis_client,
            code_type=code_type,
            task_name=task_name
        )
    except RedisError as e:
        raise RedisStorageError('Error with creating verification keys in redis.') from e
    
    return {"status": "Code was been sent.", "user_id": user.id}


async def change_password_confirm_service(
    user: User,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict [str, str]:
    pass


async def change_email_confirm_serivce(
    user: User,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict [str, str]:
    pass