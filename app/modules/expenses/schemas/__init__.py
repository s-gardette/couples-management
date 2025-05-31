"""
Expenses schemas module.
"""

from .household import (
    HouseholdBase,
    HouseholdCreate,
    HouseholdUpdate,
    HouseholdResponse,
    HouseholdListResponse,
    UserHouseholdResponse,
    JoinHouseholdRequest,
    UpdateMemberRoleRequest,
    HouseholdSettingsUpdate,
    InviteCodeResponse,
    HouseholdStatsResponse,
    HouseholdMemberResponse,
    HouseholdMembersResponse,
)

from .expense import (
    ExpenseBase,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseListResponse,
    ExpenseShareResponse,
    ExpenseFilters,
    UpdateExpenseSharesRequest,
    MarkSharePaidRequest,
    ExpenseSummaryResponse,
    ReceiptUploadResponse,
    CategoryResponse,
)

from .category import (
    CategoryBase,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse as CategoryDetailResponse,
    CategoryListResponse,
    CategoryStatsResponse,
)

from .analytics import (
    AnalyticsFilters,
    SpendingSummaryResponse,
    CategoryAnalysisResponse,
    UserSpendingPatternsResponse,
    BalanceCalculationResponse,
    HouseholdBalancesResponse,
    TrendAnalysisResponse,
    ExportDataResponse,
    AnalyticsDashboardResponse,
)

__all__ = [
    # Household schemas
    "HouseholdBase",
    "HouseholdCreate",
    "HouseholdUpdate",
    "HouseholdResponse",
    "HouseholdListResponse",
    "UserHouseholdResponse",
    "JoinHouseholdRequest",
    "UpdateMemberRoleRequest",
    "HouseholdSettingsUpdate",
    "InviteCodeResponse",
    "HouseholdStatsResponse",
    "HouseholdMemberResponse",
    "HouseholdMembersResponse",
    
    # Expense schemas
    "ExpenseBase",
    "ExpenseCreate",
    "ExpenseUpdate",
    "ExpenseResponse",
    "ExpenseListResponse",
    "ExpenseShareResponse",
    "ExpenseFilters",
    "UpdateExpenseSharesRequest",
    "MarkSharePaidRequest",
    "ExpenseSummaryResponse",
    "ReceiptUploadResponse",
    "CategoryResponse",
    
    # Category schemas
    "CategoryBase",
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryDetailResponse",
    "CategoryListResponse",
    "CategoryStatsResponse",
    
    # Analytics schemas
    "AnalyticsFilters",
    "SpendingSummaryResponse",
    "CategoryAnalysisResponse",
    "UserSpendingPatternsResponse",
    "BalanceCalculationResponse",
    "HouseholdBalancesResponse",
    "TrendAnalysisResponse",
    "ExportDataResponse",
    "AnalyticsDashboardResponse",
]
