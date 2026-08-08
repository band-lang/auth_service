from fastapi import Request
from fastapi.responses import JSONResponse
from src.exceptions import AppException, InternalServerException
from src.logger import logger


#Email custom exceptions
class EmailError(AppException):
    """Base email exception class"""
    status_code = 502
    error_type = "EMAIL ERROR"


#-----Temporary Errors-----#
class EmailTemporaryError(EmailError):
    """Email temporary error class"""


class EmailConnectionError(EmailTemporaryError):
    error_type = "EMAIL CONNECTION ERROR"

    def __init__(self, email: str) -> None:
        super().__init__(message=f"Email connection error: {email}")


class EmailTimeoutError(EmailTemporaryError):
    error_type = "EMAIL TIMEOUT ERROR"

    def __init__(self) -> None:
        super().__init__(message="Timeout connecting to mail server")


#-----Permanent Errors-----#
class EmailPermanentError(EmailError):
    """Email permanent error class"""
    pass


class EmailAuthError(EmailPermanentError):
    status_code = 500
    error_type = "EMAIL AUTH ERROR"

    def __init__(self) -> None:
        super().__init__(message="SMTP authentication failed.")


class EmailRecipientRefusedError(EmailPermanentError):
    status_code = 400
    error_type = "EMAIL RECIPIENT REFUSED ERROR"

    def __init__(self, email: str) -> None:
        super().__init__(message=f"Recipient refused: {email}")


class EmailSenderRefusedError(EmailPermanentError):
    status_code = 500
    error_type = "EMAIL SENDER REFUSED ERROR"

    def __init__(self) -> None:
        super().__init__(message=f'Sender refused error. Check .env file.')


#Exceptions for client
class CodeNotFoundError(AppException):
    status_code = 404
    error_type = "CODE NOT FOUND ERROR"

    def __init__(self) -> None:
        super().__init__(message="Code not found or expired.")


class CodeSendingRatelimitError(AppException):
    status_code = 429
    error_type = "CODE SENDING RATE LIMIT ERROR"

    def __init__(self) -> None:
        super().__init__(message="The code sending limit has been exceeded. Please, request a new code.")


class TooManyVerificationAttemptsError(AppException):
    status_code = 429
    error_type = "TOO MANY VERIFICATION ATTEMPTS ERROR"

    def __init__(self) -> None:
        super().__init__(message="Too many incorrect attempts. Please, request a new code.")


class IncorrectCodeError(AppException):
    status_code = 400
    error_type = "INCORRECT CODE ERROR"

    def __init__(self) -> None:
        super().__init__(message="Incorrect code.")


#User custom exceptions 
class BaseUserException(AppException):
    """Base user exception class."""
    pass


class EmailAlreadyExistsError(BaseUserException):
    status_code = 409
    error_type = 'EMAIL ALREADY EXISTS ERROR'

    def __init__(self) -> None:
        super().__init__(message="Email already exists.")


class InvalidCredentialsError(BaseUserException):
    status_code = 401
    error_type = 'INVALID CREDENTIALS ERROR'

    def __init__(self) -> None:
        super().__init__(message="Incorrect email or password.")


class PasswordNotChangedError(BaseUserException):
    status_code = 409
    error_type = 'PASSWORD CHANGING ERROR'

    def __init__(self) -> None:
        super().__init__(message='You entered your previous password.')


class UserNotVerifiedError(BaseUserException):
    status_code = 401
    error_type = 'USER NOT VERIFIED ERROR'

    def __init__(self) -> None:
        super().__init__(message='Your account is not verified. First, confirm your email.')


class UserAccountLimited(BaseUserException):
    status_code = 400
    error_type = "ACCOUNT SUSPICIOUS ERROR"

    def __init__(self) -> None:
        super().__init__(message='Account temporarily restricted due to suspicious activity. Please check your email.')


# Token custom exceptions
class BaseTokenException(AppException):
    """Base token exception class."""
    pass


class TokenDamagedError(BaseTokenException):
    """Token damaged exception class."""
    status_code = 401
    error_type = "TOKEN WAS DAMAGED ERROR"

    def __init__(self) -> None:
        super().__init__(message='Your token was damaged.')


class InvalidTokenError(BaseTokenException):
    """Invalid token exception class."""
    status_code = 401
    error_type = 'INVALID TOKEN ERROR'

    def __init__(self) -> None:
        super().__init__(message='You entered invalid token.')


class RefreshTokenRevokedError(BaseTokenException):
    """Refresh token revoked exception class."""
    status_code = 403
    error_type = 'REFRESH TOKEN REVOKED ERROR'

    def __init__(self) -> None:
        super().__init__(message='Refresh token revoked.')


# Internal server exceptions
class InvalidFieldNameError(InternalServerException):
    error_type = 'INVALID FIELD NAME ERROR'

    def __init__(self, transfered_field_name: str, allowed_fields: set[str]) -> None:
        super().__init__(
            message='Internal server error.',
            transfered_field_name=transfered_field_name,
            allowed_fields=allowed_fields
        )


#Handler
def app_exception_handler(
    request: Request,
    exc: AppException
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error_type, "message": exc.message}
    )


def internal_server_exception_handler(
    request: Request,
    exc: InternalServerException
) -> JSONResponse:
    logger.exception(
        msg='internal_server_error',
        error_type=exc.error_type,
        **exc.extra
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={'error': exc.error_type, 'message': exc.message}
    )