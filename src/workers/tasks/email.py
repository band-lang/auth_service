import json
from datetime import datetime, timezone
from typing import Callable, Any
from saq.types import Context
from src.logger import logger
from src.auth.email_utils import (
    send_verification_mail,
    send_change_password_mail,
    send_change_email_mail,
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


async def email_task_handler(
    ctx: Context,
    task_name: str,
    func: Callable[..., Any],
    **kwargs
) -> None:
    """Email tasks handler function."""
    
    try:
        await func(**kwargs)
    except PERMANENT_ERRORS as e:
        logger.exception(
            msg="permanent error in email_task_handler",
            arguments=kwargs,
            error=str(e)
        )
        # Saving in Dead Letter Queue
        redis = ctx["job"].queue.redis

        await redis.lpush(
            "dead_letters",
            json.dumps({
                "task": task_name,
                "kwargs": kwargs,
                "error": str(e),
                "type": "permanent",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        )
        # Not retry
        return

    except TEMPORARY_ERRORS as e:
        logger.exception(
            msg="temporary error in handler send verification mail",
            arguments=kwargs,
            error=str(e)
        )
        # Retry
        raise


async def send_mail_verification(
    ctx: Context,
    *,
    email: str,
    code: str,
) -> None:
    """Sending verification mail."""
    await email_task_handler(ctx, "send_mail_verification", send_verification_mail, to=email, code=code)


async def send_mail_suspicious_activity(
    ctx: Context,
    *,
    email: str,
    ip_address: str,
    user_agent: str
) -> None:
    """Sending mail notification about suspicious activity on account."""
    if not ip_address:
        ip_address = "Не удалось получить."
    
    if not user_agent:
        user_agent = "Не удалось получить."

    await email_task_handler(
        ctx,
        "send_suspicious_activity_notification",
        send_suspicious_activity_notification,
        to=email,
        ip_address=ip_address,
        user_agent=user_agent
    )


async def send_mail_change_password(
    ctx: Context,
    *,
    email: str,
    code: str
) -> None:
    """Sending change password mail"""
    await email_task_handler(
        ctx,
        "send_mail_change_password",
        send_change_password_mail,
        to=email,
        code=code
    )


async def send_mail_change_email(
    ctx: Context,
    *,
    email: str,
    code: str
) -> None:
    """Sending mail for change email"""
    await email_task_handler(
        ctx,
        "send_mail_change_email",
        send_change_email_mail,
        to=email,
        code=code
    )