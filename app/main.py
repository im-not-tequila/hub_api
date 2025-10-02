#sqlacodegen mysql+pymysql://user:password@mysql-server:3306/db_name --tables table1,table2,table3 --outfile app/models/mysql/generated_models.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqladmin import Admin
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.router import api_router
from app.db.postgres_connection import DATABASE_URL
from app.services.admin import (UserAdmin, DocumentAdmin, DocumentTypeGroupAdmin, DocumentTypeAdmin, UserInfoAdmin,
                                RoleAdmin, ApproverAdmin, RoleDocumentTypeGroupAdmin)


engine = create_async_engine(DATABASE_URL)


app = FastAPI(
    title="Hub API",
    version="1.0.0"
)

admin = Admin(app, engine)

origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://193.193.254.219:9999",
    "http://193.193.254.219"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Разрешённые домены
    allow_credentials=True,         # Разрешить куки и авторизацию
    allow_methods=["*"],            # Разрешить все методы (GET, POST, PUT, DELETE и т.д.)
    allow_headers=["*"],            # Разрешить любые заголовки
)

# Подключаем все роутеры
app.include_router(api_router)

admin.add_view(UserAdmin)
admin.add_view(DocumentAdmin)
admin.add_view(DocumentTypeGroupAdmin)
admin.add_view(DocumentTypeAdmin)
admin.add_view(UserInfoAdmin)
admin.add_view(RoleAdmin)
admin.add_view(ApproverAdmin)
admin.add_view(RoleDocumentTypeGroupAdmin)


@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}
