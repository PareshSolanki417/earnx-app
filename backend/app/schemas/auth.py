from typing import Optional
from pydantic import BaseModel, ConfigDict


class TelegramAuthRequest(BaseModel):
    init_data: str
    referral_code: Optional[str] = None


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthUserResponse(BaseModel):
    id: int
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    referral_code: str
    status: str
    risk_level: str

    model_config = ConfigDict(from_attributes=True)


class TelegramAuthResponse(BaseModel):
    token: TokenResponse
    user: AuthUserResponse
    is_new_user: bool = False
