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

        # Calculators table - sub-resources within organizations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calculators (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_by_user_id INTEGER NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(organization_id, name)
            )
        """)

        # Calculator users table - maps users to calculators with roles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calculator_users (
                id SERIAL PRIMARY KEY,
                calculator_id INTEGER NOT NULL REFERENCES calculators(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK (role IN ('admin', 'operator', 'viewer')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(calculator_id, user_id)
            )
        """)

        # Indexes for calculator lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_calc_users_user_id ON calculator_users(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_calc_users_calc_id ON calculator_users(calculator_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_calculators_org_id ON calculators(organization_id)
        """)

        # Add calculator_id column to calculations table (if not exists)
        # This links calculations to specific calculators
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'calculations' AND column_name = 'calculator_id'
                ) THEN
                    ALTER TABLE calculations ADD COLUMN calculator_id INTEGER REFERENCES calculators(id) ON DELETE CASCADE;
                END IF;
            END $$;
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


def can_create_calculators(org_id: int, user_id: int) -> bool:
    """Check if user can create calculators (admin or manager)."""
    role = get_user_org_role(org_id, user_id)
    return role in ('admin', 'manager')


# =============================================================================
# Calculator operations (sub-resources within organizations)
# =============================================================================

def create_calculator(org_id: int, name: str, creator_user_id: int) -> int:
    """Create a new calculator within an org. Creator becomes admin. Returns calculator ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Create the calculator
        cursor.execute(
            "INSERT INTO calculators (organization_id, name, created_by_user_id) VALUES (%s, %s, %s) RETURNING id",
            (org_id, name, creator_user_id)
        )
        calc_id = cursor.fetchone()["id"]

        # Add creator as admin
        cursor.execute(
            "INSERT INTO calculator_users (calculator_id, user_id, role) VALUES (%s, %s, 'admin')",
            (calc_id, creator_user_id)
        )
        return calc_id


def get_calculator(calc_id: int) -> dict | None:
    """Get calculator by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.organization_id, c.name, c.created_by_user_id, c.created_at,
                   u.email as created_by_email
            FROM calculators c
            JOIN users u ON c.created_by_user_id = u.id
            WHERE c.id = %s
        """, (calc_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_organization_calculators(org_id: int, user_id: int) -> list[dict]:
    """Get all calculators in an org that a user has access to, with their role."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name, c.created_at,
                   cu.role,
                   u.email as created_by_email,
                   CASE WHEN cu.role = 'admin' THEN true ELSE false END as is_admin,
                   CASE WHEN cu.role IN ('admin', 'operator') THEN true ELSE false END as can_operate,
                   CASE WHEN cu.role IS NOT NULL THEN true ELSE false END as has_access
            FROM calculators c
            JOIN users u ON c.created_by_user_id = u.id
            LEFT JOIN calculator_users cu ON c.id = cu.calculator_id AND cu.user_id = %s
            WHERE c.organization_id = %s
            ORDER BY c.name
        """, (user_id, org_id))
        return [dict(row) for row in cursor.fetchall()]


def get_user_calculators(user_id: int) -> list[dict]:
    """Get all calculators a user has access to across all orgs."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.name, c.organization_id, c.created_at,
                   o.name as organization_name,
                   cu.role,
                   CASE WHEN cu.role = 'admin' THEN true ELSE false END as is_admin,
                   CASE WHEN cu.role IN ('admin', 'operator') THEN true ELSE false END as can_operate
            FROM calculators c
            JOIN calculator_users cu ON c.id = cu.calculator_id
            JOIN organizations o ON c.organization_id = o.id
            WHERE cu.user_id = %s
            ORDER BY o.name, c.name
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def delete_calculator(calc_id: int) -> bool:
    """Delete a calculator (CASCADE will remove calculator_users and calculations)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM calculators WHERE id = %s", (calc_id,))
        return cursor.rowcount > 0


# Calculator user management

def add_user_to_calculator(calc_id: int, user_id: int, role: str) -> bool:
    """Add a user to a calculator with the specified role."""
    if role not in ('admin', 'operator', 'viewer'):
        raise ValueError(f"Invalid role: {role}")

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO calculator_users (calculator_id, user_id, role) VALUES (%s, %s, %s)",
                (calc_id, user_id, role)
            )
            return True
        except psycopg2.IntegrityError:
            # User already has access
            return False


def remove_user_from_calculator(calc_id: int, user_id: int) -> bool:
    """Remove a user from a calculator."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM calculator_users WHERE calculator_id = %s AND user_id = %s",
            (calc_id, user_id)
        )
        return cursor.rowcount > 0


def update_user_calculator_role(calc_id: int, user_id: int, new_role: str) -> bool:
    """Update a user's role on a calculator."""
    if new_role not in ('admin', 'operator', 'viewer'):
        raise ValueError(f"Invalid role: {new_role}")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE calculator_users SET role = %s WHERE calculator_id = %s AND user_id = %s",
            (new_role, calc_id, user_id)
        )
        return cursor.rowcount > 0


def get_calculator_users(calc_id: int) -> list[dict]:
    """Get all users with access to a calculator."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.email, cu.role, cu.created_at as granted_at
            FROM users u
            JOIN calculator_users cu ON u.id = cu.user_id
            WHERE cu.calculator_id = %s
            ORDER BY cu.role, u.email
        """, (calc_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_user_calculator_role(calc_id: int, user_id: int) -> str | None:
    """Get a user's role on a calculator, or None if no access."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role FROM calculator_users WHERE calculator_id = %s AND user_id = %s",
            (calc_id, user_id)
        )
        row = cursor.fetchone()
        return row["role"] if row else None


# Calculator permission checks

def is_calculator_admin(calc_id: int, user_id: int) -> bool:
    """Check if user is an admin of the calculator."""
    role = get_user_calculator_role(calc_id, user_id)
    return role == 'admin'


def is_calculator_operator(calc_id: int, user_id: int) -> bool:
    """Check if user is an operator of the calculator."""
    role = get_user_calculator_role(calc_id, user_id)
    return role == 'operator'


def can_operate_calculator(calc_id: int, user_id: int) -> bool:
    """Check if user can perform calculations (admin or operator)."""
    role = get_user_calculator_role(calc_id, user_id)
    return role in ('admin', 'operator')


def can_view_calculator(calc_id: int, user_id: int) -> bool:
    """Check if user can view calculator (any role)."""
    role = get_user_calculator_role(calc_id, user_id)
    return role is not None


def can_manage_calculator(calc_id: int, user_id: int) -> bool:
    """Check if user can manage calculator settings and users (admin only)."""
    return is_calculator_admin(calc_id, user_id)


# Calculator-scoped calculations

def save_calculator_calculation(calc_id: int, user_id: int, num_a: float, num_b: float, result: float, operation: str = "add") -> int:
    """Save a calculation to a specific calculator."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO calculations (calculator_id, user_id, operation, num_a, num_b, result) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (calc_id, user_id, operation, num_a, num_b, result)
        )
        return cursor.fetchone()["id"]


def get_calculator_calculations(calc_id: int) -> list[dict]:
    """Get all calculations for a calculator."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT calc.id, calc.operation, calc.num_a, calc.num_b, calc.result, calc.created_at,
                   u.email as performed_by
            FROM calculations calc
            JOIN users u ON calc.user_id = u.id
            WHERE calc.calculator_id = %s
            ORDER BY calc.created_at DESC
        """, (calc_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_calculator_for_org(calc_id: int) -> int | None:
    """Get the organization ID for a calculator."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT organization_id FROM calculators WHERE id = %s", (calc_id,))
        row = cursor.fetchone()
        return row["organization_id"] if row else None
