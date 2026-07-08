from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped
from src.global_models import Base


class User(Base):
    
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    totp_secret: Mapped[str] = mapped_column(String(256), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_suspicious: Mapped[bool] = mapped_column(default=False)


class RefreshToken(Base):

    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(unique=True, nullable=False)
    expire_date: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(default=False)
    user_agent: Mapped[str | None] = mapped_column(nullable=True)
    ip_address: Mapped[str | None] = mapped_column(nullable=True)