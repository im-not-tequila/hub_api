#sqlacodegen mysql+pymysql://user:password@mysql-server:3306/db_name --tables table1,table2,table3 --outfile app/models/mysql/generated_models.py

import socket
import subprocess
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqladmin import Admin
from sqlalchemy.ext.asyncio import create_async_engine

from app.api.router import api_router
from app.db.postgres_connection import DATABASE_URL
from app.services.admin import (UserAdmin, DocumentAdmin, DocumentTypeGroupAdmin, DocumentTypeAdmin, UserInfoAdmin,
                                RoleAdmin, ApproverAdmin, RoleDocumentTypeGroupAdmin, UserRoleAdmin)
from app.core.settings import get_settings
from app.core.ssh_mysql_port import get_ssh_mysql_local_port


def wait_for_port(host, port, timeout=15):
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex((host, port)) == 0:
                return True
        time.sleep(0.5)
    raise TimeoutError(f"Port {port} on {host} not ready after {timeout}s")

settings = get_settings()


engine = create_async_engine(DATABASE_URL)


app = FastAPI(
    title="Hub API",
    version="1.0.0"
)

admin = Admin(app, engine)

origins = [
    "https://new.hub.shakarim.kz",  # фронтенд Vue
    "http://new.hub.shakarim.kz",
    "https://api.hub.shakarim.kz",  # если API дергает сам себя
    "http://api.hub.shakarim.kz",
    "http://localhost:5173",        # для локальной разработки
    "http://127.0.0.1:5173"
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
admin.add_view(UserRoleAdmin)
admin.add_view(RoleDocumentTypeGroupAdmin)
admin.add_view(DocumentAdmin)
admin.add_view(DocumentTypeGroupAdmin)
admin.add_view(DocumentTypeAdmin)
admin.add_view(RoleAdmin)
admin.add_view(UserInfoAdmin)
admin.add_view(ApproverAdmin)



ssh_proc = None  # глобально

@app.on_event("startup")
async def startup_event():
    global ssh_proc
    if settings.ssh_enabled:
        local_port = get_ssh_mysql_local_port()
        ssh_proc = subprocess.Popen([
            "ssh",
            "-i", settings.SSH_KEY_PATH,
            "-N",
            "-L", f"127.0.0.1:{local_port}:{settings.MYSQL_HOST}:{settings.MYSQL_PORT}",
            f"{settings.SSH_USER}@{settings.SSH_HOST}"
        ])

        wait_for_port("127.0.0.1", local_port)

@app.on_event("shutdown")
async def shutdown_event():
    global ssh_proc
    if ssh_proc:
        ssh_proc.terminate()

@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}
