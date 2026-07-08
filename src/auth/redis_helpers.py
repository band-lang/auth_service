import json
import secrets
import hashlib
from redis.asyncio import Redis
from src.workers.queue import queue
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.queries import create_refresh_token
from src.config import ACCESS_TOKEN_EXPIRE_MINUTES


async def create_verification_keys(
    user_id: int,
    email: str,
    code: str,
    redis_client: Redis
) -> None:
    """Saves the code to Redis and queues a task to send an email."""

    async with redis_client.pipeline(transaction=True) as pipe:
        # Verification code
        pipe.setex(name=f"email:verif:{user_id}:code", time=600, value=code)
        # Counter of attempts
        pipe.setex(name=f"email:verif:{user_id}:attempts", time=600, value="1")
        await pipe.execute()

    # Task in SAQ
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
    """Function for create access and refresh tokens"""

    access_token = secrets.token_urlsafe(32)
    refresh_token = secrets.token_urlsafe(64)
    hashed_refresh_token = hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.setex(
                name=f"access_token:{access_token}",
                time=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                value=json.dumps({
                "user_id": user_id, "ip_address": ip_address, "user_agent": user_agent
            })
        )
        pipe.sadd(f"user_sessions:{user_id}", access_token)
        await pipe.execute()

    await create_refresh_token(hashed_refresh_token, user_id, user_agent, ip_address, db_session)
    
    return {"access_token": access_token, "refresh_token": refresh_token}
