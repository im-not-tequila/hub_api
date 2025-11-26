from fastapi import APIRouter, Request, Response, Depends

from app.services.auth_service import AuthService


from app.schemas import (NcalayerVerifyRequest, GetChallengeResponse, NcalayerVerifyResponse, PlatonusLoginRequest,
                      PlatonusLoginResponse, RefreshTokenResponse)

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_nitro_session, get_postgres_session, get_perco_session


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
async def ncalayer_verify(
        data: NcalayerVerifyRequest,
        response: Response,
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
        session_perco: AsyncSession = Depends(get_perco_session)
) -> NcalayerVerifyResponse:
    tokens, user = await AuthService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
        session_perco=session_perco
    ).ncalayer_verify(data)

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,  # ❗ JS не сможет прочитать
        secure=True,  # ❗ только по HTTPS (на dev можно False)
        samesite="none",  # ❗ для кросс-доменных запросов
        max_age=7 * 24 * 60 * 60,  # 7 дней
    )

    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,  # защищаем от XSS
        secure=True,  # только HTTPS
        samesite="none",
        max_age=60 * 60  # 1 час или сколько у тебя живет access токен
    )

    return NcalayerVerifyResponse(
        access_token=tokens.access_token,
        user=user,
    )


@router.post(
    path="/platonus/login",
    response_model=PlatonusLoginResponse
)
async def platonus_login(
        data: PlatonusLoginRequest,
        response: Response,
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
        session_perco: AsyncSession = Depends(get_perco_session)
):
    tokens, user = await AuthService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
        session_perco=session_perco
    ).platonus_login(data)

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,  # ❗ JS не сможет прочитать
        secure=True,  # ❗ только по HTTPS (на dev можно False)
        samesite="none",  # ❗ для кросс-доменных запросов
        max_age=7 * 24 * 60 * 60,  # 7 дней
    )

    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,  # защищаем от XSS
        secure=True,  # только HTTPS
        samesite="none",
        max_age=60 * 60  # 1 час или сколько у тебя живет access токен
    )

    return PlatonusLoginResponse(
        access_token=tokens.access_token,
        user=user,
    )


@router.post(
    path="/refresh_token",
    response_model=RefreshTokenResponse,
)
async def refresh_token(
        request: Request,
        response: Response,
        session_postgres: AsyncSession = Depends(get_postgres_session),
        session_nitro: AsyncSession = Depends(get_nitro_session),
        session_perco: AsyncSession = Depends(get_perco_session)
):
    """
    Обновление access токена по refresh токену.
    """

    refresh_token_cookie = request.cookies.get("refresh_token")
    new_access_token = await AuthService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
        session_perco=session_perco
    ).refresh_access_token(refresh_token_cookie)

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=60 * 60,  # 1 час
    )

    return RefreshTokenResponse(
        access_token=new_access_token,
        token_type="Bearer",
    )


@router.post(
    path="/logout"
)
def logout(response: Response):
    response.delete_cookie(key="refresh_token")
    response.delete_cookie(key="access_token")

    return {"message": "Logged out"}
