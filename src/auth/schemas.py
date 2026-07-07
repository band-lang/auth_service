from typing import Annotated
from pydantic import BaseModel, Field, EmailStr, SecretStr


#User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: Annotated[SecretStr, Field(min_length=8, max_length=256, examples=[">_BlSBz<PwG@]i0"])]


class UserVerifyRequest(BaseModel):
    user_id: int
    code: str = Field(min_length=8, max_length=8, json_schema_extra={"example": "password123"})


class UserVerifyResponse(BaseModel):
    access_token: str
    refresh_token: str


class UserInfo(BaseModel):
    user_agent: str | None
    ip_adress: str | None