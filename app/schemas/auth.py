from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class Token(BaseModel):
    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field(..., description="The type of token (e.g., bearer)")


class TokenData(BaseModel):
    email: Optional[str] = Field(None, description="The user's email encoded in the token")


class UserLogin(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., example="secure_password123")


class UserCreate(BaseModel):
    email: EmailStr = Field(..., example="newuser@example.com")
    password: str = Field(..., min_length=8, example="strong_pass_123")
    full_name: Optional[str] = Field(None, max_length=120, example="John Doe")
    age: Optional[int] = Field(None, ge=0, le=120, example=25)
    gender: Optional[str] = Field(None, pattern="^(Male|Female|Other)$", example="Male")
    weight_kg: Optional[float] = Field(None, gt=0, example=70.5)
    height_cm: Optional[float] = Field(None, gt=0, example=175.0)


class PasswordResetRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address to send the reset password to")
