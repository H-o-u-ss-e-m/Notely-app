from typing import List, Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "student"  # 'student' ou 'teacher'

class UserCreateDTO(UserBase):
    password: str

class UserLoginDTO(BaseModel):
    email: EmailStr
    password: str

class UserResponseDTO(UserBase):
    id: str

    class Config:
        from_attributes = True

class TokenDTO(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponseDTO

class RefreshTokenRequestDTO(BaseModel):
    refresh_token: str
