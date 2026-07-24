from typing import Annotated
from pydantic import BaseModel, Field, EmailStr, SecretStr


#User schemas
class UserCreateRequest(BaseModel):
    email: EmailStr
    password: Annotated[SecretStr, Field(min_length=8, max_length=256, examples=[">_BlSBz<PwG@]i0"])]


class CreateTokensRequest(BaseModel):
    user_id: int
    code: str = Field(min_length=8, max_length=8, json_schema_extra={"example": "12345678"})


class CreateTokensResponse(BaseModel):
    access_token: str
    refresh_token: str


class RefreshTokensRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    new_password: Annotated[SecretStr, Field(min_length=8, max_length=256, examples=[">_BlSBz<PwG@]i0"])]
    code: str = Field(min_length=8, max_length=8, json_schema_extra={"example": "12345678"})


class ChangeEmailInitRequest(BaseModel):
    new_email: EmailStr


class ChangeEmailRequest(BaseModel):
    old_email_code: str = Field(min_length=8, max_length=8, json_schema_extra={"example": "12345678"})
    new_email_code: str = Field(min_length=8, max_length=8, json_schema_extra={"example": "12345678"})


class UserInfo(BaseModel):
    user_agent: str | None
    ip_address: str | None