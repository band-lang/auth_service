import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.auth.schemas import UserCreateRequest
from src.auth.services.registration_service import register_user_service
from src.auth.exceptions import EmailAlreadyExistsError
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from src.auth.models import User

async def test_register_email_exists():
    user_data = MagicMock(spec=UserCreateRequest)
    user_data.email = "test@example.com"
    user_data.password = SecretStr("mysecretpassword")

    db_session = MagicMock(spec=AsyncSession)
    redis_client = MagicMock(spec=Redis)

    with patch("src.auth.services.registration_service.get_user_by_email", new_callable=AsyncMock) as mock_get_user:
        mock_user = MagicMock(spec=User)
        mock_user.is_verified = True
        mock_get_user.return_value = mock_user

        try:
            await register_user_service(user_data, db_session, redis_client)
            print("Failed: Should raise EmailAlreadyExistsError")
        except EmailAlreadyExistsError:
            print("Success: Raised EmailAlreadyExistsError")
        except Exception as e:
            print(f"Failed with exception: {type(e)} - {e}")

asyncio.run(test_register_email_exists())
