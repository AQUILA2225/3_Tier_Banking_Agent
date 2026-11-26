"""harden banking database integrity

Revision ID: 39fdf701b3a8
Revises: 1e73a3119982
Create Date: 2026-11-26 20:23:09.302922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39fdf701b3a8'
down_revision: Union[str, Sequence[str], None] = '1e73a3119982'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_check_constraint(
        op.f("ck_accounts_finite_balance"),
        "accounts",
        "balance <> 'NaN'::numeric"
    )

    op.create_check_constraint(
        op.f("ck_transactions_finite_amount"),
        "transactions",
        "amount <> 'NaN'::numeric"
    )

    op.create_unique_constraint(
        "uq_accounts_id_user_id",
        "accounts",
        ["id", "user_id"]
    )

    op.create_unique_constraint(
        "uq_beneficiaries_id_user_account",
        "beneficiaries",
        ["id", "user_id", "account_id"]
    )

    op.create_unique_constraint(
        "uq_fraud_assessments_id_transaction",
        "fraud_assessments",
        ["id", "transaction_id"]
    )

    op.create_foreign_key(
        "fk_transactions_source_account_owner",
        "transactions",
        "accounts",
        ["source_account_id", "initiated_by"],
        ["id", "user_id"],
        ondelete="RESTRICT"
    )

    op.create_foreign_key(
        "fk_transactions_beneficiary_consistency",
        "transactions",
        "beneficiaries",
        [
            "beneficiary_id",
            "initiated_by",
            "destination_account_id"
        ],
        ["id", "user_id", "account_id"],
        ondelete="RESTRICT"
    )

    op.create_foreign_key(
        "fk_reviews_assessment_transaction",
        "reviews",
        "fraud_assessments",
        ["fraud_assessment_id", "transaction_id"],
        ["id", "transaction_id"],
        ondelete="RESTRICT"
    )


def downgrade() -> None:

    op.drop_constraint(
        "fk_reviews_assessment_transaction",
        "reviews",
        type_="foreignkey"
    )

    op.drop_constraint(
        "fk_transactions_beneficiary_consistency",
        "transactions",
        type_="foreignkey"
    )

    op.drop_constraint(
        "fk_transactions_source_account_owner",
        "transactions",
        type_="foreignkey"
    )

    op.drop_constraint(
        "uq_fraud_assessments_id_transaction",
        "fraud_assessments",
        type_="unique"
    )

    op.drop_constraint(
        "uq_beneficiaries_id_user_account",
        "beneficiaries",
        type_="unique"
    )

    op.drop_constraint(
        "uq_accounts_id_user_id",
        "accounts",
        type_="unique"
    )

    op.drop_constraint(
        op.f("ck_transactions_finite_amount"),
        "transactions",
        type_="check"
    )

    op.drop_constraint(
        op.f("ck_accounts_finite_balance"),
        "accounts",
        type_="check"
    )
