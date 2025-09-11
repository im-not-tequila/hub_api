from pydantic import BaseModel
from app.schemas_internal import User


class NcalayerVerifyRequest(BaseModel):
    signed_data: str
    original_data: str


class NcalayerVerifyResponse(BaseModel):
    access_token: str
    user: User


class GetChallengeResponse(BaseModel):
    challenge: str


class RefreshToken(BaseModel):
    refresh_token: str


class PlatonusLoginRequest(BaseModel):
    login: str
    password: str


class PlatonusLoginResponse(BaseModel):
    access_token: str
    user: User


class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str
