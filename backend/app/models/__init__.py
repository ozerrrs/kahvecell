"""Tüm modeller burada toplanır; böylece SQLAlchemy ilişkileri birbirini bulabilir."""

from app.models.auth import OtpCode, RefreshToken
from app.models.order import Order
from app.models.payment import Payment
from app.models.shop import Product, Shop
from app.models.subscription import Subscription, SubscriptionPlan
from app.models.user import User

__all__ = [
    "User", "OtpCode", "RefreshToken",
    "SubscriptionPlan", "Subscription", "Shop", "Product", "Order", "Payment",
]
