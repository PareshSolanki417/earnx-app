import logging
from decimal import Decimal
from sqlalchemy.orm import Session

from app.config import settings
from app.models.admin import AdminUser
from app.models.settings import AppSetting
from app.models.task import Task
from app.models.user import User
from app.services.wallet_service import wallet_service
from app.security.deps import hash_password

logger = logging.getLogger("earnx.seed")


def seed_database(db: Session):
    """Populates essential baseline settings, admin account, and default tasks."""
    # 1. Seed Admin User
    admin = db.query(AdminUser).filter(AdminUser.username == settings.ADMIN_USERNAME).first()
    if not admin:
        admin = AdminUser(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            role="SUPERADMIN",
            is_active=True,
        )
        db.add(admin)
        logger.info("Created default admin user: %s", settings.ADMIN_USERNAME)

    # 2. Seed Baseline AppSettings
    default_settings = [
        ("COINS_PER_RUPEE", str(settings.COINS_PER_RUPEE), "Number of coins equal to ₹1.00"),
        ("MIN_WITHDRAWAL_RUPEES", "0.0050", "Minimum withdrawal threshold"),
        ("AD_REWARD_COINS", "10.0", "Coins awarded per verified rewarded ad impression (10 coins = ₹0.10)"),
        ("REFERRAL_BONUS_COINS", str(settings.REFERRAL_BONUS_COINS), "Coins awarded when a referral completes qualifying actions"),
        ("REFERRAL_QUALIFYING_ACTIONS", str(settings.REFERRAL_QUALIFYING_ACTIONS), "Number of verified ad views required for referral bonus"),
        ("DAILY_BONUS_DAY_1", "10.0", "Coins for Day 1 check-in"),
        ("DAILY_BONUS_DAY_2", "15.0", "Coins for Day 2 check-in"),
        ("DAILY_BONUS_DAY_3", "20.0", "Coins for Day 3 check-in"),
        ("DAILY_BONUS_DAY_4", "25.0", "Coins for Day 4 check-in"),
        ("DAILY_BONUS_DAY_5", "30.0", "Coins for Day 5 check-in"),
        ("DAILY_BONUS_DAY_6", "40.0", "Coins for Day 6 check-in"),
        ("DAILY_BONUS_DAY_7", "50.0", "Coins for Day 7 check-in"),
        ("DAILY_AD_LIMIT", "20", "Maximum rewarded ads a user can watch per day (15 to 25 to maximize network CPM)"),
        ("ESTIMATED_REVENUE_PER_AD_RUPEES", "0.35", "Estimated gross advertising payout per completed ad (for margin analysis)"),
    ]

    for key, val, desc in default_settings:
        existing = db.query(AppSetting).filter(AppSetting.key == key).first()
        if not existing:
            db.add(AppSetting(key=key, value=val, description=desc))
        elif key == "AD_REWARD_COINS" and existing.value == "15.0":
            existing.value = "10.0"
        elif key == "MIN_WITHDRAWAL_RUPEES" and existing.value in ("50.0", "50"):
            existing.value = "0.0050"

    # 3. Seed Default Verified Tasks
    if db.query(Task).count() == 0:
        tasks = [
            Task(
                title="Join Official Telegram Community",
                description="Join our Telegram announcement channel to stay updated with high-paying reward drops and payout proofs.",
                icon="telegram",
                reward_coins=Decimal("25.0"),
                action_url="https://t.me/EarnX_App",
                verification_method="TELEGRAM_JOIN",
                verification_data="@EarnX_App",
                status="ACTIVE",
            ),
            Task(
                title="Explore Sponsor Showcase",
                description="Visit our verified partner brand portal for 20 seconds and check out the new featured deals.",
                icon="globe",
                reward_coins=Decimal("15.0"),
                action_url="https://monetag.com",
                verification_method="URL_VISIT",
                verification_data="https://monetag.com",
                status="ACTIVE",
            ),
            Task(
                title="Complete 3 Video Ads Today",
                description="Watch 3 eligible sponsored video clips to qualify for the daily extra reward bonus.",
                icon="video",
                reward_coins=Decimal("30.0"),
                action_url=None,
                verification_method="REWARD_MILESTONE",
                verification_data="ads:3",
                status="ACTIVE",
            ),
            Task(
                title="Invite Your First Friend",
                description="Share your referral code with a friend and earn bonus coins once they join and watch their first ad.",
                icon="users",
                reward_coins=Decimal("50.0"),
                action_url=None,
                verification_method="REWARD_MILESTONE",
                verification_data="referrals:1",
                status="ACTIVE",
            ),
        ]
        for t in tasks:
            db.add(t)
        logger.info("Seeded initial active tasks.")

    # 4. Seed Demo User in Development Mode
    if settings.APP_ENV == "development":
        demo_user = db.query(User).filter(User.telegram_id == 123456789).first()
        if not demo_user:
            demo_user = User(
                telegram_id=123456789,
                username="demotester",
                first_name="Demo",
                last_name="Tester",
                photo_url="https://api.dicebear.com/7.x/bottts/svg?seed=EarnX",
                referral_code="EARNDEMO",
                status="ACTIVE",
                risk_level="LOW",
                consecutive_bonus_days=2,
            )
            db.add(demo_user)
            db.flush()

            # Initialize wallet and credit initial starter coins
            wallet_service.credit_coins(
                db=db,
                user_id=demo_user.id,
                amount=Decimal("150.0"),
                tx_type="ADJUSTMENT",
                source="DEV_STARTER_BALANCE",
                external_event_id="demo_starter_123456789",
                metadata={"note": "Initial development seed balance for testing withdrawals"},
            )
            logger.info("Seeded demo user with 150 starter coins.")

    db.commit()
    logger.info("Seed data verification completed.")
