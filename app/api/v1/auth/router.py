import secrets
import string
import base64

from fastapi import APIRouter, Request, HTTPException, Response

from app.services.auth_service import AuthService
from app.services import ncalayer
from app.db.session import redis_client, get_mysql_session
from app.dao.mysql import StudentDAO, TutorDAO

from .schemas import (NcalayerVerifyRequest, GetChallengeResponse, NcalayerVerifyResponse, PlatonusLoginRequest,
                      PlatonusLoginResponse, RefreshTokenResponse)

from app.schemas_internal import User


router = APIRouter()


@router.get("/ncalayer/challenge", response_model=GetChallengeResponse)
async def get_challenge():
    alphabet = string.ascii_letters + string.digits
    challenge_string = ''.join(secrets.choice(alphabet) for _ in range(16))
    challenge_bytes = challenge_string.encode('utf-8')
    base64_string = base64.b64encode(challenge_bytes).decode('utf-8')

    await redis_client.setex(
        name=base64_string,
        time=900,
        value=''
    )

    return {"challenge": base64_string}


@router.post("/ncalayer/verify", response_model=NcalayerVerifyResponse)
async def ncalayer_verify(data: NcalayerVerifyRequest, response: Response):
    redis_data = await redis_client.get(data.original_data)

    if redis_data is None:
        raise HTTPException(status_code=400, detail="Challenge expired")

    await redis_client.delete(data.original_data)

    is_valid_signature = ncalayer.check_signed_data(data.signed_data, data.original_data)

    if not is_valid_signature:
        raise HTTPException(status_code=400, detail="Invalid signature")

    user_ecp_info = ncalayer.extract_info(data.signed_data)

    if not user_ecp_info.iin_number:
        raise HTTPException(status_code=400, detail="IIN not found in certificate")

    user_model = await AuthService.authenticate_by_ecp(user_ecp_info)
    tokens = AuthService.create_tokens(user_model)
    print(user_ecp_info.model_dump())

    firstname = user_ecp_info.firstname
    lastname = user_ecp_info.lastname
    patronymic = user_ecp_info.patronymic

    result_user = User(
        id=user_model.id,
        firstname=firstname,
        lastname=lastname,
        patronymic=patronymic,
    )

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,  # ❗ JS не сможет прочитать
        secure=True,  # ❗ только по HTTPS (на dev можно False)
        samesite="none",  # ❗ для кросс-доменных запросов
        max_age=7 * 24 * 60 * 60,  # 7 дней
    )

    return {'access_token': tokens.access_token, 'user': result_user}


@router.post("/platonus/login", response_model=PlatonusLoginResponse)
async def platonus_login(data: PlatonusLoginRequest, response: Response):
    if not data.login.strip() or not data.password.strip():
        raise HTTPException(status_code=400, detail="Login or password is empty")

    user_model = await AuthService.authenticate_by_platonus(data.login, data.password)

    if user_model is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    tokens = AuthService.create_tokens(user_model)

    async with get_mysql_session() as mysql_session:
        if user_model.is_student:
            platonus_user = await StudentDAO(mysql_session).get_one_or_none(StudentID=user_model.platonus_id)
        else:
            platonus_user = await TutorDAO(mysql_session).get_one_or_none(TutorID=user_model.platonus_id)

        firstname = platonus_user.firstname
        lastname = platonus_user.lastname
        patronymic = platonus_user.patronymic

    result_user = User(
        id=user_model.id,
        firstname=firstname,
        lastname=lastname,
        patronymic=patronymic,
    )

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,  # ❗ JS не сможет прочитать
        secure=True,  # ❗ только по HTTPS (на dev можно False)
        samesite="none",  # ❗ для кросс-доменных запросов
        max_age=7 * 24 * 60 * 60,  # 7 дней
    )

    return {'access_token': tokens.access_token, 'user': result_user}


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: Request):
    """
    Обновление access токена по refresh токену.
    """

    _refresh_token = request.cookies.get("refresh_token")
    new_access_token = await AuthService.refresh_access_token(_refresh_token)

    return {"access_token": new_access_token, "token_type": "bearer"}
