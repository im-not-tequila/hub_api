from fastapi import APIRouter, Request, Response, Depends

from app.services.auth_service import AuthService
from app.core.settings import get_settings

from app.schemas import (NcalayerVerifyRequest, GetChallengeResponse, NcalayerVerifyResponse, PlatonusLoginRequest,
                      PlatonusLoginResponse, RefreshTokenResponse)

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_nitro_session, get_postgres_session, get_perco_session

router = APIRouter()
settings = get_settings()


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    domain = settings.COOKIE_DOMAIN
    # secure=True только на проде (когда домен задан и есть HTTPS)
    # на localhost/127.0.0.1 secure=True блокируется браузером на HTTP
    secure = bool(domain)
    samesite = "lax"

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        domain=domain,
        max_age=7 * 24 * 60 * 60,
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        domain=domain,
        max_age=60 * 60,
    )


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

    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)

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

    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)

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
    refresh_token_cookie = request.cookies.get("refresh_token")
    new_access_token = await AuthService(
        session_postgres=session_postgres,
        session_nitro=session_nitro,
        session_perco=session_perco
    ).refresh_access_token(refresh_token_cookie)

    domain = settings.COOKIE_DOMAIN
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=bool(domain),
        samesite="lax",
        domain=domain,
        max_age=60 * 60,
    )

    return RefreshTokenResponse(
        access_token=new_access_token,
        token_type="Bearer",
    )


@router.post(
    path="/logout"
)
def logout(response: Response):
    domain = settings.COOKIE_DOMAIN
    response.delete_cookie(key="refresh_token", domain=domain)
    response.delete_cookie(key="access_token", domain=domain)

    return {"message": "Logged out"}
