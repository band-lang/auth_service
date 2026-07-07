import json
from datetime import datetime, timezone
from typing import cast
from saq.types import Context
from redis.asyncio import Redis
from src.logger import logger
from src.auth.email_utils import (
    send_verification_mail,
    send_change_password_mail,
    send_password_change_notification,
    send_suspicious_activity_notification
)
from src.auth.exceptions import (
    EmailTimeoutError,
    EmailAuthError,
    EmailRecipientRefusedError,
    EmailSenderRefusedError,
    EmailTemporaryError,
    EmailPermanentError,
    EmailConnectionError
)


TEMPORARY_ERRORS = (
    EmailTemporaryError,
    EmailTimeoutError,
    EmailConnectionError
)
PERMANENT_ERRORS = (
    EmailAuthError,
    EmailRecipientRefusedError,
    EmailSenderRefusedError,
    EmailPermanentError
)


async def send_verification_email(ctx: Context, *, email: str, code: str) -> None:
    """Func send verification mail worker"""
    
    try:
        await send_verification_mail(email, code)
    except PERMANENT_ERRORS as e:
        logger.error(
            msg="permanent error in worker send verification email",
            email=email,
            code=code,
            error=str(e)
        )
        # Сохраняем в Dead Letter Queue
        redis = cast(Redis, ctx.get("redis"))
        await redis.lpush(
            "dead_letters",
            json.dumps({
                "task": "send_verification_email",
                "email": email,
                "error": str(e),
                "type": "permanent",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        )
        # НЕ перебрасываем — не ретраим
        return

    except TEMPORARY_ERRORS as e:
        logger.error(
            msg="temporary error in worker send verification email",
            email=email,
            code=code,
            error=str(e)
        )
        # Перебрасываем — SAQ сделает ретрай
        raise