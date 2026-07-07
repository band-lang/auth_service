from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.schemas import UserCreate
from src.database import get_db
from src.auth.dependencies import get_redis
from src.auth.service import register_user_service


router = APIRouter()


@router.get('/')
def health():
    return {"status": "ok"}


@router.post('/users')
async def register_user_router(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict:
    return await register_user_service(user_data, db, redis_client)