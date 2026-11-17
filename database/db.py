"""
db.py

Opens a connection to our MySQL database.
Every other part of the project (loader, chatbot, agents, API)
will use get_connection() from here.

The login details come from the .env file, so the password is never written in the code.

Quick connection test:
    python -m database.db
"""

import os

import mysql.connector
from dotenv import load_dotenv

# Read the values from the .env file
load_dotenv()


def get_connection():
    """Open and return a new connection to MySQL."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "samsung_phones"),
        # utf8mb4 so symbols like €, £ and µm are saved correctly
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )


if __name__ == "__main__":
    # This part only runs when we start this file directly.
    # It's a small test to check that Python can log in to MySQL.
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DATABASE(), CURRENT_USER(), VERSION()")
    db_name, user, version = cursor.fetchone()

    print("✅ Connected to MySQL!")
    print("   Database :", db_name)
    print("   User     :", user)
    print("   Version  :", version)

    cursor.close()
    conn.close()