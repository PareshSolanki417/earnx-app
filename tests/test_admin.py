from decimal import Decimal
from app.models.admin import AdminAction
from app.models.wallet import Wallet


def test_admin_login_success(client):
    res = client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "AdminEarnX2026!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data


def test_admin_login_failure(client):
    res = client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "WrongPassword!"},
    )
    assert res.status_code == 401


def test_admin_dashboard_metrics(client, admin_auth_headers):
    res = client.get("/api/admin/dashboard", headers=admin_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_users" in data
    assert "estimated_gross_revenue" in data
    assert "estimated_platform_margin" in data


def test_admin_balance_adjustment_and_audit_trail(
    client, admin_auth_headers, test_user, db_session
):
    wallet_before = db_session.query(Wallet).filter(Wallet.user_id == test_user.id).first()
    bal_before = Decimal(str(wallet_before.available_coins))

    # Perform +100 manual adjustment
    res = client.post(
        f"/api/admin/users/{test_user.id}/adjust",
        json={
            "amount_coins": 100.0,
            "reason": "Customer support courtesy credit",
        },
        headers=admin_auth_headers,
    )
    assert res.status_code == 200

    # Verify wallet was updated
    db_session.expire_all()
    wallet_after = db_session.query(Wallet).filter(Wallet.user_id == test_user.id).first()
    assert Decimal(str(wallet_after.available_coins)) == bal_before + Decimal("100.0")

    # Verify immutable audit log was created
    audit_log = (
        db_session.query(AdminAction)
        .filter(AdminAction.target_user_id == test_user.id)
        .order_by(AdminAction.id.desc())
        .first()
    )
    assert audit_log is not None
    assert audit_log.action_type == "BALANCE_ADJUSTMENT"
    assert "Customer support courtesy credit" in audit_log.details


def test_suspended_user_blocked(client, admin_auth_headers, user_auth_headers, test_user):
    # Admin suspends user
    res = client.post(
        f"/api/admin/users/{test_user.id}/status",
        json={"status": "SUSPENDED", "reason": "Violation of fair play"},
        headers=admin_auth_headers,
    )
    assert res.status_code == 200

    # User attempts to fetch profile or wallet -> must receive 403 Forbidden
    user_res = client.get("/api/user/me", headers=user_auth_headers)
    assert user_res.status_code == 403
    assert "suspended" in user_res.json()["detail"].lower()
