from decimal import Decimal
from app.models.wallet import Wallet, WalletTransaction
from app.models.ad_event import AdEvent


def test_monetag_postback_10x_duplicate_idempotency(client, test_user, db_session):
    """
    CRITICAL TEST:
    If the exact same Monetag postback event is received 10 times,
    the user must receive the reward only ONCE.
    All subsequent 9 requests must return success (idempotent), but credit 0 additional coins.
    """
    wallet = db_session.query(Wallet).filter(Wallet.user_id == test_user.id).first()
    balance_start = Decimal(str(wallet.available_coins))

    unique_event_id = "monetag_test_repeat_event_99999"

    first_credited_coins = Decimal("0.0")

    # Send 10 identical postbacks
    for attempt in range(1, 11):
        response = client.post(
            "/api/monetag/postback",
            json={
                "sub_id": str(test_user.id),
                "event_id": unique_event_id,
                "zone_id": "zone_test_123",
                "payout": 0.005,
                "token": "valid_token",
            },
        )
        assert response.status_code == 200, f"Attempt {attempt} failed with {response.text}"
        data = response.json()
        assert data["success"] is True

        if attempt == 1:
            assert data["is_duplicate"] is False
            first_credited_coins = Decimal(str(data["coins_credited"]))
            assert first_credited_coins > 0, "First attempt should credit positive coins"
        else:
            # Attempts 2 through 10 must be recognized as duplicate and credit 0 coins
            assert data["is_duplicate"] is True, f"Attempt {attempt} was not flagged as duplicate"
            assert Decimal(str(data["coins_credited"])) == Decimal("0.0"), f"Attempt {attempt} credited coins again!"

    # Refresh wallet from DB to verify final balance
    db_session.expire_all()
    wallet_final = db_session.query(Wallet).filter(Wallet.user_id == test_user.id).first()
    expected_final_balance = balance_start + first_credited_coins

    assert Decimal(str(wallet_final.available_coins)) == expected_final_balance, (
        f"Expected {expected_final_balance} but found {wallet_final.available_coins}"
    )

    # Verify exactly 1 transaction exists in the ledger with this event ID
    tx_count = (
        db_session.query(WalletTransaction)
        .filter(WalletTransaction.external_event_id == f"monetag_{unique_event_id}")
        .count()
    )
    assert tx_count == 1, f"Expected exactly 1 ledger transaction, found {tx_count}"

    # Verify exactly 1 AdEvent record exists
    ad_count = (
        db_session.query(AdEvent)
        .filter(AdEvent.external_event_id == unique_event_id)
        .count()
    )
    assert ad_count == 1, f"Expected exactly 1 AdEvent record, found {ad_count}"
