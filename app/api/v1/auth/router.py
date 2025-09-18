from fastapi import APIRouter, Request, Response

from app.services.auth_service import AuthService


from app.schemas import (NcalayerVerifyRequest, GetChallengeResponse, NcalayerVerifyResponse, PlatonusLoginRequest,
                      PlatonusLoginResponse, RefreshTokenResponse)


router = APIRouter()


@router.get(
    path="/ncalayer/challenge",
    response_model=GetChallengeResponse
)
async def ncalayer_challenge():
    return GetChallengeResponse(
        challenge=await AuthService.ncalayer_challenge()
    )


@router.post(
    path="/ncalayer/verify",
    response_model=NcalayerVerifyResponse
)
async def ncalayer_verify(data: NcalayerVerifyRequest, response: Response) -> NcalayerVerifyResponse:
    tokens, user = await AuthService().ncalayer_verify(data)

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,  # ❗ JS не сможет прочитать
        secure=True,  # ❗ только по HTTPS (на dev можно False)
        samesite="none",  # ❗ для кросс-доменных запросов
        max_age=7 * 24 * 60 * 60,  # 7 дней
    )

    return NcalayerVerifyResponse(
        access_token=tokens.access_token,
        user=user,
    )


@router.post(
    path="/platonus/login",
    response_model=PlatonusLoginResponse
)
async def platonus_login(data: PlatonusLoginRequest, response: Response):
    tokens, user = await AuthService().platonus_login(data)

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,  # ❗ JS не сможет прочитать
        secure=True,  # ❗ только по HTTPS (на dev можно False)
        samesite="none",  # ❗ для кросс-доменных запросов
        max_age=7 * 24 * 60 * 60,  # 7 дней
    )

    return PlatonusLoginResponse(
        access_token=tokens.access_token,
        user=user,
    )


@router.post(
    path="/refresh_token",
    response_model=RefreshTokenResponse
)
async def refresh_token(request: Request):
    """
    Обновление access токена по refresh токену.
    """

    _refresh_token = request.cookies.get("refresh_token")
    new_access_token = await AuthService.refresh_access_token(_refresh_token)

    return RefreshTokenResponse(
        access_token=new_access_token,
        token_type="Bearer",
    )
