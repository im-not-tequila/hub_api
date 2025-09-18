from pydantic import BaseModel
from .user import UserResponse


class NcalayerVerifyRequest(BaseModel):
    signed_data: str
    original_data: str


class NcalayerVerifyResponse(BaseModel):
    access_token: str
    user: UserResponse


class PlatonusLoginRequest(BaseModel):
    login: str
    password: str


class PlatonusLoginResponse(BaseModel):
    access_token: str
    user: UserResponse


class GetChallengeResponse(BaseModel):
    challenge: str


class RefreshToken(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str
