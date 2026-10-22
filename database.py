import sqlite3
from datetime import datetime

DB_NAME = "calories.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            meal_name TEXT,
            calories INTEGER,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def add_meal(telegram_id, meal_name, calories):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute(
        "INSERT INTO meals (telegram_id, meal_name, calories, created_at) VALUES (?, ?, ?, ?)",
        (telegram_id, meal_name, calories, now),
    )
    conn.commit()
    conn.close()


def get_today_meals(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT id, meal_name, calories, created_at FROM meals WHERE telegram_id = ? AND created_at LIKE ?",
        (telegram_id, f"{today}%"),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_today_total(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT COALESCE(SUM(calories), 0) FROM meals WHERE telegram_id = ? AND created_at LIKE ?",
        (telegram_id, f"{today}%"),
    )
    total = cursor.fetchone()[0]
    conn.close()
    return total


def delete_meal(meal_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
    conn.commit()
    conn.close()
