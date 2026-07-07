from typing import Annotated
from pydantic import BaseModel, Field, EmailStr, SecretStr


#User schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: Annotated[SecretStr, Field(min_length=8, max_length=256, examples=[">_BlSBz<PwG@]i0"])]