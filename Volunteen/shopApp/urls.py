from django.urls import path
from .views import (
    ShopHomeView,
    ShopRedeemPointsView,
    ShopIdentifyChildView,
    ShopCompleteTransactionView,
    ShopCancelTransactionView,
    ShopRedemptionHistoryView,
    ToggleRewardVisibilityView,
)

app_name='shopApp'

urlpatterns = [
    path('home/', ShopHomeView.as_view(), name='shop_home'),
    path('redeem-points/', ShopRedeemPointsView.as_view(), name='shop_redeem_points'),
    path('identify-child/', ShopIdentifyChildView.as_view(), name='shop_identify_child'),
    path('complete-transaction/', ShopCompleteTransactionView.as_view(), name='shop_complete_transaction'),
    path('cancel-transaction/', ShopCancelTransactionView.as_view(), name='shop_cancel_transaction'),
    path('redemption-history/', ShopRedemptionHistoryView.as_view(), name='shop_redemption_history'),
    path('rewards/<int:reward_id>/toggle-visibility/', ToggleRewardVisibilityView.as_view(), name='toggle_reward_visibility'),
]
