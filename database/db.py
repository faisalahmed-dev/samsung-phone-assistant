"""MySQL connection helper. Credentials are read from the .env file.

Connection test:
    python -m database.db
"""

import os

import mysql.connector
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Open a new connection to the project database."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "samsung_phones"),
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )


if __name__ == "__main__":
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DATABASE(), CURRENT_USER(), VERSION()")
    db_name, user, version = cursor.fetchone()
    print(f"Connected to MySQL {version} as {user}, database: {db_name}")
    cursor.close()
    conn.close()