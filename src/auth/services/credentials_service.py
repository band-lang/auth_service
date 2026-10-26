from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from src.auth.queries import get_refresh_tokens, get_user_by_email
from src.auth.models import User
from redis.asyncio import Redis
from redis.exceptions import RedisError
from src.exceptions import RedisStorageError, DatabaseError 
from src.workers.queue import queue
from src.logger import logger
from src.auth.exceptions import InvalidFieldNameError, PasswordNotChangedError, CodeNotFoundError, EmailAlreadyExistsError
from src.auth.redis_helpers import create_verification_keys, create_change_email_keys, delete_all_access_tokens_user
from src.auth.services.verification_code_service import verify_code
from src.auth.utils.email_utils import generate_code
from src.auth.utils.security_utils import hash_password, verify_password
from src.auth.schemas import ChangePasswordRequest, ChangeEmailRequest, UserInfo
from src.auth.constants import ALLOWED_UPDATE_FIELD_NAMES, EmailJob, CodeTypes, UpdateFieldNames

async def change_password_request_service(
    user: User,
    redis_client: Redis,
    *,
    code_type: str,
    job_func_name: str
) -> dict[str, str | int]:
    """Service for sending code for changing password"""
    code = generate_code()

    try:
        await create_verification_keys(
            user_id=user.id,
            email=user.email,
            code=code,
            redis_client=redis_client,
            code_type=code_type,
            job_func_name=job_func_name
        )
    except RedisError as e:
        raise RedisStorageError('Error with creating verification keys in redis.') from e
    
    return {"status": "Code was been sent.", "user_id": user.id}


async def change_email_request_service(
    user: User,
    new_email: str,
    job_func_name: str,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str | int]:
    """Service for sending two codes for changing email"""
    if user.email.lower() == new_email.lower():
        return {"status": "New email is the same as the current email.", "user_id": user.id}

    exists = await get_user_by_email(new_email, db_session)

    if exists:
        raise EmailAlreadyExistsError()

    old_code = generate_code()
    new_code = generate_code()

    try:
        await create_change_email_keys(
            user_id=user.id,
            old_email=user.email,
            new_email=new_email,
            old_code=old_code,
            new_code=new_code,
            job_func_name=job_func_name,
            redis_client=redis_client
        )
    except RedisError as e:
        raise RedisStorageError('Error with creating change email keys in redis.') from e

    return {"status": "Codes were sent to both emails.", "user_id": user.id}


async def _update_user_field_and_revoke_tokens(
    user: User,
    user_info: UserInfo,
    db_session: AsyncSession,
    redis_client: Redis,
    *,
    update_field_name: str,
    new_value: str,
    output_value: dict[str, str]
) -> dict[str, str]:
    """Universal helper to update a user field, revoke tokens, and commit to DB.
    Does not handle verification logic."""

    if update_field_name not in ALLOWED_UPDATE_FIELD_NAMES:
        raise InvalidFieldNameError(
            transfered_field_name=update_field_name,
            allowed_fields=ALLOWED_UPDATE_FIELD_NAMES
        )

    try:
        setattr(user, update_field_name, new_value)

        refresh_tokens = await get_refresh_tokens(user_id=user.id, db_session=db_session)
        if refresh_tokens:
            for token in refresh_tokens:
                token.is_revoked = True

        await delete_all_access_tokens_user(
            user_id=user.id,
            redis_client=redis_client
        )

        await db_session.commit()
    except IntegrityError as e:
        await db_session.rollback()
        constraint = getattr(getattr(e, "orig", None), "constraint_name", None)
        if constraint and "email" in constraint:
            raise EmailAlreadyExistsError() from e
        raise DatabaseError("Error with changing value in database.") from e
    except SQLAlchemyError as e:
        await db_session.rollback()
        raise DatabaseError('Error with changing value in database.') from e
    except RedisError as e:
        await db_session.rollback()
        raise RedisStorageError('Error with deleting access tokens from redis.') from e

    try:
        await queue.enqueue(
            job_or_func=EmailJob.CHANGE_CREDENTIALS_NOTIFY,
            email=user.email,
            ip_address=user_info.ip_address,
            timeout=30,
            retries=3,
            retry_delay=2.0
        )
    except Exception as e:
        logger.error(
            "credentials_change_notification_enqueue_failed",
            user_id=user.id,
            error=str(e),
        )
    
    return output_value


async def change_password_confirm_service(
    user: User,
    user_info: UserInfo,
    user_data: ChangePasswordRequest,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str]:

    await verify_code(
        code_type=CodeTypes.PASSWORD_RESET,
        inputed_code=user_data.code,
        user_id=user.id,
        redis_client=redis_client
    )

    if verify_password(user.password_hash, user_data.new_password.get_secret_value()):
        raise PasswordNotChangedError()
    
    hashed_password = hash_password(user_data.new_password.get_secret_value())

    return await _update_user_field_and_revoke_tokens(
        user=user,
        user_info=user_info,
        db_session=db_session,
        redis_client=redis_client,
        update_field_name=UpdateFieldNames.PASSWORD_HASH,
        new_value=hashed_password,
        output_value={'status': 'Password has been successfully reset.'}
    )


async def change_email_confirm_service(
    user: User,
    user_info: UserInfo,
    user_data: ChangeEmailRequest,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str]:

    await verify_code(
        code_type=CodeTypes.CHANGE_EMAIL_OLD,
        inputed_code=user_data.old_email_code,
        user_id=user.id,
        redis_client=redis_client
    )

    await verify_code(
        code_type=CodeTypes.CHANGE_EMAIL_NEW,
        inputed_code=user_data.new_email_code,
        user_id=user.id,
        redis_client=redis_client
    )

    try:
        pending_email = await redis_client.get(f"email:change_email_pending_address:{user.id}")
        if not pending_email:
            raise CodeNotFoundError()
        pending_email = pending_email.decode('utf-8') if isinstance(pending_email, bytes) else pending_email
    except RedisError as e:
        raise RedisStorageError('Error retrieving pending email address') from e

    return await _update_user_field_and_revoke_tokens(
        user=user,
        user_info=user_info,
        db_session=db_session,
        redis_client=redis_client,
        update_field_name=UpdateFieldNames.EMAIL,
        new_value=pending_email,
        output_value={'status': 'Email has been successfully changed.'}
    )