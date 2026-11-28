from enum import Enum
from types import MappingProxyType
from typing import Mapping

from app.models import UserRole


class Permission(str, Enum):

    PROFILE_READ = "profile:read"

    ACCOUNT_READ = "account:read"

    BENEFICIARY_READ = "beneficiary:read"
    BENEFICIARY_MANAGE = "beneficiary:manage"

    TRANSACTION_READ = "transaction:read"
    TRANSFER_INITIATE = "transfer:initiate"

    AGENT_USE = "agent:use"

    REVIEW_READ = "review:read"
    REVIEW_DECIDE = "review:decide"

    USER_READ = "user:read"
    USER_MANAGE = "user:manage"

    AUDIT_READ = "audit:read"


ROLE_PERMISSIONS: Mapping[
    UserRole,
    frozenset[Permission]
] = MappingProxyType({

    UserRole.CUSTOMER: frozenset({

        Permission.PROFILE_READ,
        Permission.ACCOUNT_READ,
        Permission.BENEFICIARY_READ,
        Permission.BENEFICIARY_MANAGE,
        Permission.TRANSACTION_READ,
        Permission.TRANSFER_INITIATE,
        Permission.AGENT_USE

    }),

    UserRole.REVIEWER: frozenset({

        Permission.PROFILE_READ,
        Permission.REVIEW_READ,
        Permission.REVIEW_DECIDE

    }),

    UserRole.ADMIN: frozenset({

        Permission.PROFILE_READ,
        Permission.USER_READ,
        Permission.USER_MANAGE,
        Permission.AUDIT_READ

    })

})


def get_role_permissions(
    role: UserRole | str
) -> frozenset[Permission]:

    try:

        normalized_role = UserRole(role)

    except (ValueError, TypeError):

        return frozenset()

    return ROLE_PERMISSIONS.get(
        normalized_role,
        frozenset()
    )


def has_permission(
    role: UserRole | str,
    permission: Permission
) -> bool:

    if not isinstance(permission, Permission):

        return False

    return permission in get_role_permissions(role)


def has_all_permissions(
    role: UserRole | str,
    *permissions: Permission
) -> bool:

    if not permissions:

        return False

    return all(
        has_permission(role, permission)
        for permission in permissions
    )