from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.schemas import UserCreate, UserVerifyRequest, UserVerifyResponse, UserInfo
from src.database import get_db
from src.auth.dependencies import get_redis, get_user_info
from src.auth.service import register_user_service, verify_user_service


router = APIRouter()


@router.get('/')
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post('/users')
async def register_user_router(
    user_data: UserCreate,
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str | int]:
    return await register_user_service(user_data, db_session, redis_client)


@router.post('/users/verify', response_model=UserVerifyResponse)
async def verify_user_router(
    user_data: UserVerifyRequest,
    user_info: UserInfo = Depends(get_user_info),
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str]:
    return await verify_user_service(
        user_data=user_data,
        user_info=user_info,
        db_session=db_session,
        redis_client=redis_client
    )