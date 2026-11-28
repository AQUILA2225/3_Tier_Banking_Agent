import pytest

from app.models import UserRole
from app.core.permissions import (
    Permission,
    ROLE_PERMISSIONS,
    get_role_permissions,
    has_permission,
    has_all_permissions
)

from app.api.deps import (
    require_roles,
    require_permissions
)

pytestmark = pytest.mark.unit

@pytest.mark.parametrize(
    "role, expected",
    [
        (
            UserRole.CUSTOMER,
            {
                Permission.PROFILE_READ,
                Permission.ACCOUNT_READ,
                Permission.BENEFICIARY_READ,
                Permission.BENEFICIARY_MANAGE,
                Permission.TRANSACTION_READ,
                Permission.TRANSFER_INITIATE,
                Permission.AGENT_USE
            }
        ),
        (
            UserRole.REVIEWER,
            {
                Permission.PROFILE_READ,
                Permission.REVIEW_READ,
                Permission.REVIEW_DECIDE
            }
        ),
        (
            UserRole.ADMIN,
            {
                Permission.PROFILE_READ,
                Permission.USER_READ,
                Permission.USER_MANAGE,
                Permission.AUDIT_READ
            }
        )
    ]
)
def test_exact_role_permissions(role, expected):

    assert get_role_permissions(role) == expected

@pytest.mark.parametrize(
    "role",
    ["CUSTOMER", "REVIEWER", "ADMIN"]
)
def test_all_roles_can_read_profile(role):

    assert has_permission(
        role,
        Permission.PROFILE_READ
    )


@pytest.mark.parametrize(
    "role",
    ["UNKNOWN", "", "customer", None]
)
def test_unknown_role_has_no_permissions(role):

    assert get_role_permissions(role) == frozenset()

    assert not has_permission(
        role,
        Permission.PROFILE_READ
    )

def test_invalid_permission_rejected():

    assert not has_permission(
        UserRole.CUSTOMER,
        "profile:read"
    )

def test_all_required_permissions_allowed():

    assert has_all_permissions(
        UserRole.CUSTOMER,
        Permission.ACCOUNT_READ,
        Permission.TRANSFER_INITIATE
    )

def test_missing_required_permission_denied():

    assert not has_all_permissions(
        UserRole.CUSTOMER,
        Permission.ACCOUNT_READ,
        Permission.REVIEW_DECIDE
    )

def test_empty_permission_check_denied():

    assert not has_all_permissions(
        UserRole.CUSTOMER
    )

def test_role_mapping_is_immutable():

    with pytest.raises(TypeError):

        ROLE_PERMISSIONS[UserRole.CUSTOMER] = (
            frozenset(Permission)
        )

def test_permission_collection_is_immutable():

    permissions = get_role_permissions(
        UserRole.CUSTOMER
    )

    with pytest.raises(AttributeError):

        permissions.add(
            Permission.REVIEW_DECIDE
        )

def test_empty_role_dependency_rejected():

    with pytest.raises(ValueError):

        require_roles()

def test_invalid_role_dependency_rejected():

    with pytest.raises(ValueError):

        require_roles("ADMIN")

def test_empty_permission_dependency_rejected():

    with pytest.raises(ValueError):

        require_permissions()

def test_invalid_permission_dependency_rejected():

    with pytest.raises(ValueError):

        require_permissions("profile:read")