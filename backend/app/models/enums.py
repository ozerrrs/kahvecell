"""Tablolarda kullanılan sabit değer kümeleri."""

import enum


class UserRole(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    SHOP_OWNER = "SHOP_OWNER"
    ADMIN = "ADMIN"


class PlanType(str, enum.Enum):
    STARTER = "STARTER"
    PREMIUM = "PREMIUM"
    UNLIMITED = "UNLIMITED"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class OrderStatus(str, enum.Enum):
    """Sipariş durum makinesi: PENDING → ACCEPTED → PREPARING → READY → DELIVERED (veya CANCELLED)."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class CupSize(str, enum.Enum):
    S = "S"
    M = "M"
    L = "L"


class MilkType(str, enum.Enum):
    NONE = "NONE"
    REGULAR = "REGULAR"
    LACTOSE_FREE = "LACTOSE_FREE"
    OAT = "OAT"
    ALMOND = "ALMOND"
    SOY = "SOY"


class PaymentStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
