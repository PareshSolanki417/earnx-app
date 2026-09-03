from decimal import Decimal
import pytest
from app.services.wallet_service import wallet_service
from app.models.wallet import Wallet


def test_credit_and_debit_ledger(db_session, test_user):
    wallet = db_session.query(Wallet).filter(Wallet.user_id == test_user.id).first()
    initial_balance = Decimal(str(wallet.available_coins))

    # Credit 50 coins
    tx1, is_new1 = wallet_service.credit_coins(
        db=db_session,
        user_id=test_user.id,
        amount=Decimal("50.0"),
        tx_type="AD_REWARD",
        source="TEST_AD",
        external_event_id="test_credit_unique_1",
    )
    assert is_new1 is True
    assert tx1.balance_before == initial_balance
    assert tx1.balance_after == initial_balance + Decimal("50.0")

    # Debit 30 coins
    tx2 = wallet_service.debit_coins(
        db=db_session,
        user_id=test_user.id,
        amount=Decimal("30.0"),
        tx_type="WITHDRAWAL",
        source="TEST_WITHDRAWAL",
    )
    assert tx2.balance_before == initial_balance + Decimal("50.0")
    assert tx2.balance_after == initial_balance + Decimal("20.0")


def test_insufficient_balance_rejection(db_session, test_user):
    # Attempting to debit more coins than available must raise ValueError
    with pytest.raises(ValueError, match="Insufficient balance"):
        wallet_service.debit_coins(
            db=db_session,
            user_id=test_user.id,
            amount=Decimal("999999.0"),
            tx_type="WITHDRAWAL",
            source="TEST_OVERDRAW",
        )


def test_wallet_api_endpoint(client, user_auth_headers):
    response = client.get("/api/wallet", headers=user_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "available_coins" in data
    assert "rupee_value" in data
    assert "coins_per_rupee" in data
