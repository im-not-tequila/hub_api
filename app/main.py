from fastapi import FastAPI
from app.api.router import api_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Hub API",
    version="1.0.0"
)

origins = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
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

@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}
