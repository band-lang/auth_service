from saq.types import Context
from src.workers.queue import queue
from src.workers.logging_config import setup_worker_logging
from src.workers.tasks.email import (
    send_mail_verification,
    send_mail_change_password,
    send_mail_change_email,
    send_mail_suspicious_activity,
    send_mail_creditionals_change_notification
)


async def startup(ctx: Context) -> None:
    setup_worker_logging()


async def shutdown(ctx: Context) -> None:
    pass


settings = {
    "queue": queue,
    "functions": [
        send_mail_verification,
        send_mail_change_password,
        send_mail_change_email,
        send_mail_suspicious_activity,
        send_mail_creditionals_change_notification
    ],
    "concurrency": 10,
    "startup": startup,
    "shutdown": shutdown
}