from typing import cast
from fastapi import Request, Header
from redis.asyncio import Redis
from src.auth.schemas import UserInfo


def get_redis(request: Request) -> Redis:
    return cast(Redis, request.app.state.redis)


def get_user_info(
    request: Request,
    user_agent: str | None = Header(None, include_in_schema=False)
) -> UserInfo:
    client_host = request.client.host if request.client else None
    
    return UserInfo(
        user_agent=user_agent,
        ip_adress=client_host
    )