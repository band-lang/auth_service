from typing import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from redis.asyncio import Redis
from src.auth import router as auth_router
from src.config import REDIS_HOST, REDIS_PORT, REDIS_MAX_CONNECTIONS
from src.auth.exceptions import app_exception_handler, AppException
from src.exceptions import DatabaseException, database_errors_handler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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
    description="Микро сервис для авторизации.",
    lifespan=lifespan
)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(DatabaseException, database_errors_handler)
app.include_router(auth_router.router)