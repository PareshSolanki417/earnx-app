from decimal import Decimal


def test_daily_bonus_claim_and_duplicate_prevention(client, user_auth_headers):
    # 1. Check status
    res = client.get("/api/tasks/daily-bonus/status", headers=user_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["can_claim_today"] is True
    assert len(data["days"]) == 7

    # 2. Claim bonus
    claim_res = client.post("/api/tasks/daily-bonus/claim", headers=user_auth_headers)
    assert claim_res.status_code == 200
    claim_data = claim_res.json()
    assert claim_data["success"] is True
    assert float(claim_data["coins_earned"]) > 0

    # 3. Attempting to claim again on the SAME day must fail
    dup_res = client.post("/api/tasks/daily-bonus/claim", headers=user_auth_headers)
    assert dup_res.status_code == 400
    assert "already claimed" in dup_res.json()["detail"].lower()
