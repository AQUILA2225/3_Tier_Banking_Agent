from sqlalchemy.orm import configure_mappers

from app.models import (
    User,
    Account,
    Beneficiary,
    Transaction,
    FraudAssessment,
    Review,
    AuditLog
)


def test_model_relationship_configuration():
    configure_mappers()


def test_bidirectional_relationships():
    user = User()
    recipient = User()

    source = Account(owner=user)
    destination = Account(owner=recipient)

    beneficiary = Beneficiary(
        owner=user,
        account=destination
    )

    transaction = Transaction(
        initiator=user,
        source_account=source,
        destination_account=destination,
        beneficiary=beneficiary
    )

    assessment = FraudAssessment(
        transaction=transaction
    )

    review = Review(
        transaction=transaction,
        fraud_assessment=assessment
    )

    audit = AuditLog(
        user=user,
        transaction=transaction
    )

    assert source in user.accounts
    assert destination in recipient.accounts
    assert beneficiary in user.beneficiaries
    assert beneficiary in destination.beneficiaries
    assert transaction in user.initiated_transactions
    assert transaction in source.outgoing_transactions
    assert transaction in destination.incoming_transactions
    assert transaction in beneficiary.transactions
    assert assessment in transaction.fraud_assessments
    assert review in transaction.reviews
    assert review in assessment.reviews
    assert audit in user.audit_logs
    assert audit in transaction.audit_logs

    review.reviewer = recipient

    assert review in recipient.reviews