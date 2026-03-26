"""Tests for calculator API endpoints."""

import pytest
from fastapi.testclient import TestClient

from number_adder import database as db
from number_adder.server import app


@pytest.fixture
def client(test_db):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(test_db, client):
    """Register a user and return auth headers."""
    response = client.post("/register", json={
        "email": "calcapi@example.com",
        "password": "testpassword123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_auth_headers(test_db, client):
    """Register a second user and return auth headers."""
    response = client.post("/register", json={
        "email": "second@example.com",
        "password": "testpassword456"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def third_auth_headers(test_db, client):
    """Register a third user and return auth headers."""
    response = client.post("/register", json={
        "email": "third@example.com",
        "password": "testpassword789"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_org(client, auth_headers):
    """Create a test organization."""
    response = client.post(
        "/organizations",
        json={"name": "Test Org"},
        headers=auth_headers
    )
    return response.json()["id"]


class TestCreateCalculator:
    """Tests for POST /organizations/{org_id}/calculators."""

    def test_create_calculator_as_admin(self, client, auth_headers, test_org):
        """Org admin should be able to create calculator."""
        response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Sales Calculator"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Sales Calculator"
        assert data["role"] == "admin"
        assert data["is_admin"] is True
        assert data["can_operate"] is True

    def test_create_calculator_as_manager(self, client, auth_headers, second_auth_headers, test_org):
        """Org manager should be able to create calculator."""
        # Add second user as manager
        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "manager"},
            headers=auth_headers
        )

        response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Marketing Calculator"},
            headers=second_auth_headers
        )

        assert response.status_code == 200

    def test_create_calculator_as_member_fails(self, client, auth_headers, second_auth_headers, test_org):
        """Org member should not be able to create calculator."""
        # Add second user as member
        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )

        response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Member Calculator"},
            headers=second_auth_headers
        )

        assert response.status_code == 403

    def test_create_duplicate_calculator_name_fails(self, client, auth_headers, test_org):
        """Creating calculator with duplicate name should fail."""
        client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Duplicate"},
            headers=auth_headers
        )

        response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Duplicate"},
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()


class TestListCalculators:
    """Tests for listing calculators."""

    def test_list_org_calculators(self, client, auth_headers, test_org):
        """Should list calculators in an org."""
        client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Calc One"},
            headers=auth_headers
        )
        client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Calc Two"},
            headers=auth_headers
        )

        response = client.get(
            f"/organizations/{test_org}/calculators",
            headers=auth_headers
        )

        assert response.status_code == 200
        calcs = response.json()["calculators"]
        assert len(calcs) == 2

    def test_list_my_calculators(self, client, auth_headers, second_auth_headers):
        """Should list calculators user has access to across orgs."""
        # Create two orgs
        org1_response = client.post(
            "/organizations",
            json={"name": "Org A"},
            headers=auth_headers
        )
        org1 = org1_response.json()["id"]

        org2_response = client.post(
            "/organizations",
            json={"name": "Org B"},
            headers=second_auth_headers
        )
        org2 = org2_response.json()["id"]

        # Create calculators
        calc1_response = client.post(
            f"/organizations/{org1}/calculators",
            json={"name": "Org A Calc"},
            headers=auth_headers
        )
        calc1 = calc1_response.json()["id"]

        client.post(
            f"/organizations/{org2}/calculators",
            json={"name": "Org B Calc"},
            headers=second_auth_headers
        )

        # First user should only see their calculator
        response = client.get("/calculators", headers=auth_headers)
        assert response.status_code == 200
        calcs = response.json()["calculators"]
        assert len(calcs) == 1
        assert calcs[0]["name"] == "Org A Calc"

    def test_list_org_calculators_non_member_fails(self, client, auth_headers, second_auth_headers, test_org):
        """Non-org-member should not see calculators."""
        response = client.get(
            f"/organizations/{test_org}/calculators",
            headers=second_auth_headers
        )

        assert response.status_code == 403


class TestCalculatorOperations:
    """Tests for calculator add operation."""

    def test_add_as_operator(self, client, auth_headers, second_auth_headers, test_org):
        """Operator should be able to add numbers."""
        # Create calculator
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Math Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        # Add second user to org and calculator as operator
        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )
        client.post(
            f"/calculators/{calc_id}/users",
            json={"email": "second@example.com", "role": "operator"},
            headers=auth_headers
        )

        # Second user adds numbers
        response = client.post(
            f"/calculators/{calc_id}/add",
            json={"a": 5.0, "b": 3.0},
            headers=second_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == 8.0
        assert data["calculator_name"] == "Math Calc"

    def test_add_as_viewer_fails(self, client, auth_headers, second_auth_headers, test_org):
        """Viewer should not be able to add numbers."""
        # Create calculator
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "View Only Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        # Add second user as viewer
        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )
        client.post(
            f"/calculators/{calc_id}/users",
            json={"email": "second@example.com", "role": "viewer"},
            headers=auth_headers
        )

        # Second user tries to add
        response = client.post(
            f"/calculators/{calc_id}/add",
            json={"a": 5.0, "b": 3.0},
            headers=second_auth_headers
        )

        assert response.status_code == 403
        assert "operator or admin" in response.json()["detail"].lower()

    def test_add_no_access_fails(self, client, auth_headers, second_auth_headers, test_org):
        """User without access should not be able to add."""
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Private Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        response = client.post(
            f"/calculators/{calc_id}/add",
            json={"a": 5.0, "b": 3.0},
            headers=second_auth_headers
        )

        assert response.status_code == 403

    def test_org_admin_can_add_without_explicit_calculator_role(self, client, auth_headers, second_auth_headers, test_org):
        """Org admins should be able to use calculators without explicit calculator membership."""
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Org Admin Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "admin"},
            headers=auth_headers
        )

        response = client.post(
            f"/calculators/{calc_id}/add",
            json={"a": 4.0, "b": 6.0},
            headers=second_auth_headers
        )

        assert response.status_code == 200
        assert response.json()["result"] == 10.0


class TestCalculatorHistory:
    """Tests for calculator history."""

    def test_view_history_as_viewer(self, client, auth_headers, second_auth_headers, test_org):
        """Viewer should be able to see history."""
        # Create calculator and do some calculations
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "History Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        client.post(f"/calculators/{calc_id}/add", json={"a": 1.0, "b": 2.0}, headers=auth_headers)
        client.post(f"/calculators/{calc_id}/add", json={"a": 10.0, "b": 20.0}, headers=auth_headers)

        # Add second user as viewer
        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )
        client.post(
            f"/calculators/{calc_id}/users",
            json={"email": "second@example.com", "role": "viewer"},
            headers=auth_headers
        )

        # Viewer can see history
        response = client.get(f"/calculators/{calc_id}/history", headers=second_auth_headers)

        assert response.status_code == 200
        calcs = response.json()["calculations"]
        assert len(calcs) == 2

    def test_history_isolated_per_calculator(self, client, auth_headers, test_org):
        """History should be isolated per calculator."""
        calc1_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Calc A"},
            headers=auth_headers
        )
        calc1 = calc1_response.json()["id"]

        calc2_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Calc B"},
            headers=auth_headers
        )
        calc2 = calc2_response.json()["id"]

        # Add to calc1
        client.post(f"/calculators/{calc1}/add", json={"a": 1.0, "b": 1.0}, headers=auth_headers)
        client.post(f"/calculators/{calc1}/add", json={"a": 2.0, "b": 2.0}, headers=auth_headers)

        # Add to calc2
        client.post(f"/calculators/{calc2}/add", json={"a": 100.0, "b": 100.0}, headers=auth_headers)

        history1 = client.get(f"/calculators/{calc1}/history", headers=auth_headers).json()["calculations"]
        history2 = client.get(f"/calculators/{calc2}/history", headers=auth_headers).json()["calculations"]

        assert len(history1) == 2
        assert len(history2) == 1
        assert history2[0]["num_a"] == 100.0


class TestCalculatorUserManagement:
    """Tests for managing calculator users."""

    def test_add_user_to_calculator(self, client, auth_headers, second_auth_headers, test_org):
        """Admin should be able to add users."""
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Team Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        # Add second user to org first
        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )

        # Then add to calculator
        response = client.post(
            f"/calculators/{calc_id}/users",
            json={"email": "second@example.com", "role": "operator"},
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_add_non_org_member_fails(self, client, auth_headers, second_auth_headers, test_org):
        """Cannot add user who is not in the org."""
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Org Check Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        # Try to add second user who is NOT in the org
        response = client.post(
            f"/calculators/{calc_id}/users",
            json={"email": "second@example.com", "role": "operator"},
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "organization" in response.json()["detail"].lower()

    def test_list_calculator_users(self, client, auth_headers, second_auth_headers, test_org):
        """Admin should see user list."""
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "User List Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        response = client.get(f"/calculators/{calc_id}/users", headers=auth_headers)

        assert response.status_code == 200
        users = response.json()["users"]
        assert len(users) == 1
        assert users[0]["role"] == "admin"

    def test_list_calculator_users_non_admin_fails(self, client, auth_headers, second_auth_headers, test_org):
        """Non-admin should not see user list."""
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Private Users Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        # Add second user as operator
        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )
        client.post(
            f"/calculators/{calc_id}/users",
            json={"email": "second@example.com", "role": "operator"},
            headers=auth_headers
        )

        response = client.get(f"/calculators/{calc_id}/users", headers=second_auth_headers)

        assert response.status_code == 403

    def test_org_admin_can_add_user_to_calculator_without_explicit_membership(self, client, auth_headers, second_auth_headers, third_auth_headers, test_org):
        """Org admins should be able to manage calculator users without explicit calculator membership."""
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Org Admin Manage Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "admin"},
            headers=auth_headers
        )
        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "third@example.com", "role": "member"},
            headers=auth_headers
        )

        response = client.post(
            f"/calculators/{calc_id}/users",
            json={"email": "third@example.com", "role": "viewer"},
            headers=second_auth_headers
        )

        assert response.status_code == 200


class TestOrgAdminImplicitCalculatorAccess:
    """Tests for org-admin implicit access to calculators."""

    def test_org_admin_can_delete_calculator_without_explicit_membership(self, client, auth_headers, second_auth_headers, test_org):
        """Org admins should be able to delete calculators in their org."""
        calc_response = client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Delete Me"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "admin"},
            headers=auth_headers
        )

        response = client.delete(
            f"/calculators/{calc_id}",
            headers=second_auth_headers
        )

        assert response.status_code == 200

    def test_org_admin_calculator_listing_shows_admin_access(self, client, auth_headers, second_auth_headers, test_org):
        """Org admins should see calculator controls enabled in org calculator list."""
        client.post(
            f"/organizations/{test_org}/calculators",
            json={"name": "Marketing"},
            headers=auth_headers
        )

        client.post(
            f"/organizations/{test_org}/users",
            json={"email": "second@example.com", "role": "admin"},
            headers=auth_headers
        )

        response = client.get(
            f"/organizations/{test_org}/calculators",
            headers=second_auth_headers
        )

        assert response.status_code == 200
        calculators = response.json()["calculators"]
        assert len(calculators) == 1
        assert calculators[0]["role"] == "admin (org)"
        assert calculators[0]["is_admin"] is True
        assert calculators[0]["can_operate"] is True
        assert calculators[0]["has_access"] is True


class TestCrossCalculatorIsolation:
    """Tests to verify calculator isolation."""

    def test_cannot_access_other_org_calculator(self, client, auth_headers, second_auth_headers):
        """User cannot access calculator in org they're not in."""
        # First user creates org and calculator
        org_response = client.post(
            "/organizations",
            json={"name": "Private Org"},
            headers=auth_headers
        )
        org_id = org_response.json()["id"]

        calc_response = client.post(
            f"/organizations/{org_id}/calculators",
            json={"name": "Private Calculator"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        # Second user tries to access
        response = client.get(f"/calculators/{calc_id}", headers=second_auth_headers)
        assert response.status_code == 403

        response = client.post(
            f"/calculators/{calc_id}/add",
            json={"a": 1.0, "b": 1.0},
            headers=second_auth_headers
        )
        assert response.status_code == 403

    def test_cannot_add_users_to_other_calculator(self, client, auth_headers, second_auth_headers, third_auth_headers):
        """Cannot add users to calculator you don't admin."""
        org_response = client.post(
            "/organizations",
            json={"name": "Admin Test Org"},
            headers=auth_headers
        )
        org_id = org_response.json()["id"]

        calc_response = client.post(
            f"/organizations/{org_id}/calculators",
            json={"name": "Admin Test Calc"},
            headers=auth_headers
        )
        calc_id = calc_response.json()["id"]

        # Add second user to org and calc as operator
        client.post(
            f"/organizations/{org_id}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )
        client.post(
            f"/calculators/{calc_id}/users",
            json={"email": "second@example.com", "role": "operator"},
            headers=auth_headers
        )

        # Add third user to org
        client.post(
            f"/organizations/{org_id}/users",
            json={"email": "third@example.com", "role": "member"},
            headers=auth_headers
        )

        # Second user (operator) tries to add third user - should fail
        response = client.post(
            f"/calculators/{calc_id}/users",
            json={"email": "third@example.com", "role": "viewer"},
            headers=second_auth_headers
        )

        assert response.status_code == 403
