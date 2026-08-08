from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from src.auth.schemas import UserCreateRequest, CreateTokensRequest, UserInfo
from src.auth.queries import (
    get_user_by_email,
    create_user,
    get_user_by_id
)
from src.auth.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    UserNotVerifiedError
)
from src.auth.redis_helpers import (
    create_verification_keys,
    create_tokens
)
from src.auth.services.verification_code_serivce import _verify_code
from src.exceptions import DatabaseError, RedisStorageError
from src.logger import logger
from src.auth.utils.email_utils import generate_code
from src.auth.utils.security_utils import hash_password, verify_password, _DUMMY_HASH




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
                await create_verification_keys(
                    existing_user.id,
                    existing_user.email,
                    code,
                    redis_client,
                    code_type="verification",
                    job_func_name='send_mail_verification'
                )
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
            job_func_name='send_mail_verification'
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
        verify_password(_DUMMY_HASH, user_data.password.get_secret_value())
        raise InvalidCredentialsError()
    
    if not user.is_verified:
        verify_password(_DUMMY_HASH, user_data.password.get_secret_value())
        raise UserNotVerifiedError()
    
    if not verify_password(user.password_hash, user_data.password.get_secret_value()):
        raise InvalidCredentialsError()
    
    code = generate_code()
    
    try:
        await create_verification_keys(
            user.id,
            user.email, code,
            redis_client,
            code_type="verification",
            job_func_name='send_mail_verification'
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
    """Service for verification user.

    Args:
        user_data - pydantic schema with fields user_id: int and code: str.
        user_info - pydantic schema with fields user_agent: str | None, ip_address: str | None.
        db_session - object of SessionLocal, usings for work with connection of database.
        redis_client - object of Redis, usings for work with connection of redis.

    Returns:
        access_token and refresh_token in dict.

    """

    try:
        user = await get_user_by_id(user_data.user_id, db_session)
    except SQLAlchemyError as e:
        raise DatabaseError("Error with finding user in database.") from e

    if not user:
        raise InvalidCredentialsError()
    
    await _verify_code(
        code_type="verification",
        inputed_code=user_data.code,
        user_id=user_data.user_id,
        redis_client=redis_client
    )
    
    try:
        if not user.is_verified:
            user.is_verified = True

        tokens = await create_tokens(
            db_session=db_session,
            redis_client=redis_client,
            user_id=user_data.user_id,
            ip_address=user_info.ip_address,
            user_agent=user_info.user_agent
        )

        await db_session.commit()

        return {
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token']
        }

    except SQLAlchemyError as e:
        await db_session.rollback()

        try:
            await redis_client.delete(f"access_token:{tokens['access_token']}")
            await redis_client.delete(f'user_sessions:{user.id}')
        except RedisError as e:
            logger.exception(
                msg='error with deleting tokens from redis',
                error=str(e)
            )

        raise DatabaseError("Error with creating new values in database.") from e
    except RedisError as e:
        await db_session.rollback()
        raise RedisStorageError('Error with creating tokens in redis.') from e