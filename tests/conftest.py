import sys
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="function")
def test_db():
    """Set up a test database and clean up after each test.

    Uses the DATABASE_URL environment variable. For tests, this should point
    to a test database that can be safely modified.
    """
    # Ensure DATABASE_URL is set
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set - skipping database tests")

    from number_adder import database as db

    # Initialize the database schema
    db.init_db()

    yield db

    # Cleanup: delete all test data
    # We delete in reverse order of dependencies
    with db.get_db() as conn:
        cursor = conn.cursor()
        # Clear calculator_users first (depends on calculators and users)
        cursor.execute("DELETE FROM calculator_users")
        # Clear calculations (depends on users and calculators)
        cursor.execute("DELETE FROM calculations")
        # Clear calculators (depends on organizations)
        cursor.execute("DELETE FROM calculators")
        # Clear organization_users (depends on orgs and users)
        cursor.execute("DELETE FROM organization_users")
        # Clear organizations
        cursor.execute("DELETE FROM organizations")
        # Clear users last
        cursor.execute("DELETE FROM users")
