import secrets
import hashlib
import json
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from src.auth.schemas import UserCreate, UserVerifyRequest, UserInfo
from src.auth.exceptions import (
    EmailAlreadyExistsError,
    UserNotFoundError,
    CodeNotFoundError,
    IncorrectCodeError,
    TooManyVerificationAttemptsError
)
from src.exceptions import RedisStorageError, DatabaseError
from src.auth.queries import get_user_by_email, create_user, create_refresh_token, get_user_by_id
from src.auth.email_utils import generate_code
from src.auth.utils import hash_password, verify_password
from src.workers.queue import queue
from src.config import ACCESS_TOKEN_EXPIRE_MINUTES
from src.logger import logger


async def create_verification_keys(
    user_id: int,
    email: str,
    code: str,
    redis_client: Redis
) -> None:
    """Сохраняет код в Redis и ставит задачу на отправку письма."""

    async with redis_client.pipeline(transaction=True) as pipe:
        # Код верификации
        pipe.setex(name=f"email:verif:{user_id}:code", time=600, value=code)
        # Счётчик попыток
        pipe.setex(name=f"email:verif:{user_id}:attempts", time=600, value="1")
        await pipe.execute()

    # Задача в SAQ (отдельно от pipeline)
    await queue.enqueue(
        "send_verification_email",
        email=email,
        code=code,
        timeout=30
    )


async def create_tokens(
    db_session: AsyncSession,
    redis_client: Redis,
    user_id: int,
    ip_address: str | None,
    user_agent: str | None
) -> dict[str, str]:
    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(64)
    hashed_access_token = hashlib.sha256(access_token.encode("utf-8")).hexdigest()
    hashed_refresh_token = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.setex(
                name=f"access_token:{hashed_access_token}",
                time=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                value=json.dumps({
                "user_id": user_id, "ip_address": ip_address, "user_agent": user_agent
            })
        )
        pipe.sadd(f"user_sessions:{user_id}", hashed_access_token)
        await pipe.execute()

    await create_refresh_token(hashed_refresh_token, user_id, user_agent, ip_address, db_session)
    
    return {"access_token": access_token, "refresh_token": refresh_token}


async def register_user_service(
    user_data: UserCreate,
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

        await create_verification_keys(user.id, user.email, code, redis_client)

        await db_session.commit()
        await db_session.refresh(user)
    except SQLAlchemyError as e:
        await db_session.rollback()
        raise DatabaseError("An occured error with creating user in database.") from e
    except RedisError as e:
        await db_session.rollback()
        raise RedisStorageError("An occured error with creating verify user keys in database.") from e
    
    return {"status": "Code was successfully sent.", "user_id": user.id}


async def verify_user_service(
    user_data: UserVerifyRequest,
    user_info: UserInfo,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str]:
    try:
        user = await get_user_by_id(user_data.user_id, db_session)
    except SQLAlchemyError as e:
        raise DatabaseError("Error with finding user in database.") from e

    if not user:
        raise UserNotFoundError()
    
    try:
        verif_code_redis = await redis_client.get(f"email:verif:{user_data.user_id}:code")
        verif_attempts_redis = await redis_client.get(f"email:verif:{user_data.user_id}:attempts")
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
        raise TooManyVerificationAttemptsError()
    
    if str(verif_code_redis) == user_data.code:
        try:
            user.is_verified = True
            
            tokens = await create_tokens(
                db_session=db_session,
                redis_client=redis_client,
                user_id=user_data.user_id,
                ip_address=user_info.ip_adress,
                user_agent=user_info.user_agent
            )

            await db_session.commit()
        except SQLAlchemyError as e:
            await db_session.rollback()
            raise DatabaseError("Error with settings verified flag in database.") from e
        except RedisError as e:
            await db_session.rollback()
            raise RedisStorageError("Error with creating access token key in redis.") from e
        
        try:
            await redis_client.delete(f"email:verif:{user_data.user_id}:code")
            await redis_client.delete(f"email:verif:{user_data.user_id}:attempts")
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
            await redis_client.incr(f"email:verif:{user_data.user_id}:attempts")
            raise IncorrectCodeError()
        except RedisError as e:
            raise RedisStorageError("Error with incrementing verify attempts in redis.") from e