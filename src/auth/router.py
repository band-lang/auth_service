from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import User
from src.auth.schemas import (
    UserCreateRequest,
    CreateTokensRequest,
    CreateTokensResponse,
    UserInfo,
    RefreshTokensRequest,
    ChangePasswordRequest,
    ChangeEmailRequest,
    ChangeEmailInitRequest
)
from src.database import get_db
from src.auth.dependencies import (
    get_redis,
    get_user_info,
    get_active_user,
    get_user_without_suspicious_check
)
from src.auth.services.registration_service import (
    register_user_service,
    create_tokens_service,
    login_user_request_service
)
from src.auth.services.tokens_service import (
    refresh_tokens_service,
    revoke_tokens_service
)
from src.auth.services.credentials_service import (
    change_password_request_service,
    change_email_request_service,
    change_password_confirm_service,
    change_email_confirm_service
)
from src.limiter import limiter


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
@limiter.limit("5/minute")
async def register_user_router(
    request: Request,
    user_data: UserCreateRequest,
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str | int]:
    return await register_user_service(user_data, db_session, redis_client)


# Use the same schema as in the registration endpoint, because the fields are the same.
@router.post('/login/request')
@limiter.limit("5/minute")
async def login_user_request_router(
    request: Request,
    user_data: UserCreateRequest,
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str | int]:
    return await login_user_request_service(user_data, db_session, redis_client)


@router.post('/tokens', response_model=CreateTokensResponse)
@limiter.limit("5/minute")
async def create_tokens_router(
    request: Request,
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
@limiter.limit("4/hour")
async def refresh_tokens_router(
    request: Request,
    inputed_refresh_token: RefreshTokensRequest,
    user: User = Depends(get_active_user),
    user_info: UserInfo = Depends(get_user_info),
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str]:
    return await refresh_tokens_service(inputed_refresh_token.refresh_token, user, user_info, db_session, redis_client)


@router.delete('/tokens/revoke')
@limiter.limit("30/hour")
async def revoke_tokens_router(
    request: Request,
    inputed_refresh_token: RefreshTokensRequest,
    user: User = Depends(get_active_user),
    access_token: HTTPAuthorizationCredentials = Depends(security),
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str]:
    return await revoke_tokens_service(access_token.credentials, inputed_refresh_token.refresh_token, db_session, redis_client)


@router.post('/password/reset')
@limiter.limit("3/hour")
async def reset_password_request_router(
    request: Request,
    user: User = Depends(get_user_without_suspicious_check),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str | int]:
    return await change_password_request_service(
        user,
        redis_client,
        code_type="password_reset",
        job_func_name="send_mail_change_password"
    )


@router.patch('/password/reset/confirm')
@limiter.limit("3/hour")
async def reset_password_confirm_router(
    request: Request,
    user_data: ChangePasswordRequest,
    user: User = Depends(get_user_without_suspicious_check),
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str]:
    return await change_password_confirm_service(
        user=user,
        user_data=user_data,
        db_session=db_session,
        redis_client=redis_client
    )


@router.post('/email/change')
@limiter.limit("3/hour")
async def change_email_request_router(
    request: Request,
    user_data: ChangeEmailInitRequest,
    user: User = Depends(get_user_without_suspicious_check),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str | int]:
    return await change_email_request_service(
        user=user,
        new_email=user_data.new_email,
        redis_client=redis_client
    )


@router.patch('/email/change/confirm')
@limiter.limit("3/hour")
async def change_email_confirm_router(
    request: Request,
    user_data: ChangeEmailRequest,
    user: User = Depends(get_user_without_suspicious_check),
    db_session: AsyncSession = Depends(get_db),
    redis_client: Redis = Depends(get_redis)
) -> dict[str, str]:
    return await change_email_confirm_service(
        user=user,
        user_data=user_data,
        db_session=db_session,
        redis_client=redis_client
    )