"""Tests for calculator multi-tenancy functionality."""

import pytest
from number_adder import database as db


@pytest.fixture
def test_user(test_db):
    """Create a test user and return their ID."""
    user_id = db.create_user("calctest@example.com", "hashedpassword123")
    yield user_id


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


@pytest.fixture
def test_org(test_user):
    """Create a test organization."""
    org_id = db.create_organization("Test Org", test_user)
    yield org_id


class TestCalculatorCreation:
    """Tests for creating calculators."""

    def test_create_calculator(self, test_user, test_org):
        """Creating a calculator should return an ID and add creator as admin."""
        calc_id = db.create_calculator(test_org, "Sales Calculator", test_user)

        assert calc_id is not None
        assert isinstance(calc_id, int)

        # Creator should be admin
        assert db.is_calculator_admin(calc_id, test_user) is True
        assert db.can_view_calculator(calc_id, test_user) is True
        assert db.can_operate_calculator(calc_id, test_user) is True

    def test_get_calculator(self, test_user, test_org):
        """Should be able to retrieve calculator details."""
        calc_id = db.create_calculator(test_org, "Marketing Calculator", test_user)

        calc = db.get_calculator(calc_id)

        assert calc is not None
        assert calc["id"] == calc_id
        assert calc["name"] == "Marketing Calculator"
        assert calc["organization_id"] == test_org
        assert calc["created_by_email"] == "calctest@example.com"

    def test_get_nonexistent_calculator(self):
        """Getting a non-existent calculator should return None."""
        calc = db.get_calculator(99999)
        assert calc is None

    def test_delete_calculator(self, test_user, test_org):
        """Deleting a calculator should remove it."""
        calc_id = db.create_calculator(test_org, "To Delete", test_user)

        result = db.delete_calculator(calc_id)

        assert result is True
        assert db.get_calculator(calc_id) is None

    def test_calculator_unique_name_per_org(self, test_user, test_org):
        """Calculator names must be unique within an org."""
        db.create_calculator(test_org, "Unique Name", test_user)

        with pytest.raises(Exception):  # IntegrityError
            db.create_calculator(test_org, "Unique Name", test_user)

    def test_same_name_different_orgs(self, test_user, second_user):
        """Same calculator name can exist in different orgs."""
        org1 = db.create_organization("Org One", test_user)
        org2 = db.create_organization("Org Two", second_user)

        calc1 = db.create_calculator(org1, "Shared Name", test_user)
        calc2 = db.create_calculator(org2, "Shared Name", second_user)

        assert calc1 != calc2
        assert db.get_calculator(calc1)["name"] == "Shared Name"
        assert db.get_calculator(calc2)["name"] == "Shared Name"


class TestCalculatorUsers:
    """Tests for managing users on calculators."""

    def test_add_user_to_calculator(self, test_user, second_user, test_org):
        """Adding a user to a calculator should work."""
        calc_id = db.create_calculator(test_org, "Team Calc", test_user)

        result = db.add_user_to_calculator(calc_id, second_user, "operator")

        assert result is True
        assert db.can_view_calculator(calc_id, second_user) is True
        assert db.can_operate_calculator(calc_id, second_user) is True

    def test_add_user_with_different_roles(self, test_user, second_user, third_user, test_org):
        """Users can be added with different roles."""
        calc_id = db.create_calculator(test_org, "Role Test Calc", test_user)

        db.add_user_to_calculator(calc_id, second_user, "operator")
        db.add_user_to_calculator(calc_id, third_user, "viewer")

        assert db.get_user_calculator_role(calc_id, test_user) == "admin"
        assert db.get_user_calculator_role(calc_id, second_user) == "operator"
        assert db.get_user_calculator_role(calc_id, third_user) == "viewer"

    def test_add_user_duplicate_fails(self, test_user, second_user, test_org):
        """Adding the same user twice should fail."""
        calc_id = db.create_calculator(test_org, "Dup Test", test_user)
        db.add_user_to_calculator(calc_id, second_user, "operator")

        result = db.add_user_to_calculator(calc_id, second_user, "viewer")

        assert result is False

    def test_add_user_invalid_role_raises(self, test_user, second_user, test_org):
        """Adding a user with invalid role should raise ValueError."""
        calc_id = db.create_calculator(test_org, "Invalid Role Test", test_user)

        with pytest.raises(ValueError, match="Invalid role"):
            db.add_user_to_calculator(calc_id, second_user, "superuser")

    def test_remove_user_from_calculator(self, test_user, second_user, test_org):
        """Removing a user from calculator should work."""
        calc_id = db.create_calculator(test_org, "Remove Test", test_user)
        db.add_user_to_calculator(calc_id, second_user, "operator")

        result = db.remove_user_from_calculator(calc_id, second_user)

        assert result is True
        assert db.can_view_calculator(calc_id, second_user) is False

    def test_update_user_calculator_role(self, test_user, second_user, test_org):
        """Updating a user's role should work."""
        calc_id = db.create_calculator(test_org, "Update Role Test", test_user)
        db.add_user_to_calculator(calc_id, second_user, "viewer")

        result = db.update_user_calculator_role(calc_id, second_user, "operator")

        assert result is True
        assert db.get_user_calculator_role(calc_id, second_user) == "operator"

    def test_get_calculator_users(self, test_user, second_user, third_user, test_org):
        """Should list all users with access to calculator."""
        calc_id = db.create_calculator(test_org, "List Users Test", test_user)
        db.add_user_to_calculator(calc_id, second_user, "operator")
        db.add_user_to_calculator(calc_id, third_user, "viewer")

        users = db.get_calculator_users(calc_id)

        assert len(users) == 3
        emails = {u["email"] for u in users}
        assert "calctest@example.com" in emails
        assert "second@example.com" in emails
        assert "third@example.com" in emails


class TestCalculatorPermissions:
    """Tests for permission check functions."""

    def test_is_calculator_admin(self, test_user, second_user, test_org):
        """is_calculator_admin should correctly identify admins."""
        calc_id = db.create_calculator(test_org, "Admin Test", test_user)
        db.add_user_to_calculator(calc_id, second_user, "operator")

        assert db.is_calculator_admin(calc_id, test_user) is True
        assert db.is_calculator_admin(calc_id, second_user) is False

    def test_can_operate_calculator(self, test_user, second_user, third_user, test_org):
        """can_operate_calculator should return True for admin and operator."""
        calc_id = db.create_calculator(test_org, "Operate Test", test_user)
        db.add_user_to_calculator(calc_id, second_user, "operator")
        db.add_user_to_calculator(calc_id, third_user, "viewer")

        assert db.can_operate_calculator(calc_id, test_user) is True   # admin
        assert db.can_operate_calculator(calc_id, second_user) is True  # operator
        assert db.can_operate_calculator(calc_id, third_user) is False  # viewer

    def test_can_view_calculator(self, test_user, second_user, third_user, test_org):
        """can_view_calculator should return True for any role."""
        calc_id = db.create_calculator(test_org, "View Test", test_user)
        db.add_user_to_calculator(calc_id, second_user, "viewer")

        assert db.can_view_calculator(calc_id, test_user) is True
        assert db.can_view_calculator(calc_id, second_user) is True
        assert db.can_view_calculator(calc_id, third_user) is False  # no access


class TestCalculatorListing:
    """Tests for listing calculators."""

    def test_get_organization_calculators(self, test_user, second_user, test_org):
        """Should list calculators in org with user's access level."""
        # Add second user to org
        db.add_user_to_organization(test_org, second_user, "member")

        calc1 = db.create_calculator(test_org, "Calc One", test_user)
        calc2 = db.create_calculator(test_org, "Calc Two", test_user)

        # Give second user access to only calc1
        db.add_user_to_calculator(calc1, second_user, "operator")

        # Test user (admin) sees both
        calcs_for_admin = db.get_organization_calculators(test_org, test_user)
        assert len(calcs_for_admin) == 2

        # Second user sees both but only has access to one
        calcs_for_member = db.get_organization_calculators(test_org, second_user)
        assert len(calcs_for_member) == 2

        calc1_for_member = next(c for c in calcs_for_member if c["name"] == "Calc One")
        calc2_for_member = next(c for c in calcs_for_member if c["name"] == "Calc Two")

        assert calc1_for_member["has_access"] is True
        assert calc2_for_member["has_access"] is False

    def test_get_user_calculators(self, test_user, second_user):
        """Should list all calculators user has access to across orgs."""
        org1 = db.create_organization("Org A", test_user)
        org2 = db.create_organization("Org B", second_user)

        calc1 = db.create_calculator(org1, "Org A Calc", test_user)
        calc2 = db.create_calculator(org2, "Org B Calc", second_user)

        # Give test_user access to calc2
        db.add_user_to_calculator(calc2, test_user, "operator")

        calcs = db.get_user_calculators(test_user)

        assert len(calcs) == 2
        names = {c["name"] for c in calcs}
        assert "Org A Calc" in names
        assert "Org B Calc" in names


class TestCalculatorCalculations:
    """Tests for calculator-scoped calculations."""

    def test_save_calculator_calculation(self, test_user, test_org):
        """Should save calculation to specific calculator."""
        calc_id = db.create_calculator(test_org, "Math Calc", test_user)

        result_id = db.save_calculator_calculation(calc_id, test_user, 5.0, 3.0, 8.0, "add")

        assert result_id is not None

    def test_get_calculator_calculations(self, test_user, second_user, test_org):
        """Should retrieve calculations for a calculator."""
        calc_id = db.create_calculator(test_org, "History Calc", test_user)
        db.add_user_to_calculator(calc_id, second_user, "operator")

        db.save_calculator_calculation(calc_id, test_user, 1.0, 2.0, 3.0, "add")
        db.save_calculator_calculation(calc_id, second_user, 10.0, 5.0, 15.0, "add")

        calcs = db.get_calculator_calculations(calc_id)

        assert len(calcs) == 2
        # Most recent first
        assert calcs[0]["num_a"] == 10.0
        assert calcs[0]["performed_by"] == "second@example.com"
        assert calcs[1]["num_a"] == 1.0
        assert calcs[1]["performed_by"] == "calctest@example.com"

    def test_calculations_isolated_per_calculator(self, test_user, test_org):
        """Calculations should be isolated to their calculator."""
        calc1 = db.create_calculator(test_org, "Calc A", test_user)
        calc2 = db.create_calculator(test_org, "Calc B", test_user)

        db.save_calculator_calculation(calc1, test_user, 1.0, 1.0, 2.0, "add")
        db.save_calculator_calculation(calc1, test_user, 2.0, 2.0, 4.0, "add")
        db.save_calculator_calculation(calc2, test_user, 100.0, 100.0, 200.0, "add")

        calc1_history = db.get_calculator_calculations(calc1)
        calc2_history = db.get_calculator_calculations(calc2)

        assert len(calc1_history) == 2
        assert len(calc2_history) == 1


class TestCrossTenantCalculatorIsolation:
    """Tests to verify calculator isolation between orgs."""

    def test_user_cannot_see_other_org_calculators(self, test_user, second_user):
        """User should not see calculators from orgs they're not in."""
        org1 = db.create_organization("Org A", test_user)
        org2 = db.create_organization("Org B", second_user)

        db.create_calculator(org1, "Org A Calc", test_user)
        db.create_calculator(org2, "Org B Calc", second_user)

        # test_user's calculators should not include Org B's
        user_calcs = db.get_user_calculators(test_user)
        calc_names = {c["name"] for c in user_calcs}

        assert "Org A Calc" in calc_names
        assert "Org B Calc" not in calc_names

    def test_calculator_belongs_to_correct_org(self, test_user, test_org):
        """get_calculator_for_org should return correct org ID."""
        calc_id = db.create_calculator(test_org, "Org Check", test_user)

        org_id = db.get_calculator_for_org(calc_id)

        assert org_id == test_org
