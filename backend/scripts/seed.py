"""Örnek veri (seed) betiği — Ankara.

Çalıştırma (backend klasöründe, sanal ortam açıkken):
    python -m scripts.seed

Betik tekrar çalıştırılabilir: zaten var olan kayıtları atlar, kopya oluşturmaz.
Dükkân isimleri hayalidir; koordinatlar ilgili semtlerin gerçek konumlarıdır.
"""

from datetime import time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, init_db
from app.models import Payment, Product, Shop, Subscription, SubscriptionPlan, User
from app.models.base import utcnow
from app.models.enums import PaymentStatus, PlanType, SubscriptionStatus, UserRole

# ---------------------------------------------------------------------------
# Abonelik paketleri (case dokümanı 3.2)
# ---------------------------------------------------------------------------
PLANS = [
    dict(plan_type=PlanType.STARTER, name="Starter", monthly_price=Decimal("89.99"),
         monthly_credits=10, guest_credits=0, has_priority=False),
    dict(plan_type=PlanType.PREMIUM, name="Premium", monthly_price=Decimal("149.99"),
         monthly_credits=20, guest_credits=2, has_priority=False),
    dict(plan_type=PlanType.UNLIMITED, name="Unlimited", monthly_price=Decimal("249.99"),
         monthly_credits=None, guest_credits=5, has_priority=True),
]

# ---------------------------------------------------------------------------
# Test kullanıcıları  (giriş: telefon numarası + SMS kodu 1234)
# ---------------------------------------------------------------------------
TEST_CUSTOMER = dict(
    phone_number="+905551234567",
    full_name="Test Müşteri",
    email="musteri@kahvecell.test",
    role=UserRole.CUSTOMER,
    preferences={"favorite_coffees": ["Latte", "Türk Kahvesi"], "allergens": []},
)
TEST_SHOP_OWNER = dict(
    phone_number="+905557654321",
    full_name="Test Dükkân Sahibi",
    email="dukkan@kahvecell.test",
    role=UserRole.SHOP_OWNER,
    preferences=None,
)
TEST_ADMIN = dict(
    phone_number="+905550000000",
    full_name="Test Admin",
    email="admin@kahvecell.test",
    role=UserRole.ADMIN,
    preferences=None,
)

# ---------------------------------------------------------------------------
# Ankara dükkânları
# ---------------------------------------------------------------------------
SHOPS = [
    dict(
        name="Kızılay Kavurma Evi",
        address="Ziya Gökalp Cd. No:12, Kızılay, Çankaya",
        latitude=39.92077, longitude=32.85411,
        opens_at=time(7, 0), closes_at=time(23, 0), rating=Decimal("4.5"),
        description="Meydanın kalbinde, sabah erkenden açılan hızlı servis kahvecisi.",
        price_factor=Decimal("1.00"),
    ),
    dict(
        name="Tunalı Demleme",
        address="Tunalı Hilmi Cd. No:88, Kavaklıdere, Çankaya",
        latitude=39.90522, longitude=32.86058,
        opens_at=time(8, 0), closes_at=time(0, 0), rating=Decimal("4.7"),
        description="Üçüncü dalga demleme yöntemleri ve günlük taze kavrum.",
        price_factor=Decimal("1.10"),
    ),
    dict(
        name="7. Cadde Kahve Durağı",
        address="Aşkabat Cd. (7. Cadde) No:41, Bahçelievler, Çankaya",
        latitude=39.92316, longitude=32.82378,
        opens_at=time(8, 0), closes_at=time(22, 30), rating=Decimal("4.3"),
        description="Öğrencilerin uğrak noktası; geniş masalar, priz bol.",
        price_factor=Decimal("0.90"),
    ),
    dict(
        name="Çayyolu Bahçe Kahve",
        address="Prof. Dr. Ahmet Taner Kışlalı Cd. No:5, Çayyolu, Çankaya",
        latitude=39.88534, longitude=32.69028,
        opens_at=time(9, 0), closes_at=time(23, 0), rating=Decimal("4.6"),
        description="Bahçeli, sakin; uzaktan çalışanlar için ideal.",
        price_factor=Decimal("1.05"),
    ),
    dict(
        name="Hamamönü Köşk Kahvesi",
        address="Hamamönü Sk. No:7, Altındağ",
        latitude=39.93526, longitude=32.86283,
        opens_at=time(10, 0), closes_at=time(22, 0), rating=Decimal("4.4"),
        description="Restore edilmiş tarihi konakta geleneksel Türk kahvesi.",
        price_factor=Decimal("0.95"),
    ),
]

# Temel menü (Ankara, 2026 sonu yaklaşık fiyatları). Her dükkân kendi fiyat çarpanını uygular.
MENU = [
    ("Espresso", "Espresso Bazlı", "Tek shot, yoğun gövdeli.", Decimal("110")),
    ("Americano", "Espresso Bazlı", "Espresso ve sıcak su.", Decimal("140")),
    ("Cappuccino", "Espresso Bazlı", "Espresso, buharda ısıtılmış süt ve yoğun köpük.", Decimal("165")),
    ("Latte", "Espresso Bazlı", "Espresso ve bol sütlü, ince köpüklü.", Decimal("170")),
    ("Türk Kahvesi", "Geleneksel", "Közde pişirilmiş, lokum eşliğinde.", Decimal("100")),
    ("Filtre Kahve", "Demleme", "Günün çekirdeğiyle V60 demleme.", Decimal("135")),
    ("Iced Latte", "Soğuk", "Buzlu latte.", Decimal("180")),
    ("Mocha", "Espresso Bazlı", "Espresso, çikolata ve süt.", Decimal("185")),
]


def _round_price(value: Decimal) -> Decimal:
    """Fiyatı en yakın 5 TL'ye yuvarlar (menülerde görülen tarz)."""
    return (value / 5).quantize(Decimal("1")) * 5


def get_or_create_user(db: Session, data: dict) -> tuple[User, bool]:
    user = db.scalar(select(User).where(User.phone_number == data["phone_number"]))
    if user:
        return user, False
    user = User(**data)
    db.add(user)
    db.flush()
    return user, True


def seed_plans(db: Session) -> dict[PlanType, SubscriptionPlan]:
    plans = {}
    for data in PLANS:
        plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.plan_type == data["plan_type"]))
        if not plan:
            plan = SubscriptionPlan(**data)
            db.add(plan)
            print(f"  + Paket: {data['name']}")
        plans[data["plan_type"]] = plan
    db.flush()
    return plans


def seed_shops(db: Session, owner: User) -> None:
    for index, data in enumerate(SHOPS):
        if db.scalar(select(Shop).where(Shop.name == data["name"])):
            continue
        factor = data.pop("price_factor")
        # İlk dükkânı test dükkân sahibine bağla (dükkân paneli testleri için).
        shop = Shop(**data, city="Ankara", owner_id=owner.id if index == 0 else None)
        db.add(shop)
        db.flush()
        for name, category, description, price in MENU:
            db.add(Product(shop_id=shop.id, name=name, category=category,
                           description=description, base_price=_round_price(price * factor)))
        print(f"  + Dükkân: {shop.name} ({len(MENU)} ürün)")


def seed_test_subscription(db: Session, user: User, plan: SubscriptionPlan) -> None:
    has_active = db.scalar(
        select(Subscription).where(Subscription.user_id == user.id,
                                   Subscription.status == SubscriptionStatus.ACTIVE)
    )
    if has_active:
        return
    now = utcnow()
    subscription = Subscription(
        user_id=user.id, plan_id=plan.id,
        remaining_credits=plan.monthly_credits, remaining_guest_credits=plan.guest_credits,
        status=SubscriptionStatus.ACTIVE, started_at=now, expires_at=now + timedelta(days=30),
    )
    db.add(subscription)
    db.flush()
    db.add(Payment(
        user_id=user.id, plan_id=plan.id, subscription_id=subscription.id,
        transaction_id="SEED-TXN-0001", amount=plan.monthly_price,
        status=PaymentStatus.SUCCESS, card_last4="4242",
    ))
    print(f"  + Abonelik: {user.full_name} → {plan.name} ({plan.monthly_credits} kahve, 30 gün)")


def main() -> None:
    init_db()
    with SessionLocal() as db:
        print("Seed başlıyor…")
        plans = seed_plans(db)

        customer, created = get_or_create_user(db, TEST_CUSTOMER)
        if created:
            print(f"  + Kullanıcı: {customer.full_name} ({customer.phone_number})")
        owner, created = get_or_create_user(db, TEST_SHOP_OWNER)
        if created:
            print(f"  + Kullanıcı: {owner.full_name} ({owner.phone_number})")
        admin, created = get_or_create_user(db, TEST_ADMIN)
        if created:
            print(f"  + Kullanıcı: {admin.full_name} ({admin.phone_number})")

        seed_shops(db, owner)
        seed_test_subscription(db, customer, plans[PlanType.STARTER])
        db.commit()

        print("\nVeritabanındaki toplamlar:")
        for model in (SubscriptionPlan, User, Shop, Product, Subscription, Payment):
            count = len(db.scalars(select(model)).all())
            print(f"  {model.__tablename__:20} {count}")
        print("\nTamamlandı ✔")


if __name__ == "__main__":
    main()
