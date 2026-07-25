import secrets
from redis.asyncio import Redis
from redis.exceptions import RedisError
from src.exceptions import RedisStorageError
from src.auth.exceptions import TooManyVerificationAttemptsError, IncorrectCodeError
from src.auth.exceptions import CodeNotFoundError
from src.logger import logger


async def _verify_code(
    code_type: str,
    inputed_code: str,
    user_id: int,
    redis_client: Redis
) -> None:
    """Check verification code.
    
    Args:
        code_type: type of code, needs for redis.
        inputed_code: entered code by the user.
        user_id: id of user account in database.
        redis_client: object of class Redis.

    Returns:
        None if the check succeeds, and raises an error if something goes wrong.
    """

    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.get(f"email:{code_type}:{user_id}:code")
            pipe.get(f"email:{code_type}:{user_id}:attempts")
            result = await pipe.execute()
    except RedisError as e:
        raise RedisStorageError('Error with getting verification keys from redis.') from e

    verif_code_redis = result[0]
    verif_attempts_redis = result[1]

    if not verif_code_redis:
        raise CodeNotFoundError()
    
    if not verif_attempts_redis:
        logger.error(
            "Attempts key not found, but code key exists",
            user_id=user_id
        )
        raise RedisStorageError("Error with getting key with attempts counter from redis.")
    
    if int(verif_attempts_redis) >= 5:
        try:
            await redis_client.delete(f"email:{code_type}:{user_id}:code")
            await redis_client.delete(f"email:{code_type}:{user_id}:attempts")
        except RedisError as e:
            logger.exception(
                msg='error with deleting password reset keys from redis',
                error=str(e)
            )
        
        raise TooManyVerificationAttemptsError()
    
    # Ensure both are strings for comparison since we don't know if decode_responses=True is used in all environments
    if isinstance(verif_code_redis, bytes):
        verif_code_redis = verif_code_redis.decode('utf-8')
    if isinstance(inputed_code, bytes):
        inputed_code = inputed_code.decode('utf-8')
    if secrets.compare_digest(verif_code_redis, inputed_code):
        # Keep keys for 30 seconds so the user can retry if the service fails
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.expire(f"email:{code_type}:{user_id}:code", 30)
            pipe.expire(f"email:{code_type}:{user_id}:attempts", 30)
            await pipe.execute()
        return

    try:
        await redis_client.incr(f'email:{code_type}:{user_id}:attempts')
        raise IncorrectCodeError()
    except RedisError as e:
        raise RedisStorageError("Error with incrementing verify attempts in redis.") from e