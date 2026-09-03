from app.services.fraud_service import fraud_service
from app.models.user import User


def test_referral_stats_endpoint(client, user_auth_headers):
    res = client.get("/api/referral", headers=user_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "referral_code" in data
    assert "referral_link" in data
    assert "bonus_per_referral" in data


def test_self_referral_detection(db_session, test_user):
    # Attempting to refer using one's own referral code is blocked
    is_self = fraud_service.check_self_referral(
        db=db_session,
        user_telegram_id=test_user.telegram_id,
        referral_code=test_user.referral_code,
    )
    assert is_self is True
