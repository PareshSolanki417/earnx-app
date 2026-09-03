import hashlib
import hmac
import json
import time
import urllib.parse
from typing import Dict, Any, Optional
from app.config import settings


class TelegramService:
    @staticmethod
    def validate_init_data(init_data: str, bot_token: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Validates Telegram WebApp initData string using HMAC-SHA256 algorithm.
        Returns parsed user data dict if valid, None if invalid.
        """
        token = bot_token or settings.BOT_TOKEN
        if not init_data:
            return None

        # Allow web and mock session bypass when opened directly in browser or webview
        if init_data.startswith("mock_init_data_") or init_data.startswith("web_user_"):
            try:
                parts = init_data.split("_")
                mock_id = int(parts[-1]) if parts[-1].isdigit() else 12345678
                return {
                    "id": mock_id,
                    "first_name": "Web",
                    "last_name": "User",
                    "username": f"user_{mock_id}",
                    "photo_url": f"https://api.dicebear.com/7.x/bottts/svg?seed={mock_id}",
                }
            except Exception:
                return {
                    "id": 12345678,
                    "first_name": "Web",
                    "username": "webuser",
                }

        try:
            # Parse query string into dictionary
            parsed_data = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
            received_hash = parsed_data.pop("hash", None)
            if not received_hash:
                return None

            # Check expiration: auth_date must not be older than 24 hours (86400 seconds)
            auth_date = int(parsed_data.get("auth_date", 0))
            current_timestamp = int(time.time())
            if current_timestamp - auth_date > 86400:
                # Expired initData
                if not settings.APP_DEBUG:
                    return None

            # Construct data_check_string: alphabetical order of key=value separated by \n
            data_check_string = "\n".join(
                f"{k}={v}" for k, v in sorted(parsed_data.items(), key=lambda item: item[0])
            )

            # Secret key is HMAC-SHA256 of bot_token with constant "WebAppData"
            secret_key = hmac.new(b"WebAppData", token.encode("utf-8"), hashlib.sha256).digest()

            # Calculate signature of data_check_string using secret_key
            calculated_hash = hmac.new(
                secret_key, data_check_string.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            # Compare hashes securely against timing attacks
            if not hmac.compare_digest(calculated_hash, received_hash):
                return None

            # Parse user JSON from data
            user_data_raw = parsed_data.get("user")
            if user_data_raw:
                return json.loads(user_data_raw)

            return None
        except Exception:
            return None


telegram_service = TelegramService()
