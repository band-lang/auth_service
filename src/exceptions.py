from fastapi import Request
from fastapi.responses import JSONResponse
from src.logger import logger


#Base app custom exception
class AppException(Exception):
    status_code = 500
    error_type = "UNKNOWN ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


#Base database custom exception
class DatabaseException(Exception):
    error_code = 500
    error_type = "DATABASE ERROR"

    def __init__(self, message: str) -> None:
        self.message = message


#Redis exceptions
class RedisStorageError(DatabaseException):
    status_code = 500
    error_type = "REDIS ERROR"

    def __init__(self, message):
        super().__init__(message)


#Database exceptions
class DatabaseError(DatabaseException):
    status_code = 500
    error_type = "DATABASE ERROR"

    def __init__(self, message):
        super().__init__(message)


def database_errors_handler(
    request: Request,
    exc: DatabaseException
) -> JSONResponse:
    logger.exception(
        msg=exc.__cause__
    )
    
    return JSONResponse(
        status_code=exc.error_code,
        content={"error": exc.error_type, "message": exc.message}
    )