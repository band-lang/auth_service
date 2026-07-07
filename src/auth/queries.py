from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.auth.models import User, RefreshToken
from src.auth.schemas import UserCreate
from src.auth.utils import hash_password
from src.config import REFRESH_TOKEN_EXPIRE_DAYS


#Quries for work with users
async def get_user_by_email(
    email: str,
    db_session: AsyncSession
) -> User | None:
    """Return True/False or None if user not existing."""

    result = await db_session.execute(
        select(User)
        .where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(
    user_id: int,
    db_session: AsyncSession
) -> User | None:
    result = await db_session.execute(
        select(User)
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    user_data: UserCreate,
    db_session: AsyncSession
) -> User:
    hashed_password = hash_password(user_data.password.get_secret_value())

    user = User(
        email=user_data.email,
        password_hash=hashed_password
    )

    db_session.add(user)
    await db_session.flush()

    return user


async def create_refresh_token(
    hashed_token: str,
    user_id: int,
    user_agent: str | None,
    ip_address: str | None,
    db_session: AsyncSession
) -> None:
    refresh_token = RefreshToken(
        user_id=user_id,
        token_hash=hashed_token,
        expire_date=datetime.now(timezone.utc) + timedelta(REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=user_agent,
        ip_address=ip_address
    )

    db_session.add(refresh_token)
    await db_session.flush()