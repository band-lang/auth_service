import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.auth.schemas import UserCreateRequest
from src.auth.services.registration_service import login_user_request_service
from src.auth.exceptions import UserNotFoundError
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

async def test_login_user_not_found():
    user_data = MagicMock(spec=UserCreateRequest)
    user_data.email = "test@example.com"
    user_data.password = SecretStr("mysecretpassword")

    db_session = MagicMock(spec=AsyncSession)
    redis_client = MagicMock(spec=Redis)

    with patch("src.auth.services.registration_service.get_user_by_email", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = None

        try:
            await login_user_request_service(user_data, db_session, redis_client)
            print("Failed: Should raise UserNotFoundError")
        except UserNotFoundError:
            print("Success: Raised UserNotFoundError")
        except Exception as e:
            print(f"Failed with exception: {type(e)} - {e}")

asyncio.run(test_login_user_not_found())
