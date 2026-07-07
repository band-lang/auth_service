from src.workers.queue import queue
from src.workers.logging_config import setup_worker_logging
from src.workers.tasks.email import send_verification_email


async def startup(ctx):
    setup_worker_logging()


async def shutdown(ctx):
    pass


settings = {
    "queue": queue,
    "functions": [
        send_verification_email,
    ],
    "concurrency": 10,
    "startup": startup,
    "shutdown": shutdown
}