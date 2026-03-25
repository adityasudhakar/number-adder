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

        # Organizations table (multi-tenancy)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Organization users table - maps users to orgs with roles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization_users (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('admin', 'manager', 'member')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(organization_id, user_id)
            )
        """)

        # Indexes for organization_users lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_org_users_user_id ON organization_users(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_org_users_org_id ON organization_users(organization_id)
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


# =============================================================================
# Organization operations (multi-tenancy)
# =============================================================================

def create_organization(name: str, creator_user_id: int) -> int:
    """Create a new organization and add the creator as admin. Returns org ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Create the organization
        cursor.execute(
            "INSERT INTO organizations (name) VALUES (%s) RETURNING id",
            (name,)
        )
        org_id = cursor.fetchone()["id"]

        # Add creator as admin
        cursor.execute(
            "INSERT INTO organization_users (organization_id, user_id, role) VALUES (%s, %s, 'admin')",
            (org_id, creator_user_id)
        )
        return org_id


def get_organization(org_id: int) -> dict | None:
    """Get organization by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, created_at FROM organizations WHERE id = %s",
            (org_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_organizations(user_id: int) -> list[dict]:
    """Get all organizations a user belongs to, with their role in each."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT o.id, o.name, o.created_at, ou.role
            FROM organizations o
            JOIN organization_users ou ON o.id = ou.organization_id
            WHERE ou.user_id = %s
            ORDER BY o.name
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def delete_organization(org_id: int) -> bool:
    """Delete an organization (CASCADE will remove org_users, calculators, etc.)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM organizations WHERE id = %s", (org_id,))
        return cursor.rowcount > 0


# Organization user management

def add_user_to_organization(org_id: int, user_id: int, role: str) -> bool:
    """Add a user to an organization with the specified role."""
    if role not in ('admin', 'manager', 'member'):
        raise ValueError(f"Invalid role: {role}")

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO organization_users (organization_id, user_id, role) VALUES (%s, %s, %s)",
                (org_id, user_id, role)
            )
            return True
        except psycopg2.IntegrityError:
            # User already in org
            return False


def remove_user_from_organization(org_id: int, user_id: int) -> bool:
    """Remove a user from an organization."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM organization_users WHERE organization_id = %s AND user_id = %s",
            (org_id, user_id)
        )
        return cursor.rowcount > 0


def update_user_org_role(org_id: int, user_id: int, new_role: str) -> bool:
    """Update a user's role in an organization."""
    if new_role not in ('admin', 'manager', 'member'):
        raise ValueError(f"Invalid role: {new_role}")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE organization_users SET role = %s WHERE organization_id = %s AND user_id = %s",
            (new_role, org_id, user_id)
        )
        return cursor.rowcount > 0


def get_organization_users(org_id: int) -> list[dict]:
    """Get all users in an organization with their roles."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.email, ou.role, ou.created_at as joined_at
            FROM users u
            JOIN organization_users ou ON u.id = ou.user_id
            WHERE ou.organization_id = %s
            ORDER BY ou.role, u.email
        """, (org_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_user_org_role(org_id: int, user_id: int) -> str | None:
    """Get a user's role in an organization, or None if not a member."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role FROM organization_users WHERE organization_id = %s AND user_id = %s",
            (org_id, user_id)
        )
        row = cursor.fetchone()
        return row["role"] if row else None


# Organization permission checks

def is_org_admin(org_id: int, user_id: int) -> bool:
    """Check if user is an admin of the organization."""
    role = get_user_org_role(org_id, user_id)
    return role == 'admin'


def is_org_manager(org_id: int, user_id: int) -> bool:
    """Check if user is a manager of the organization."""
    role = get_user_org_role(org_id, user_id)
    return role == 'manager'


def is_org_member(org_id: int, user_id: int) -> bool:
    """Check if user belongs to the organization (any role)."""
    role = get_user_org_role(org_id, user_id)
    return role is not None


def can_manage_org_users(org_id: int, user_id: int) -> bool:
    """Check if user can add/remove users (admin or manager)."""
    role = get_user_org_role(org_id, user_id)
    return role in ('admin', 'manager')
