import aiosqlite
import logging
from datetime import datetime
import os

class Database:
    def __init__(self):
        # Создаем папку data, если её нет
        os.makedirs('data', exist_ok=True)
        # Указываем путь к базе данных в папке data
        self.db_name = os.path.join('data', 'places.db')

    async def init(self):
        async with aiosqlite.connect(self.db_name) as db:
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    city TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Таблица мест
            await db.execute("""
                CREATE TABLE IF NOT EXISTS places (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    place_name TEXT,
                    address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            await db.commit()

    async def add_place(self, user_id: int, place_name: str, address: str):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "INSERT INTO places (user_id, place_name, address) VALUES (?, ?, ?)",
                (user_id, place_name, address)
            )
            await db.commit()

    async def get_user_places(self, user_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                "SELECT place_name, address FROM places WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ) as cursor:
                return await cursor.fetchall()

    async def add_user(self, user_id: int):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                (user_id,)
            )
            await db.commit()

    async def set_user_city(self, user_id: int, city: str):
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute(
                "UPDATE users SET city = ? WHERE user_id = ?",
                (city, user_id)
            )
            await db.commit()

    async def get_user_city(self, user_id: int) -> str:
        async with aiosqlite.connect(self.db_name) as db:
            async with db.execute(
                "SELECT city FROM users WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None 