from pydantic import BaseModel, EmailStr
from typing import Optional

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    username: Optional[str] = None
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str