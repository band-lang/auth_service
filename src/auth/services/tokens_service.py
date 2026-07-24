from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from src.auth.models import User
from src.auth.queries import (
    get_refresh_token_by_hash
)
from redis.asyncio import Redis
from redis.exceptions import RedisError
from src.auth.redis_helpers import create_tokens
from src.auth.exceptions import (
    InvalidTokenError,
    RefreshTokenRevokedError
)
from src.exceptions import RedisStorageError, DatabaseError
from src.auth.schemas import UserInfo
from src.logger import logger
from src.workers.queue import queue


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
            await redis_client.delete(f'user_sessions:{user.id}')
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
    
    return {'status': 'Tokens successfully revoked.'}