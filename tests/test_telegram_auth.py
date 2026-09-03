import hashlib
import hmac
import json
import time
from app.services.telegram_service import telegram_service


def test_telegram_valid_hmac_validation():
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    auth_date = int(time.time())
    user_data = {"id": 99887766, "first_name": "Alice", "username": "alice_earnx"}
    user_str = json.dumps(user_data, separators=(",", ":"))

    params = {
        "auth_date": str(auth_date),
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": user_str,
    }

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    init_data = f"auth_date={auth_date}&query_id=AAHdF6IQAAAAAN0XohDhrOrc&user={user_str}&hash={calc_hash}"

    validated = telegram_service.validate_init_data(init_data, bot_token=bot_token)
    assert validated is not None
    assert validated["id"] == 99887766
    assert validated["username"] == "alice_earnx"


def test_telegram_tampered_data_rejected():
    bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    # An attacker altered the user id to someone else's id
    init_data = (
        'auth_date=1700000000&query_id=AAHdF6IQAAAAAN0XohDhrOrc&'
        'user={"id":11111111,"first_name":"Hacker"}&'
        'hash=0000000000000000000000000000000000000000000000000000000000000000'
    )
    validated = telegram_service.validate_init_data(init_data, bot_token=bot_token)
    assert validated is None


def test_mock_init_data_in_dev_mode():
    validated = telegram_service.validate_init_data("mock_init_data_user_55555")
    assert validated is not None
    assert validated["id"] == 55555
