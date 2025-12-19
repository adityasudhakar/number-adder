"""Database setup and operations for number-adder service."""

import sqlite3
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

DATABASE_PATH = Path("number_adder.db")


def get_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize the database with tables."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Calculations table with CASCADE DELETE for GDPR compliance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                num_a REAL NOT NULL,
                num_b REAL NOT NULL,
                result REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # Enable foreign key support (required for CASCADE DELETE)
        cursor.execute("PRAGMA foreign_keys = ON")


# User operations
def create_user(email: str, password_hash: str) -> int:
    """Create a new user and return their ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        return cursor.lastrowid


def get_user_by_email(email: str) -> dict | None:
    """Get user by email."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    """Get user by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_user(user_id: int) -> bool:
    """Delete a user and all their data (CASCADE DELETE handles calculations)."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Enable foreign keys for this connection
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return cursor.rowcount > 0


# Calculation operations
def save_calculation(user_id: int, num_a: float, num_b: float, result: float) -> int:
    """Save a calculation and return its ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO calculations (user_id, num_a, num_b, result) VALUES (?, ?, ?, ?)",
            (user_id, num_a, num_b, result)
        )
        return cursor.lastrowid


def get_user_calculations(user_id: int) -> list[dict]:
    """Get all calculations for a user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, num_a, num_b, result, created_at FROM calculations WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]


# GDPR operations
def export_user_data(user_id: int) -> dict:
    """Export all user data for GDPR compliance."""
    user = get_user_by_id(user_id)
    if not user:
        return None

    calculations = get_user_calculations(user_id)

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "created_at": user["created_at"]
        },
        "calculations": calculations,
        "export_timestamp": datetime.now().isoformat()
    }
