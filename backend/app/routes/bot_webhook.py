import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, BackgroundTasks
import httpx

from app.config import settings

logger = logging.getLogger("earnx.bot_webhook")

router = APIRouter(prefix="/telegram", tags=["Telegram Webhook"])


async def send_telegram_reply(chat_id: int, text: str, reply_markup: Optional[dict] = None):
    """Sends a message back to the user via Telegram Bot HTTP API."""
    token = settings.BOT_TOKEN
    if not token or "demo_" in token:
        token = "8941202680:AAEe1DbfYdRpdUGkjpI1nEI4di0kFqQ3q7E"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning("Telegram sendMessage failed: %s", resp.text)
    except Exception as e:
        logger.error("Error sending Telegram message: %s", e)


@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Receives live updates from Telegram when users send /start or interact with the bot.
    Processes commands and responds instantly with the Mini App WebApp button.
    """
    try:
        data = await request.json()
    except Exception:
        return {"ok": True}

    message = data.get("message")
    if not message:
        return {"ok": True}

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    user_info = message.get("from", {})
    first_name = user_info.get("first_name", "Friend")

    if not chat_id:
        return {"ok": True}

    if text.startswith("/start"):
        # Check if referral code was passed, e.g. /start EARN123456
        parts = text.split()
        ref_code = parts[1].strip().upper() if len(parts) > 1 else None

        base_url = settings.WEBAPP_URL.rstrip("/")
        app_url = f"{base_url}/?startapp={ref_code}" if ref_code else f"{base_url}/"

        reply_text = (
            f"👋 <b>Hello, {first_name}!</b>\n\n"
            "Welcome to <b>EarnX</b> — The premier ad-supported reward platform.\n\n"
            "🪙 <b>How to Earn:</b>\n"
            "• 🎬 <b>Watch & Earn:</b> Watch sponsor videos for instant coins\n"
            "• 🎁 <b>Daily Streak:</b> Claim consecutive 7-day bonuses\n"
            "• 📋 <b>Tasks:</b> Complete simple sponsor missions\n"
            "• 👥 <b>Referrals:</b> Invite friends and get +50 coins\n\n"
            "💳 <i>Redeem your coins directly to UPI or Bank Transfer!</i>"
        )

        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "🚀 Open EarnX App",
                        "web_app": {"url": app_url}
                    }
                ],
                [
                    {
                        "text": "📢 Channel",
                        "url": "https://t.me/EarnXOfficial"
                    },
                    {
                        "text": "💬 Support",
                        "url": "https://t.me/EarnXSupportBot"
                    }
                ]
            ]
        }

        background_tasks.add_task(send_telegram_reply, chat_id, reply_text, reply_markup)

    elif text.startswith("/help"):
        help_text = (
            "ℹ️ <b>EarnX Help & Commands</b>\n\n"
            "1. Tap <b>Open EarnX App</b> to launch the Mini App.\n"
            "2. All coin balances are stored in an immutable double-entry ledger.\n"
            "3. Payouts require a minimum of ₹50.00 (5,000 coins).\n"
            "4. Need help? Contact @EarnXSupportBot"
        )
        background_tasks.add_task(send_telegram_reply, chat_id, help_text)

    return {"ok": True}
