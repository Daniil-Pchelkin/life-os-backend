import os
import psycopg2
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
# Модель данных, которую фронтенд будет отправлять при выполнении задачи
class ActivityComplete(BaseModel):
    telegram_id: int
    username: str = "Unknown"
    pillar_name: str  # Допустимые значения: mind, body, inner_state, finance, connections
    xp_gained: int    # Количество получаемого опыта (например, 50)

@app.post("/complete-activity")
def complete_activity(data: ActivityComplete):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # 1. Проверяем или создаем пользователя
        cursor.execute(
            """
            INSERT INTO users (telegram_id, username) 
            VALUES (%s, %s) 
            ON CONFLICT (telegram_id) 
            DO UPDATE SET username = EXCLUDED.username;
            """,
            (data.telegram_id, data.username)
        )
        
        # 2. Добавляем или обновляем опыт по конкретному столпу
        cursor.execute(
            """
            INSERT INTO user_pillars (telegram_id, pillar_name, level, xp) 
            VALUES (%s, %s, 1, %s)
            ON CONFLICT (telegram_id, pillar_name) 
            DO UPDATE SET xp = user_pillars.xp + %s
            RETURNING level, xp;
            """,
            (data.telegram_id, data.pillar_name, data.xp_gained, data.xp_gained)
        )
        result = cursor.fetchone()
        current_level, current_xp = result[0], result[1]
        
        # Простейшая формула уровня: каждые 100 XP повышают уровень
        new_level = (current_xp // 100) + 1
        if new_level > current_level:
            cursor.execute(
                "UPDATE user_pillars SET level = %s WHERE telegram_id = %s AND pillar_name = %s;",
                (new_level, data.telegram_id, data.pillar_name)
            )
            current_level = new_level

        # 3. Обновляем общий суммарный опыт пользователя
        cursor.execute(
            "UPDATE users SET total_xp = total_xp + %s WHERE telegram_id = %s;",
            (data.xp_gained, data.telegram_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "pillar": data.pillar_name,
            "level": current_level,
            "xp": current_xp,
            "next_level_xp": current_level * 100
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Ошибка при начислении опыта: {str(e)}"
        }