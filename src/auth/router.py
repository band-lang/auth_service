from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import User
from src.auth.schemas import (
    UserCreateRequest,
    CreateTokensRequest,
    CreateTokensResponse,
    UserInfo,
    RefreshTokensRequest
)
from src.database import get_db
from src.auth.dependencies import (
    get_redis,
    get_user_info,
    get_active_user,
    get_user_without_suspicious_check
)
from src.auth.service import (
    register_user_service,
    login_user_request_service,
    create_tokens_service,
    refresh_tokens_service,
    revoke_tokens_service,
    change_password_or_email_request_service
)


router = APIRouter()
security = HTTPBearer()

# Dev endpoints
@router.get('/')
def health_router() -> dict[str, str]:
    return {"status": "ok"}


@router.get('/protected')
def protected_router(
    user: User = Depends(get_active_user)
) -> dict [str, str]:
    return {'status': 'Success!'}


@router.post('/users')
async def register_user_router(
    user_data: UserCreateRequest,
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str | int]:
    return await register_user_service(user_data, db_session, redis_client)


# Use the same schema as in the registration endpoint, because the fields are the same.
@router.post('/login/request')
async def login_user_request_router(
    user_data: UserCreateRequest,
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str | int]:
    return await login_user_request_service(user_data, db_session, redis_client)


@router.post('/tokens', response_model=CreateTokensResponse)
async def create_tokens_router(
    user_data: CreateTokensRequest,
    user_info: UserInfo = Depends(get_user_info),
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str]:
    return await create_tokens_service(
        user_data=user_data,
        user_info=user_info,
        db_session=db_session,
        redis_client=redis_client
    )


@router.post('/tokens/refresh', response_model=CreateTokensResponse)
async def refresh_tokens_router(
    inputed_refresh_token: RefreshTokensRequest,
    user: User = Depends(get_active_user),
    user_info: UserInfo = Depends(get_user_info),
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str]:
    return await refresh_tokens_service(inputed_refresh_token.refresh_token, user, user_info, db_session, redis_client)


@router.delete('/tokens/revoke')
async def revoke_tokens_router(
    inputed_refresh_token: RefreshTokensRequest,
    user: User = Depends(get_active_user),
    access_token: HTTPAuthorizationCredentials = Depends(security),
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str]:
    return await revoke_tokens_service(access_token.credentials, inputed_refresh_token.refresh_token, db_session, redis_client)


@router.post('/password/reset')
async def reset_password_request_router(
    user: User = Depends(get_user_without_suspicious_check),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str | int]:
    return await change_password_or_email_request_service(
        user,
        redis_client,
        code_type="password_reset",
        task_name="send_mail_change_password"
    )


@router.post('/email/change')
async def change_email_request_router(
    user: User = Depends(get_user_without_suspicious_check),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str | int]:
    return await change_password_or_email_request_service(
        user,
        redis_client,
        code_type="change_email",
        task_name="send_mail_change_email"
    )