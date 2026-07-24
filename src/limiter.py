from slowapi import Limiter
from slowapi.util import get_remote_address
from src.config import REDIS_HOST, REDIS_PORT


# Configurate rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
)
