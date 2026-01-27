"""Database setup and operations for number-adder service."""

import os
from datetime import datetime
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    """Get a database connection."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
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
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_premium BOOLEAN NOT NULL DEFAULT FALSE,
                stripe_customer_id TEXT,
                api_key_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Calculations table with CASCADE DELETE for GDPR compliance
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calculations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                operation TEXT NOT NULL DEFAULT 'add',
                num_a DOUBLE PRECISION NOT NULL,
                num_b DOUBLE PRECISION NOT NULL,
                result DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)


# User operations
def create_user(email: str, password_hash: str) -> int:
    """Create a new user and return their ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
            (email, password_hash)
        )
        return cursor.fetchone()["id"]


def get_user_by_email(email: str) -> dict | None:
    """Get user by email."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    """Get user by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, is_premium, stripe_customer_id, created_at FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def upgrade_user_to_premium(user_id: int) -> bool:
    """Upgrade a user to premium."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_premium = TRUE WHERE id = %s", (user_id,))
        return cursor.rowcount > 0


def set_stripe_customer_id(user_id: int, customer_id: str) -> bool:
    """Set the Stripe customer ID for a user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET stripe_customer_id = %s WHERE id = %s", (customer_id, user_id))
        return cursor.rowcount > 0


def get_user_by_stripe_customer_id(customer_id: str) -> dict | None:
    """Get user by Stripe customer ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, is_premium, stripe_customer_id, created_at FROM users WHERE stripe_customer_id = %s", (customer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_user(user_id: int) -> bool:
    """Delete a user and all their data (CASCADE DELETE handles calculations)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        return cursor.rowcount > 0


# Calculation operations
def save_calculation(user_id: int, num_a: float, num_b: float, result: float, operation: str = "add") -> int:
    """Save a calculation and return its ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO calculations (user_id, operation, num_a, num_b, result) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user_id, operation, num_a, num_b, result)
        )
        return cursor.fetchone()["id"]


def get_user_calculations(user_id: int) -> list[dict]:
    """Get all calculations for a user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, operation, num_a, num_b, result, created_at FROM calculations WHERE user_id = %s ORDER BY created_at DESC",
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
            "is_premium": bool(user["is_premium"]),
            "created_at": user["created_at"]
        },
        "calculations": calculations,
        "export_timestamp": datetime.now().isoformat()
    }


# API key operations
def set_api_key_hash(user_id: int, api_key_hash: str | None) -> bool:
    """Set or clear the API key hash for a user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET api_key_hash = %s WHERE id = %s",
            (api_key_hash, user_id)
        )
        return cursor.rowcount > 0


def get_user_by_api_key_hash(api_key_hash: str) -> dict | None:
    """Get user by API key hash."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email, is_premium, stripe_customer_id, created_at FROM users WHERE api_key_hash = %s",
            (api_key_hash,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def has_api_key(user_id: int) -> bool:
    """Check if a user has an API key set."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT api_key_hash FROM users WHERE id = %s",
            (user_id,)
        )
        row = cursor.fetchone()
        return row is not None and row["api_key_hash"] is not None
