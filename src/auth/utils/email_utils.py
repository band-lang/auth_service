import asyncio
import random
from typing import Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from email.mime.text import MIMEText
from aiosmtplib import SMTP
from aiosmtplib.errors import (
    SMTPAuthenticationError,
    SMTPException,
    SMTPRecipientRefused,
    SMTPSenderRefused,
    SMTPDataError,
    SMTPConnectError,
    SMTPConnectTimeoutError
)
from src.config import (
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_FROM,
    MAIL_SERVER,
    MAIL_PORT,
    APP_NAME
)
from src.logger import logger
from src.auth.exceptions import (
    EmailTimeoutError,
    EmailAuthError,
    EmailRecipientRefusedError,
    EmailSenderRefusedError,
    EmailTemporaryError,
    EmailPermanentError,
    EmailConnectionError
)


#Jinja2 settings, not ideal, check that
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "email"
jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(['html', 'xml'])
)


def render_template(template_name: str, **kwargs: Any) -> str:
    """Render html templates with passed arguments"""
    template = jinja_env.get_template(template_name)
    return template.render(**kwargs)


def generate_code() -> str:
    """Generate code"""
    return f"{random.randint(0000000, 99_999_999):08d}"


async def send_email(to: str, subject: str, body: str, message_type: str) -> None:
    """Base function for sending mail"""

    message = MIMEText(body, "html")
    message["From"] = MAIL_FROM
    message["To"] = to
    message["Subject"] = subject

    #ОБЯЗАТЕЛЬНО добавить логирование и отправку ошибок мне в телеграм.

    try:
        smtp = SMTP(hostname=MAIL_SERVER, port=MAIL_PORT, start_tls=True, timeout=10)
        await smtp.connect()

        try:
            await asyncio.wait_for(smtp.login(MAIL_USERNAME, MAIL_PASSWORD), timeout=15)
        except asyncio.TimeoutError:
            await smtp.quit()
            raise
        
        await smtp.send_message(message)
        await smtp.quit()

    except SMTPConnectTimeoutError as e:
        logger.exception(
            msg="timeout_error",
            msg_type=message_type,
            mail_server=MAIL_SERVER,
            mail_from=MAIL_FROM,
            mail_port=MAIL_PORT,
            error=str(e)
        )
        raise EmailTimeoutError()

    except SMTPConnectError as e:
        logger.exception(
            msg="smtp_connect_error",
            mail_server=MAIL_SERVER,
            mail_from=MAIL_FROM,
            mail_port=MAIL_PORT,
            error=str(e)
        )
        raise EmailConnectionError(MAIL_FROM)
    
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
        logger.exception(
            msg="timeout_error",
            msg_type=message_type,
            mail_server=MAIL_SERVER,
            mail_from=MAIL_FROM,
            mail_port=MAIL_PORT,
            error=str(e)
        )
        raise EmailTimeoutError()

    except SMTPAuthenticationError as e:
        logger.exception(
            msg="smtp_auth_error",
            mail_server=MAIL_SERVER,
            mail_from=MAIL_FROM,
            mail_port=MAIL_PORT,
            error=str(e)
        )
        raise EmailAuthError()

    except SMTPRecipientRefused as e:
        logger.exception(
            msg="recipient_refused_error",
            to=to,
            mail_server=MAIL_SERVER,
            mail_from=MAIL_FROM,
            mail_port=MAIL_PORT,
            error=str(e)
        )
        raise EmailRecipientRefusedError(to)

    except SMTPSenderRefused as e:
        logger.exception(
            msg="sender_refused_error",
            mail_server=MAIL_SERVER,
            mail_from=MAIL_FROM,
            mail_port=MAIL_PORT,
            error=str(e)
        )
        raise EmailSenderRefusedError()

    except SMTPDataError as e:
        logger.exception(
            msg="smtp_data_error",
            msg_type=message_type,
            to=to,
            subject=subject,
            body=body,
            to_type=type(to),
            subject_type=type(subject),
            body_type=type(body),
            error=str(e)
        )
        smtp_code = getattr(e, "code", 500) or 500

        if 400 <= smtp_code < 500:
            raise EmailTemporaryError(f"SMTPDataError, error code: {smtp_code}")
        else:
            raise EmailPermanentError(f"SMTPDataError, error code: {smtp_code}")

    except SMTPException as e:
        logger.exception(
            msg="unknown_smtp_error",
            msg_type=message_type,
            to=to,
            subject=subject,
            body=body,
            to_type=type(to),
            subject_type=type(subject),
            body_type=type(body),
            mail_server=MAIL_SERVER,
            mail_from=MAIL_FROM,
            mail_port=MAIL_PORT,
            error=str(e)
        )
        raise EmailPermanentError(f"Unknown SMTP Permanent Error")
    
    except Exception as e:
        logger.exception(
            msg="unknown_error",
            msg_type=message_type,
            to=to,
            subject=subject,
            body=body,
            to_type=type(to),
            subject_type=type(subject),
            body_type=type(body),
            mail_server=MAIL_SERVER,
            mail_from=MAIL_FROM,
            mail_port=MAIL_PORT,
            error=str(e)
        )
        raise EmailPermanentError(f"Unknown exception error")


async def send_verification_mail(to: str, code: str) -> None:
    """Sending verification mail"""

    subject = f"Подтверждение регистрации/входа в {APP_NAME}."
    body = render_template(
        "verification.html",
        app_name=APP_NAME,
        code=code,
        ttl_minutes=10
    )
    await send_email(to, subject, body, "verify_user")


async def send_change_password_mail(to: str, code: str) -> None:
    """Sending change password mail"""

    subject = f"Смена пароля в {APP_NAME}."
    body = render_template(
        "change_password.html",
        app_name=APP_NAME,
        code=code,
        ttl_minutes=10
    )
    await send_email(to, subject, body, "change_password")


async def send_change_email_mail(to: str, code: str) -> None:
    """Sending change email mail"""

    subject=f'Смена почты в {APP_NAME}'
    body = render_template(
        "change_email.html",
        app_name=APP_NAME,
        code=code,
        ttl_minutes=10
    )
    await send_email(to, subject, body, "change_email")


async def send_password_change_notification(to: str, ip_address: str) -> None:
    """Sending notify about password change"""

    subject = f"На вашем аккаунте {APP_NAME} был сменён пароль."
    body = render_template(
        "password_changed.html",
        app_name=APP_NAME,
        ip_address=ip_address
    )
    await send_email(to, subject, body, "password_change_notification")


async def send_suspicious_activity_notification(to: str, ip_address: str, user_agent: str) -> None:
    """Sending notify about suspicious activity"""

    subject = f"Подозрительная активность в вашем аккаунте {APP_NAME}"
    body = render_template(
        "suspicious_activity.html",
        app_name=APP_NAME,
        ip_address=ip_address,
        user_agent=user_agent
    )
    await send_email(to, subject, body, "suspicious_activity_notification")