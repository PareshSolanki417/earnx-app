from app.routes.auth import router as auth_router
from app.routes.user import router as user_router
from app.routes.wallet import router as wallet_router
from app.routes.ads import router as ads_router
from app.routes.tasks import router as tasks_router
from app.routes.referral import router as referral_router
from app.routes.withdrawals import router as withdrawals_router
from app.routes.notifications import router as notifications_router
from app.routes.admin import router as admin_router
from app.routes.bot_webhook import router as bot_webhook_router
from app.routes.adsgram import router as adsgram_router
from app.routes.paymentwall import router as paymentwall_router

__all__ = [
    "auth_router",
    "user_router",
    "wallet_router",
    "ads_router",
    "tasks_router",
    "referral_router",
    "withdrawals_router",
    "notifications_router",
    "admin_router",
    "bot_webhook_router",
    "adsgram_router",
    "paymentwall_router",
]
