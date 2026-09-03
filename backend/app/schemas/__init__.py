from app.schemas.auth import (
    TelegramAuthRequest,
    AdminLoginRequest,
    TokenResponse,
    AuthUserResponse,
    TelegramAuthResponse,
)
from app.schemas.wallet import WalletResponse, TransactionResponse, TransactionListResponse
from app.schemas.ads import (
    AdStartRequest,
    AdStartResponse,
    MonetagPostbackPayload,
    PostbackResultResponse,
)
from app.schemas.tasks import (
    TaskItemResponse,
    TaskCompleteRequest,
    TaskCompleteResponse,
    DailyBonusStatusResponse,
    DailyBonusClaimResponse,
)
from app.schemas.referral import ReferralStatsResponse, ReferredUserItem
from app.schemas.withdrawal import (
    WithdrawalCreateRequest,
    WithdrawalResponse,
    WithdrawalListResponse,
)
from app.schemas.admin import (
    AdminDashboardMetrics,
    AdminUserItem,
    AdminUserDetail,
    AdminBalanceAdjustRequest,
    AdminUserStatusUpdate,
    AdminWithdrawalActionRequest,
    AdminTaskCreate,
    AdminSettingItem,
    AdminSettingUpdate,
    AdminActionLogItem,
    FraudEventItem,
)
from app.schemas.user import UserProfileResponse

__all__ = [
    "TelegramAuthRequest",
    "AdminLoginRequest",
    "TokenResponse",
    "AuthUserResponse",
    "TelegramAuthResponse",
    "WalletResponse",
    "TransactionResponse",
    "TransactionListResponse",
    "AdStartRequest",
    "AdStartResponse",
    "MonetagPostbackPayload",
    "PostbackResultResponse",
    "TaskItemResponse",
    "TaskCompleteRequest",
    "TaskCompleteResponse",
    "DailyBonusStatusResponse",
    "DailyBonusClaimResponse",
    "ReferralStatsResponse",
    "ReferredUserItem",
    "WithdrawalCreateRequest",
    "WithdrawalResponse",
    "WithdrawalListResponse",
    "AdminDashboardMetrics",
    "AdminUserItem",
    "AdminUserDetail",
    "AdminBalanceAdjustRequest",
    "AdminUserStatusUpdate",
    "AdminWithdrawalActionRequest",
    "AdminTaskCreate",
    "AdminSettingItem",
    "AdminSettingUpdate",
    "AdminActionLogItem",
    "FraudEventItem",
    "UserProfileResponse",
]
