from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from src.auth.queries import get_refresh_tokens
from src.auth.models import User
from redis.asyncio import Redis
from redis.exceptions import RedisError
from src.exceptions import RedisStorageError, DatabaseError
from src.auth.exceptions import InvalidFieldNameError, PasswordNotChangedError, CodeNotFoundError
from src.auth.redis_helpers import create_verification_keys, create_change_email_keys, delete_all_access_tokens_user
from src.auth.services.verification_code_serivce import _verify_code
from src.auth.utils.email_utils import generate_code
from src.auth.utils.security_utils import hash_password, verify_password
from src.auth.schemas import ChangePasswordRequest, ChangeEmailRequest
from src.auth.constants import ALLOWED_UPDATE_FIELD_NAMES


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
            user.id,
            user.email,
            code,
            redis_client,
            code_type=code_type,
            job_func_name=job_func_name
        )
    except RedisError as e:
        raise RedisStorageError('Error with creating verification keys in redis.') from e
    
    return {"status": "Code for changing password was been sent.", "user_id": user.id}


async def change_email_request_service(
    user: User,
    new_email: str,
    redis_client: Redis
) -> dict[str, str | int]:
    """Service for sending two codes for changing email"""
    if user.email == new_email:
        # Change this on custom exception
        return {"status": "New email is the same as the current email."}

    old_code = generate_code()
    new_code = generate_code()

    try:
        await create_change_email_keys(
            user_id=user.id,
            old_email=user.email,
            new_email=new_email,
            old_code=old_code,
            new_code=new_code,
            redis_client=redis_client
        )
    except RedisError as e:
        raise RedisStorageError('Error with creating change email keys in redis.') from e

    return {"status": "Codes were sent to both emails.", "user_id": user.id}


async def _update_user_field_and_revoke_tokens(
    user: User,
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
    except SQLAlchemyError as e:
        await db_session.rollback()
        raise DatabaseError('Error with changing value in database.') from e
    except RedisError as e:
        await db_session.rollback()
        raise RedisStorageError('Error with deleting access tokens from redis.') from e
    
    return output_value


async def change_password_confirm_service(
    user: User,
    user_data: ChangePasswordRequest,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str]:

    await _verify_code(
        code_type="password_reset",
        inputed_code=user_data.code,
        user_id=user.id,
        redis_client=redis_client
    )

    hashed_password = hash_password(user_data.new_password.get_secret_value())

    if verify_password(user.password_hash, user_data.new_password.get_secret_value()):
        raise PasswordNotChangedError()

    return await _update_user_field_and_revoke_tokens(
        user=user,
        db_session=db_session,
        redis_client=redis_client,
        update_field_name='password_hash',
        new_value=hashed_password,
        output_value={'status': 'Password was been successfully reseted.'}
    )


async def change_email_confirm_service(
    user: User,
    user_data: ChangeEmailRequest,
    db_session: AsyncSession,
    redis_client: Redis
) -> dict[str, str]:

    await _verify_code(
        code_type="change_email_old",
        inputed_code=user_data.old_email_code,
        user_id=user.id,
        redis_client=redis_client
    )

    await _verify_code(
        code_type="change_email_new",
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
        db_session=db_session,
        redis_client=redis_client,
        update_field_name='email',
        new_value=pending_email,
        output_value={'status': 'Email was been successfully reseted.'}
    )