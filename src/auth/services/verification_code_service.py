from redis.asyncio import Redis
from redis.exceptions import RedisError
from src.exceptions import RedisStorageError
from src.auth.exceptions import TooManyVerificationAttemptsError, IncorrectCodeError
from src.auth.exceptions import CodeNotFoundError
from src.logger import logger


async def verify_code(
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
        logger.warning(
            "Attempts key not found, but code key exists",
            user_id=user_id
        )
        try:
            await redis_client.delete(f"email:{code_type}:{user_id}:code")
        except RedisError as e:
            logger.exception(
                msg='error with deleting changing credentials keys from redis',
                error=str(e)
            )
        raise RedisStorageError("Error with getting key with attempts counter from redis.")
    
    if int(verif_attempts_redis) > 5:
        try:
            async with redis_client.pipeline(transaction=True) as pipe:
                pipe.delete(f"email:{code_type}:{user_id}:code")
                pipe.delete(f"email:{code_type}:{user_id}:attempts")
                await pipe.execute()
        except RedisError as e:
            logger.exception(
                msg='error with deleting changing credentials keys from redis',
                error=str(e)
            )
        
        raise TooManyVerificationAttemptsError()
    
    if verif_code_redis == inputed_code:
        try:
            async with redis_client.pipeline(transaction=True) as pipe:
                pipe.delete(f"email:{code_type}:{user_id}:code")
                pipe.delete(f"email:{code_type}:{user_id}:attempts")
                await pipe.execute()
        except RedisError as e:
            raise RedisStorageError("Error with deleting credentials keys from redis.") from e
        return

    try:
        await redis_client.incr(f'email:{code_type}:{user_id}:attempts')
    except RedisError as e:
        raise RedisStorageError("Error with incrementing verify attempts in redis.") from e
    raise IncorrectCodeError()