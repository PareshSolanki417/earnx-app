import os
import sys
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# Add backend directory to sys.path to load shared config
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
from app.config import settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("earnx.bot")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles /start command.
    Extracts optional referral code (e.g. /start EARN123456) and presents the Mini App button.
    """
    user = update.effective_user
    args = context.args
    referral_code = args[0] if args and len(args) > 0 else None

    # Construct WebApp URL with start parameter for referral routing
    base_url = settings.WEBAPP_URL.rstrip("/")
    version_param = "v=20260904_04"
    app_url = f"{base_url}/?{version_param}&startapp={referral_code}" if referral_code else f"{base_url}/?{version_param}"

    welcome_text = (
        f"👋 Hello, *{user.first_name}*!\n\n"
        "Welcome to *EarnX* — The premier reward platform.\n\n"
        "🪙 *How to Earn:*\n"
        "• 🎬 Watch verified sponsor video offers\n"
        "• 🎁 Claim consecutive 7-day check-in bonuses\n"
        "• 📋 Complete simple sponsor activities\n"
        "• 👥 Invite friends to earn +50 coins\n\n"
        "💳 Redeem your verified coins directly to TON, WLD, Binance, or PayPal!"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                text="🚀 Open EarnX Mini App",
                web_app=WebAppInfo(url=app_url),
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_markdown_v2(
        welcome_text.replace(".", "\\.").replace("-", "\\-").replace("!", "\\!").replace("(", "\\(").replace(")", "\\)"),
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "ℹ️ *EarnX Help Guide*\n\n"
        "1. Tap *Open EarnX Mini App* to view your balance.\n"
        "2. All coin balances are stored in an immutable double-entry ledger.\n"
        "3. Payouts require minimum 0.0050 (TON, WLD, Binance, PayPal).\n"
        "4. Automated bots and click spam are strictly prohibited."
    )
    await update.message.reply_markdown(help_text)


def main():
    token = settings.BOT_TOKEN
    if not token or token == "mock_bot_token":
        logger.warning(
            "BOT_TOKEN is not configured or is using default mock. Please set BOT_TOKEN in .env"
        )

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    logger.info("Starting EarnX Telegram Bot in polling mode...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
