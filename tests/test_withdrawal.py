from decimal import Decimal
from app.services.wallet_service import wallet_service
from app.models.wallet import Wallet


def test_withdrawal_below_minimum_rejected(client, user_auth_headers):
    # Minimum is ₹50; requesting ₹20 must fail
    res = client.post(
        "/api/withdrawals",
        json={
            "amount_rupees": 20.0,
            "payout_method": "UPI",
            "payout_account": "user@upi",
        },
        headers=user_auth_headers,
    )
    assert res.status_code == 400
    assert "Minimum withdrawal amount is ₹50.00" in res.json()["detail"]


def test_withdrawal_insufficient_balance_rejected(client, user_auth_headers):
    # User only has 200 coins; requesting ₹50 requires 5,000 coins (at 100 coins/₹1)
    res = client.post(
        "/api/withdrawals",
        json={
            "amount_rupees": 50.0,
            "payout_method": "UPI",
            "payout_account": "user@upi",
        },
        headers=user_auth_headers,
    )
    assert res.status_code == 400
    assert "Insufficient balance" in res.json()["detail"]


def test_successful_withdrawal_and_refund_on_rejection(
    client, user_auth_headers, admin_auth_headers, test_user, db_session
):
    # Credit sufficient coins to test user (e.g. 10,000 coins)
    wallet_service.credit_coins(
        db=db_session,
        user_id=test_user.id,
        amount=Decimal("10000.0"),
        tx_type="ADJUSTMENT",
        source="TEST_SEED_FOR_WITHDRAWAL",
    )
    db_session.commit()

    # Submit valid ₹50 withdrawal
    res = client.post(
        "/api/withdrawals",
        json={
            "amount_rupees": 50.0,
            "payout_method": "UPI",
            "payout_account": "tester@okaxis",
            "account_holder_name": "Test User",
        },
        headers=user_auth_headers,
    )
    assert res.status_code == 200
    w_data = res.json()
    assert w_data["status"] == "PENDING"
    withdrawal_id = w_data["id"]

    # Verify 5,000 coins were deducted
    db_session.expire_all()
    wallet = db_session.query(Wallet).filter(Wallet.user_id == test_user.id).first()
    bal_after_withdrawal = Decimal(str(wallet.available_coins))

    # Admin rejects withdrawal -> must automatically refund 5,000 coins back
    action_res = client.post(
        f"/api/admin/withdrawals/{withdrawal_id}/action",
        json={
            "status": "REJECTED",
            "admin_notes": "Invalid UPI VPA handle",
        },
        headers=admin_auth_headers,
    )
    assert action_res.status_code == 200
    assert action_res.json()["status"] == "REJECTED"

    # Verify coins were refunded
    db_session.expire_all()
    wallet_after_refund = db_session.query(Wallet).filter(Wallet.user_id == test_user.id).first()
    assert Decimal(str(wallet_after_refund.available_coins)) == bal_after_withdrawal + Decimal("5000.0")
