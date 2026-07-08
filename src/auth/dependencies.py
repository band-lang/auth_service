import json
from typing import cast
from fastapi import Request, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import User
from src.auth.schemas import UserInfo
from src.auth.exceptions import (
    TokenDamagedError,
    InvalidTokenError,
    UserNotFoundError,
    UserNotVerifiedError,
    UserAccountLimited
)
from src.auth.queries import get_user_by_id
from src.exceptions import RedisStorageError, DatabaseError
from src.database import get_db


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


# User dependencies
def get_user_info(
    request: Request,
    user_agent: str | None = Header(None, include_in_schema=False)
) -> UserInfo:
    client_host = request.client.host if request.client else None
    
    return UserInfo(
        user_agent=user_agent,
        ip_address=client_host
    )


security = HTTPBearer()


async def get_current_user(
    db_session: AsyncSession = Depends(get_db),
    token: HTTPAuthorizationCredentials = Depends(security),
    redis_client: Redis = Depends(get_redis)
) -> User:
    try:
        user_data_raw = await redis_client.get(f"access_token:{token.credentials}")
        if not user_data_raw:
            raise InvalidTokenError()
        
        user_data = json.loads(user_data_raw)
        user_id = int(user_data['user_id'])
        if not user_id:
            raise TokenDamagedError()
    except RedisError as e:
        raise RedisStorageError("Error with getting key from redis.") from e
    
    try:
        user = await get_user_by_id(user_id, db_session)
    except DatabaseError as e:
        raise DatabaseError("Error with getting user from database")
    
    if not user:
        raise UserNotFoundError()
    
    return user


async def get_active_user(
    user: User = Depends(get_current_user)
) -> User:
    if not user.is_verified:
        raise UserNotVerifiedError()
    
    if user.is_suspicious:
        raise UserAccountLimited()
    
    return user