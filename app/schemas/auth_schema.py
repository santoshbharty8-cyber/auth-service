import uuid
import re
from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator



class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    id: str
    email: EmailStr
    status: str
    verification_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str

class TwoFactorRequiredResponse(BaseModel):
    require_2fa: bool = True
    mfa_token: str

class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class ResetRequest(BaseModel):
    email: str


class ResetConfirm(BaseModel):
    token: str
    new_password: str

class VerifyEmail(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr


class RequestOTPRequest(BaseModel):
    email: EmailStr


class LoginOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class OTPResponse(BaseModel):
    message: str
    otp: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str

class LoginStartRequest(BaseModel):
    email: EmailStr

class LoginPhoneOTPRequest(BaseModel):

    phone: str = Field(
        ...,
        example="+919876543210",
        description="Phone number used for OTP login"
    )

    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        example="482193",
        description="6-digit OTP code"
    )

class RequestPhoneOTPRequest(BaseModel):

    phone: str = Field(
        ...,
        pattern=r"^\+[1-9]\d{7,14}$"
    )

class Login2FARequest(BaseModel):

    mfa_token: str = Field(..., example="mfa_token")

    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        example="123456"
    )

class RecoveryCodeLoginRequest(BaseModel):

    mfa_token: str
    recovery_code: str