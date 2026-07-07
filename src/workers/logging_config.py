import logging
import sys


def setup_worker_logging(level:int = logging.INFO) -> None:
    """Logger for worker"""

    logger = logging.getLogger("saq")
    logger.setLevel(level)

    #Handler for out in console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    ))
    logger.addHandler(console_handler)

    #Handler for logging in file
    file_handler = logging.FileHandler('logs/worker.log')
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    ))
    logger.addHandler(file_handler)