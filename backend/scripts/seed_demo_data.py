from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    User,
    UserRole,
    Account,
    AccountType,
    AccountStatus,
    Beneficiary
)


DEMO_USERS = (
    ("Demo Customer One", "customer1@example.com", UserRole.CUSTOMER),
    ("Demo Customer Two", "customer2@example.com", UserRole.CUSTOMER),
    ("Demo Customer Three", "customer3@example.com", UserRole.CUSTOMER),
    ("Demo Reviewer", "reviewer@example.com", UserRole.REVIEWER),
    ("Demo Admin", "admin@example.com", UserRole.ADMIN),
)


DEMO_ACCOUNTS = (
    (
        "customer1@example.com",
        "100000000001",
        AccountType.SAVINGS,
        Decimal("100000.00")
    ),
    (
        "customer2@example.com",
        "100000000002",
        AccountType.SAVINGS,
        Decimal("50000.00")
    ),
    (
        "customer3@example.com",
        "100000000003",
        AccountType.CURRENT,
        Decimal("200000.00")
    ),
)


DEMO_BENEFICIARIES = (
    ("customer1@example.com", "100000000002", "Customer Two"),
    ("customer1@example.com", "100000000003", "Customer Three"),
    ("customer2@example.com", "100000000001", "Customer One"),
)


def seed_demo_data(db: Session) -> dict[str, int]:

    counts = {
        "users": 0,
        "accounts": 0,
        "beneficiaries": 0
    }

    users: dict[str, User] = {}
    accounts: dict[str, Account] = {}

    # 1. Seed users

    for full_name, email, role in DEMO_USERS:

        user = db.scalar(
            select(User).where(User.email == email)
        )

        if user is None:

            user = User(
                full_name=full_name,
                email=email,
                password_hash="!LOGIN_DISABLED",
                role=role.value
            )

            db.add(user)
            db.flush()

            counts["users"] += 1

        elif (
            user.full_name != full_name
            or user.role != role.value
        ):
            raise RuntimeError(
                f"Conflicting demo user: {email}"
            )

        users[email] = user

    # 2. Seed bank accounts

    for email, account_number, account_type, balance in DEMO_ACCOUNTS:

        account = db.scalar(
            select(Account).where(
                Account.account_number == account_number
            )
        )

        if account is None:

            account = Account(
                user_id=users[email].id,
                account_number=account_number,
                account_type=account_type.value,
                balance=balance,
                currency="INR",
                status=AccountStatus.ACTIVE.value
            )

            db.add(account)
            db.flush()

            counts["accounts"] += 1

        elif (
            account.user_id != users[email].id
            or account.account_type != account_type.value
            or account.currency != "INR"
        ):
            raise RuntimeError(
                f"Conflicting demo account: {account_number}"
            )

        accounts[account_number] = account

    # 3. Seed beneficiaries

    for email, account_number, nickname in DEMO_BENEFICIARIES:

        user = users[email]
        account = accounts[account_number]

        beneficiary = db.scalar(
            select(Beneficiary).where(
                Beneficiary.user_id == user.id,
                Beneficiary.account_id == account.id
            )
        )

        if beneficiary is None:

            beneficiary = Beneficiary(
                user_id=user.id,
                account_id=account.id,
                nickname=nickname
            )

            db.add(beneficiary)
            db.flush()

            counts["beneficiaries"] += 1

    return counts


def main() -> None:

    # Prevent execution outside local development.

    if (
        settings.app_env != "development"
        or settings.db_name != "banking_agent_db"
        or settings.db_user != "banking_app"
        or settings.db_host not in ("localhost", "127.0.0.1")
    ):
        raise RuntimeError(
            "Demo seeding is restricted to the local development database."
        )

    with SessionLocal.begin() as db:

        database_name, database_user = db.execute(
            text("select current_database(), current_user")
        ).one()

        if (
            database_name != "banking_agent_db"
            or database_user != "banking_app"
        ):
            raise RuntimeError(
                "Unsafe database connection."
            )

        # Prevent concurrent executions of this seed script.

        db.execute(
            text("select pg_advisory_xact_lock(317001)")
        )

        counts = seed_demo_data(db)

    print("Demo data seeding completed successfully.")

    for entity, count in counts.items():
        print(f"{entity.capitalize()} created: {count}")


if __name__ == "__main__":
    main()