from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.user.router import router as user_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/v1/auth", tags=["Auth"])
api_router.include_router(user_router, prefix="/v1/user", tags=["User"])
