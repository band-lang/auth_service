from typing import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis.asyncio import Redis
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from src.limiter import limiter
from src.auth import router as auth_router
from src.config import REDIS_HOST, REDIS_PORT, REDIS_MAX_CONNECTIONS
from src.auth.exceptions import app_exception_handler, internal_server_exception_handler
from src.exceptions import (
    DatabaseException,
    database_errors_handler,
    AppException,
    InternalServerException
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.redis = Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        max_connections=REDIS_MAX_CONNECTIONS,
        decode_responses=True
    )

    await app.state.redis.ping()

    yield

    await app.state.redis.close()


app = FastAPI(
    title="Auth service",
    version="a0.1.0",
    description="Micro service for auth",
    lifespan=lifespan
)

# Attach limiter to app state and register its handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler) # type: ignore[arg-type]

app.add_exception_handler(AppException, app_exception_handler) # type: ignore[arg-type]
app.add_exception_handler(DatabaseException, database_errors_handler) # type: ignore[arg-type]
app.add_exception_handler(InternalServerException, internal_server_exception_handler)

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="127.0.0.1")

app.include_router(auth_router.router, prefix='/auth')