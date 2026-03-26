"""Tests for organization API endpoints."""

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
        "email": "apitest@example.com",
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


class TestCreateOrganization:
    """Tests for POST /organizations."""

    def test_create_organization_success(self, client, auth_headers):
        """Should create an organization and make creator admin."""
        response = client.post(
            "/organizations",
            json={"name": "Test Company"},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Company"
        assert data["role"] == "admin"
        assert data["is_admin"] is True
        assert data["can_invite"] is True

    def test_create_organization_unauthenticated(self, client):
        """Should reject unauthenticated requests."""
        response = client.post(
            "/organizations",
            json={"name": "Test Company"}
        )

        assert response.status_code == 401


class TestListOrganizations:
    """Tests for GET /organizations."""

    def test_list_organizations_empty(self, client, auth_headers):
        """Should return empty list when user has no orgs."""
        response = client.get("/organizations", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["organizations"] == []

    def test_list_organizations_with_orgs(self, client, auth_headers):
        """Should list orgs user belongs to."""
        # Create two orgs
        client.post("/organizations", json={"name": "Org One"}, headers=auth_headers)
        client.post("/organizations", json={"name": "Org Two"}, headers=auth_headers)

        response = client.get("/organizations", headers=auth_headers)

        assert response.status_code == 200
        orgs = response.json()["organizations"]
        assert len(orgs) == 2
        names = {o["name"] for o in orgs}
        assert "Org One" in names
        assert "Org Two" in names


class TestGetOrganization:
    """Tests for GET /organizations/{org_id}."""

    def test_get_organization_as_member(self, client, auth_headers):
        """Should return org details for members."""
        create_response = client.post(
            "/organizations",
            json={"name": "My Org"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        response = client.get(f"/organizations/{org_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Org"
        assert data["is_admin"] is True

    def test_get_organization_non_member(self, client, auth_headers, second_auth_headers):
        """Should reject non-members."""
        # First user creates org
        create_response = client.post(
            "/organizations",
            json={"name": "Private Org"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        # Second user tries to access
        response = client.get(f"/organizations/{org_id}", headers=second_auth_headers)

        assert response.status_code == 403

    def test_get_organization_not_found(self, client, auth_headers):
        """Should return 404 for non-existent org."""
        response = client.get("/organizations/99999", headers=auth_headers)

        assert response.status_code == 403  # 403 because user isn't member


class TestDeleteOrganization:
    """Tests for DELETE /organizations/{org_id}."""

    def test_delete_organization_as_admin(self, client, auth_headers):
        """Admin should be able to delete org."""
        create_response = client.post(
            "/organizations",
            json={"name": "To Delete"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        response = client.delete(f"/organizations/{org_id}", headers=auth_headers)

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify it's gone
        list_response = client.get("/organizations", headers=auth_headers)
        assert len(list_response.json()["organizations"]) == 0

    def test_delete_organization_as_non_admin(self, client, auth_headers, second_auth_headers):
        """Non-admin should not be able to delete org."""
        # First user creates org
        create_response = client.post(
            "/organizations",
            json={"name": "Protected Org"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        # Add second user as member
        client.post(
            f"/organizations/{org_id}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )

        # Second user tries to delete
        response = client.delete(f"/organizations/{org_id}", headers=second_auth_headers)

        assert response.status_code == 403


class TestOrganizationUsers:
    """Tests for organization user management endpoints."""

    def test_list_users_as_admin(self, client, auth_headers):
        """Admin should see user list."""
        create_response = client.post(
            "/organizations",
            json={"name": "Team Org"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        response = client.get(f"/organizations/{org_id}/users", headers=auth_headers)

        assert response.status_code == 200
        users = response.json()["users"]
        assert len(users) == 1
        assert users[0]["email"] == "apitest@example.com"
        assert users[0]["role"] == "admin"

    def test_list_users_as_member(self, client, auth_headers, second_auth_headers):
        """Member should not see user list."""
        create_response = client.post(
            "/organizations",
            json={"name": "Team Org"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        # Add second user as member
        client.post(
            f"/organizations/{org_id}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )

        # Member tries to list users
        response = client.get(f"/organizations/{org_id}/users", headers=second_auth_headers)

        assert response.status_code == 403

    def test_add_user_as_admin(self, client, auth_headers, second_auth_headers):
        """Admin should be able to add users."""
        create_response = client.post(
            "/organizations",
            json={"name": "Growing Org"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        response = client.post(
            f"/organizations/{org_id}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify user was added
        users_response = client.get(f"/organizations/{org_id}/users", headers=auth_headers)
        users = users_response.json()["users"]
        assert len(users) == 2
        emails = {u["email"] for u in users}
        assert "second@example.com" in emails

    def test_add_user_as_manager(self, client, auth_headers, second_auth_headers, third_auth_headers):
        """Manager should be able to add members but not admins."""
        create_response = client.post(
            "/organizations",
            json={"name": "Manager Test Org"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        # Add second user as manager
        client.post(
            f"/organizations/{org_id}/users",
            json={"email": "second@example.com", "role": "manager"},
            headers=auth_headers
        )

        # Manager adds third user as member - should work
        response = client.post(
            f"/organizations/{org_id}/users",
            json={"email": "third@example.com", "role": "member"},
            headers=second_auth_headers
        )
        assert response.status_code == 200

    def test_manager_cannot_add_admin(self, client, auth_headers, second_auth_headers, third_auth_headers):
        """Manager should not be able to add admins."""
        create_response = client.post(
            "/organizations",
            json={"name": "Escalation Test"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        # Add second user as manager
        client.post(
            f"/organizations/{org_id}/users",
            json={"email": "second@example.com", "role": "manager"},
            headers=auth_headers
        )

        # Manager tries to add admin - should fail
        response = client.post(
            f"/organizations/{org_id}/users",
            json={"email": "third@example.com", "role": "admin"},
            headers=second_auth_headers
        )
        assert response.status_code == 403

    def test_add_user_not_registered(self, client, auth_headers):
        """Should fail when trying to add unregistered user."""
        create_response = client.post(
            "/organizations",
            json={"name": "Add Nonexistent"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        response = client.post(
            f"/organizations/{org_id}/users",
            json={"email": "notregistered@example.com", "role": "member"},
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "register" in response.json()["detail"].lower()

    def test_remove_user(self, client, auth_headers, second_auth_headers):
        """Admin should be able to remove users."""
        create_response = client.post(
            "/organizations",
            json={"name": "Removal Test"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        # Add second user
        client.post(
            f"/organizations/{org_id}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )

        # Get second user's ID
        second_user = db.get_user_by_email("second@example.com")

        # Remove them
        response = client.delete(
            f"/organizations/{org_id}/users/{second_user['id']}",
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify they're gone
        users_response = client.get(f"/organizations/{org_id}/users", headers=auth_headers)
        assert len(users_response.json()["users"]) == 1

    def test_cannot_remove_self(self, client, auth_headers):
        """Admin should not be able to remove themselves."""
        create_response = client.post(
            "/organizations",
            json={"name": "Self Remove Test"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        # Get current user's ID
        user = db.get_user_by_email("apitest@example.com")

        response = client.delete(
            f"/organizations/{org_id}/users/{user['id']}",
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "yourself" in response.json()["detail"].lower()

    def test_update_user_role(self, client, auth_headers, second_auth_headers):
        """Admin should be able to change roles."""
        create_response = client.post(
            "/organizations",
            json={"name": "Role Change Test"},
            headers=auth_headers
        )
        org_id = create_response.json()["id"]

        # Add second user as member
        client.post(
            f"/organizations/{org_id}/users",
            json={"email": "second@example.com", "role": "member"},
            headers=auth_headers
        )

        # Get second user's ID
        second_user = db.get_user_by_email("second@example.com")

        # Promote to manager
        response = client.patch(
            f"/organizations/{org_id}/users/{second_user['id']}",
            json={"role": "manager"},
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify role changed
        users_response = client.get(f"/organizations/{org_id}/users", headers=auth_headers)
        second_user_data = next(
            u for u in users_response.json()["users"]
            if u["email"] == "second@example.com"
        )
        assert second_user_data["role"] == "manager"


class TestCrossTenantIsolationAPI:
    """Tests to verify API respects tenant boundaries."""

    def test_cannot_access_other_org(self, client, auth_headers, second_auth_headers):
        """User A cannot access Org B's data."""
        # User A creates org
        create_response = client.post(
            "/organizations",
            json={"name": "Org A"},
            headers=auth_headers
        )
        org_a_id = create_response.json()["id"]

        # User B creates their own org
        client.post(
            "/organizations",
            json={"name": "Org B"},
            headers=second_auth_headers
        )

        # User B tries to access Org A
        response = client.get(f"/organizations/{org_a_id}", headers=second_auth_headers)
        assert response.status_code == 403

    def test_cannot_add_users_to_other_org(self, client, auth_headers, second_auth_headers, third_auth_headers):
        """User A cannot add users to Org B."""
        # User A creates Org A
        client.post(
            "/organizations",
            json={"name": "Org A"},
            headers=auth_headers
        )

        # User B creates Org B
        create_response = client.post(
            "/organizations",
            json={"name": "Org B"},
            headers=second_auth_headers
        )
        org_b_id = create_response.json()["id"]

        # User A tries to add User C to Org B
        response = client.post(
            f"/organizations/{org_b_id}/users",
            json={"email": "third@example.com", "role": "member"},
            headers=auth_headers
        )

        assert response.status_code == 403
