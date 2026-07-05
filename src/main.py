from fastapi import FastAPI
from src.auth import router as auth_router


app = FastAPI(
    title="Auth service",
    version="a0.1.0",
    description="Микро сервис для авторизации."
)


app.include_router(auth_router.router)