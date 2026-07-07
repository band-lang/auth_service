from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from src.auth.schemas import UserCreate
from src.auth.exceptions import EmailAlreadyExistsError
from src.exceptions import RedisStorageError, DatabaseError
from src.auth.queries import get_user_by_email, create_user
from src.auth.email_utils import generate_code
from src.workers.queue import queue


async def create_verification_keys(
    user_id: int,
    email: str,
    code: str,
    redis_client: Redis
) -> None:
    """Сохраняет код в Redis и ставит задачу на отправку письма."""

    async with redis_client.pipeline(transaction=True) as pipe:
        # Код верификации
        pipe.setex(f"email:verif:{user_id}:code", code, 600)
        # Счётчик попыток
        pipe.setex(f"email:verif:{user_id}:attempts", "1", 600)
        await pipe.execute()

    # Задача в SAQ (отдельно от pipeline)
    await queue.enqueue(
        "send_verification_email",
        email=email,
        code=code
    )


async def register_user_service(
    user_data: UserCreate,
    db: AsyncSession,
    redis_client: Redis
):
    """Service for registration users."""

    existing_user = await get_user_by_email(user_data.email, db)

    if existing_user:
        if existing_user.is_verified:
            raise EmailAlreadyExistsError()
        else:
            try:
                code = generate_code()
                await create_verification_keys(existing_user.id, existing_user.email, code, redis_client)
            except RedisError as e:
                raise RedisStorageError("Redis creating verification keys error") from e

            return {"status": "Code was successfully sent.", "user_id": existing_user.id}

    code = generate_code()

    try:
        user = await create_user(user_data, db)

        await create_verification_keys(user.id, user.email, code, redis_client)

        await db.commit()
        await db.refresh(user)
    except SQLAlchemyError as e:
        await db.rollback()
        raise DatabaseError("An occured error with creating user in database. Please try again later.") from e
    except RedisError as e:
        await db.rollback()
        raise RedisStorageError("An occured error with creating verify user keys in database. Please try again later.") from e
    
    return {"status": "Code was successfully sended.", "user_id": user.id}