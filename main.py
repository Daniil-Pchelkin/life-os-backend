import os
import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Разрешаем запросы с любых сайтов (чтобы фронтенд на Vercel мог стучаться на бэкенд)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Получаем строку подключения к базе данных из переменных окружения Render
DATABASE_URL = os.getenv("DATABASE_URL")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Life OS API работает!"}

# Тестовый эндпоинт для проверки связи с базой данных Neon
@app.get("/test-db")
def test_db():
    try:
        # Подключаемся к базе данных по адресу из переменных окружения
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        db_version = cursor.fetchone()
        cursor.close()
        conn.close()
        return {
            "status": "success", 
            "message": "База данных подключена успешно!",
            "postgres_version": db_version[0]
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Ошибка подключения к базе: {str(e)}"
        }