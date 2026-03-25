"""Tests for organization multi-tenancy functionality."""

import pytest
from number_adder import database as db


@pytest.fixture
def test_user(test_db):
    """Create a test user and return their ID."""
    user_id = db.create_user("orgtest@example.com", "hashedpassword123")
    yield user_id
    # Cleanup handled by test_db fixture


@pytest.fixture
def second_user(test_db):
    """Create a second test user."""
    user_id = db.create_user("second@example.com", "hashedpassword456")
    yield user_id


@pytest.fixture
def third_user(test_db):
    """Create a third test user."""
    user_id = db.create_user("third@example.com", "hashedpassword789")
    yield user_id


class TestOrganizationCreation:
    """Tests for creating organizations."""

    def test_create_organization(self, test_user):
        """Creating an org should return an ID and add creator as admin."""
        org_id = db.create_organization("Test Org", test_user)

        assert org_id is not None
        assert isinstance(org_id, int)

        # Creator should be admin
        assert db.is_org_admin(org_id, test_user) is True
        assert db.is_org_member(org_id, test_user) is True

    def test_get_organization(self, test_user):
        """Should be able to retrieve org details."""
        org_id = db.create_organization("My Company", test_user)

        org = db.get_organization(org_id)

        assert org is not None
        assert org["id"] == org_id
        assert org["name"] == "My Company"
        assert org["created_at"] is not None

    def test_get_nonexistent_organization(self):
        """Getting a non-existent org should return None."""
        org = db.get_organization(99999)
        assert org is None

    def test_delete_organization(self, test_user):
        """Deleting an org should remove it and all memberships."""
        org_id = db.create_organization("To Delete", test_user)

        result = db.delete_organization(org_id)

        assert result is True
        assert db.get_organization(org_id) is None
        assert db.is_org_member(org_id, test_user) is False


class TestOrganizationUsers:
    """Tests for managing users in organizations."""

    def test_add_user_to_organization(self, test_user, second_user):
        """Adding a user to an org should work."""
        org_id = db.create_organization("Team Org", test_user)

        result = db.add_user_to_organization(org_id, second_user, "member")

        assert result is True
        assert db.is_org_member(org_id, second_user) is True

    def test_add_user_with_different_roles(self, test_user, second_user, third_user):
        """Users can be added with different roles."""
        org_id = db.create_organization("Role Test Org", test_user)

        db.add_user_to_organization(org_id, second_user, "manager")
        db.add_user_to_organization(org_id, third_user, "member")

        assert db.get_user_org_role(org_id, test_user) == "admin"
        assert db.get_user_org_role(org_id, second_user) == "manager"
        assert db.get_user_org_role(org_id, third_user) == "member"

    def test_add_user_duplicate_fails(self, test_user, second_user):
        """Adding the same user twice should fail."""
        org_id = db.create_organization("Dup Test", test_user)
        db.add_user_to_organization(org_id, second_user, "member")

        # Try to add again
        result = db.add_user_to_organization(org_id, second_user, "manager")

        assert result is False

    def test_add_user_invalid_role_raises(self, test_user, second_user):
        """Adding a user with invalid role should raise ValueError."""
        org_id = db.create_organization("Invalid Role Test", test_user)

        with pytest.raises(ValueError, match="Invalid role"):
            db.add_user_to_organization(org_id, second_user, "superadmin")

    def test_remove_user_from_organization(self, test_user, second_user):
        """Removing a user from org should work."""
        org_id = db.create_organization("Remove Test", test_user)
        db.add_user_to_organization(org_id, second_user, "member")

        result = db.remove_user_from_organization(org_id, second_user)

        assert result is True
        assert db.is_org_member(org_id, second_user) is False

    def test_update_user_role(self, test_user, second_user):
        """Updating a user's role should work."""
        org_id = db.create_organization("Update Role Test", test_user)
        db.add_user_to_organization(org_id, second_user, "member")

        result = db.update_user_org_role(org_id, second_user, "manager")

        assert result is True
        assert db.get_user_org_role(org_id, second_user) == "manager"

    def test_get_organization_users(self, test_user, second_user, third_user):
        """Should list all users in an org with their roles."""
        org_id = db.create_organization("List Users Test", test_user)
        db.add_user_to_organization(org_id, second_user, "manager")
        db.add_user_to_organization(org_id, third_user, "member")

        users = db.get_organization_users(org_id)

        assert len(users) == 3
        emails = {u["email"] for u in users}
        assert "orgtest@example.com" in emails
        assert "second@example.com" in emails
        assert "third@example.com" in emails

    def test_get_user_organizations(self, test_user, second_user):
        """Should list all orgs a user belongs to."""
        org1_id = db.create_organization("Org One", test_user)
        org2_id = db.create_organization("Org Two", test_user)

        # Add second_user to both orgs with different roles
        db.add_user_to_organization(org1_id, second_user, "member")
        db.add_user_to_organization(org2_id, second_user, "manager")

        orgs = db.get_user_organizations(second_user)

        assert len(orgs) == 2
        org_names = {o["name"] for o in orgs}
        assert "Org One" in org_names
        assert "Org Two" in org_names


class TestOrganizationPermissions:
    """Tests for permission check functions."""

    def test_is_org_admin(self, test_user, second_user):
        """is_org_admin should correctly identify admins."""
        org_id = db.create_organization("Admin Test", test_user)
        db.add_user_to_organization(org_id, second_user, "member")

        assert db.is_org_admin(org_id, test_user) is True
        assert db.is_org_admin(org_id, second_user) is False

    def test_is_org_manager(self, test_user, second_user, third_user):
        """is_org_manager should correctly identify managers."""
        org_id = db.create_organization("Manager Test", test_user)
        db.add_user_to_organization(org_id, second_user, "manager")
        db.add_user_to_organization(org_id, third_user, "member")

        assert db.is_org_manager(org_id, test_user) is False  # admin, not manager
        assert db.is_org_manager(org_id, second_user) is True
        assert db.is_org_manager(org_id, third_user) is False

    def test_is_org_member(self, test_user, second_user, third_user):
        """is_org_member should return True for any role."""
        org_id = db.create_organization("Member Test", test_user)
        db.add_user_to_organization(org_id, second_user, "manager")

        assert db.is_org_member(org_id, test_user) is True
        assert db.is_org_member(org_id, second_user) is True
        assert db.is_org_member(org_id, third_user) is False  # not in org

    def test_can_manage_org_users(self, test_user, second_user, third_user):
        """can_manage_org_users should return True for admin and manager."""
        org_id = db.create_organization("Manage Users Test", test_user)
        db.add_user_to_organization(org_id, second_user, "manager")
        db.add_user_to_organization(org_id, third_user, "member")

        assert db.can_manage_org_users(org_id, test_user) is True   # admin
        assert db.can_manage_org_users(org_id, second_user) is True  # manager
        assert db.can_manage_org_users(org_id, third_user) is False  # member


class TestCrossTenantIsolation:
    """Tests to verify users can't access other orgs' data."""

    def test_user_not_in_other_org(self, test_user, second_user):
        """User should not be member of org they weren't added to."""
        org1_id = db.create_organization("Org A", test_user)
        org2_id = db.create_organization("Org B", second_user)

        # test_user should only be in org1
        assert db.is_org_member(org1_id, test_user) is True
        assert db.is_org_member(org2_id, test_user) is False

        # second_user should only be in org2
        assert db.is_org_member(org1_id, second_user) is False
        assert db.is_org_member(org2_id, second_user) is True

    def test_get_user_organizations_isolation(self, test_user, second_user):
        """get_user_organizations should only return orgs user belongs to."""
        db.create_organization("User1 Org", test_user)
        db.create_organization("User2 Org", second_user)

        user1_orgs = db.get_user_organizations(test_user)
        user2_orgs = db.get_user_organizations(second_user)

        assert len(user1_orgs) == 1
        assert user1_orgs[0]["name"] == "User1 Org"

        assert len(user2_orgs) == 1
        assert user2_orgs[0]["name"] == "User2 Org"
