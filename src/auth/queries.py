from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.auth.models import User
from src.auth.schemas import UserCreate
from src.auth.utils import hash_password


async def get_user_by_email(
    email: str,
    db: AsyncSession
) -> User | None:
    """Return True/False or None if user not existing."""

    result = await db.execute(
        select(User)
        .where(User.email == email)
    )
    return result.scalar_one_or_none()


async def create_user(
    user_data: UserCreate,
    db: AsyncSession
) -> User:
    hashed_password = hash_password(user_data.password.get_secret_value())

    user = User(
        email=user_data.email,
        password_hash=hashed_password
    )

    db.add(user)
    await db.flush()

    return user