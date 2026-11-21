# KahveCell ☕

Operatör abonelerinin mobil ödeme ile anlaşmalı kahve dükkânlarından indirimli kahve siparişi verebildiği, konum tabanlı dijital kahve abonelik platformu.

## Teknoloji

| Katman | Teknoloji |
|---|---|
| Backend | Python 3, FastAPI, SQLAlchemy |
| Veritabanı | SQLite |
| Frontend | React (Vite) |
| Harita | Leaflet |

## Proje yapısı

```
kahvecell/
├── backend/            FastAPI sunucusu
│   ├── app/
│   │   ├── main.py         uygulamanın giriş noktası
│   │   ├── core/           ayarlar, veritabanı, güvenlik (JWT), hata yönetimi, loglama
│   │   ├── models/         veritabanı tabloları
│   │   ├── schemas/        istek/yanıt kalıpları ve doğrulama
│   │   ├── repositories/   veritabanı erişimi
│   │   ├── services/       iş kuralları
│   │   └── api/v1/         endpoint'ler (/api/v1/...)
│   ├── scripts/seed.py     örnek veri betiği
│   └── tests/              otomatik testler
├── frontend/           React arayüzü
└── docs/               dokümantasyon
```

## Gereksinimler

- Python 3.11 veya üzeri
- Node.js 20 veya üzeri

## Kurulum (ilk sefer)

### Backend

Mac / Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

### Frontend

```bash
cd frontend
npm install
```

## Çalıştırma

### Backend

```bash
cd backend
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Terminalde `Uvicorn running on http://127.0.0.1:8000` yazısı görününce sunucu hazırdır. Durdurmak için `Ctrl + C`.

| Adres | İçerik |
|---|---|
| http://localhost:8000 | "KahveCell backend çalışıyor ☕" mesajı |
| http://localhost:8000/docs | Swagger — tüm endpoint'ler ve test ekranı |

İlk açılışta `backend/kahvecell.db` veritabanı dosyası ve tablolar otomatik oluşur.

### Örnek veri (seed)

Backend sanal ortamı açıkken, `backend` klasöründe:

```bash
python -m scripts.seed
```

Ankara'dan 5 dükkân, 40 ürün, 3 abonelik paketi ve test kullanıcılarını ekler. Tekrar çalıştırmak güvenlidir; var olan kayıtları atlar.

### Frontend

```bash
cd frontend
npm run dev
```

Tarayıcıda http://localhost:5173 adresini açın.

## Test hesapları

Şifre yoktur; giriş SMS kodu ile yapılır. SMS simülasyonu olduğu için kod her zaman **`1234`**'tür.

| Rol | Telefon | Not |
|---|---|---|
| Müşteri | 0555 123 45 67 | Aktif Starter aboneliği (10 kahve, 30 gün) |
| Dükkân Sahibi | 0555 765 43 21 | Kızılay Kavurma Evi'nin sahibi |
| Admin | 0555 000 00 00 | Tüm kullanıcıları yönetir |

## Kayıt ve giriş akışı

| Endpoint | Ne zaman | Gövde |
|---|---|---|
| `POST /api/v1/auth/register` | Yeni kullanıcı | `{"phone_number": "05559998877", "full_name": "Ali Yılmaz", "email": "ali@example.com"}` |
| `POST /api/v1/auth/request-otp` | Kayıtlı kullanıcı girişi | `{"phone_number": "05551234567"}` |
| `POST /api/v1/auth/verify-otp` | Her iki durumda kodu doğrulama | `{"phone_number": "05551234567", "code": "1234"}` |
| `POST /api/v1/auth/refresh` | Erişim anahtarı süresi dolunca | `{"refresh_token": "..."}` |
| `POST /api/v1/auth/logout` | Çıkış | `{"refresh_token": "..."}` |

Hesap, `register` sonrası kod doğrulandığında oluşturulur. Kayıtlı bir numarayla `register` → **409**, kayıtsız bir numarayla `request-otp` → **404** döner.

### Swagger'da giriş yapma

1. `POST /api/v1/auth/request-otp` → `{"phone_number": "05551234567"}`
2. `POST /api/v1/auth/verify-otp` → `{"phone_number": "05551234567", "code": "1234"}`
3. Dönen `access_token` değerini kopyalayın.
4. Sayfanın üstündeki **Authorize 🔓** düğmesine basıp yapıştırın.

Artık giriş gerektiren endpoint'leri deneyebilirsiniz.

## Abonelik ve ödeme

| Paket | Fiyat | Kahve hakkı | Misafir hakkı |
|---|---|---|---|
| Starter | 89,99 TL | 10 / ay | – |
| Premium | 149,99 TL | 20 / ay | 2 |
| Unlimited | 249,99 TL | Sınırsız | 5 + öncelik |

**Akış:** `POST /payments/process` (kart ile ödeme → `transaction_id`) → `POST /subscriptions` (`transaction_id` ile başlat).

| Kart | Sonuç |
|---|---|
| `4242-4242-4242-4242` | Her zaman başarılı |
| `4000-0000-0000-0002` | Her zaman başarısız |

| İşlem | Endpoint | Kural |
|---|---|---|
| Yükseltme | `PATCH /subscriptions/me` + `transaction_id` | Fiyat farkı ödenir, haklar hemen eklenir |
| Düşürme | `PATCH /subscriptions/me` | Ücretsiz, dönem sonunda uygulanır |
| İptal | `DELETE /subscriptions/me` | Dönem sonuna kadar kullanılabilir |
| Yenileme | otomatik | Dönem bitince haklar yeniden yüklenir |
| Ay sonu simülasyonu (demo) | `POST /subscriptions/me/simulate-renewal` | Üretimde kapalı |

Kart numarasının tamamı saklanmaz, yalnızca son 4 hanesi kaydedilir. Başarısız ödemeler de geçmişte tutulur (`GET /payments/me`).

## Dükkânlar ve konum

| Endpoint | Açıklama |
|---|---|
| `GET /api/v1/shops` | Tüm dükkânlar (puana göre) |
| `GET /api/v1/shops?lat=39.9208&lng=32.8541&radius=5` | Yakındakiler, en yakından uzağa, `distance_km` ile |
| `GET /api/v1/shops?q=kizilay` | Ad/adres araması (Türkçe karakter ve büyük/küçük harf duyarsız) |
| `GET /api/v1/shops?min_rating=4.5&open_now=true&sort=name` | Filtre ve sıralama |
| `GET /api/v1/shops/{id}?lat=..&lng=..` | Detay + kategorilere ayrılmış menü + mesafe |
| `GET /api/v1/shops/{id}/menu` | Sadece menü |

Mesafe **Haversine** formülüyle hesaplanır. Önce `(latitude, longitude)` index'i ile kare alan dışındaki dükkânlar veritabanında elenir, sonra kalanların kesin mesafesi hesaplanır. "Şu an açık mı?" Türkiye saatine göredir ve gece yarısını geçen çalışma saatlerini destekler.

## Siparişler ve QR

```
PENDING ──► ACCEPTED ──► PREPARING ──► READY ──► DELIVERED (QR okutularak)
   │            │
   └────────────┴──► CANCELLED (kahve hakkı iade edilir)
```

| Endpoint | Kim | Açıklama |
|---|---|---|
| `POST /api/v1/orders` | Müşteri | Sipariş + 1 hak düşer (Unlimited'da düşmez) + imzalı QR |
| `GET /api/v1/orders/history` | Müşteri | Geçmiş (`favorites_only=true` ile favoriler) |
| `GET /api/v1/orders/{id}` | Müşteri / Dükkân | Detay ve durum geçmişi |
| `GET /api/v1/orders/{id}/qr` | Müşteri | QR kod PNG |
| `PATCH /api/v1/orders/{id}/favorite` | Müşteri | Favoriye ekle/çıkar |
| `POST /api/v1/orders/{id}/reorder` | Müşteri | Aynı siparişi tekrar ver |
| `GET /api/v1/orders/incoming` | Dükkân | Gelen siparişler (Unlimited aboneler önde) |
| `PATCH /api/v1/orders/{id}/status` | Dükkân / Müşteri | Durum güncelle (müşteri sadece PENDING iptal) |
| `POST /api/v1/orders/verify-qr` | Dükkân | QR gerçek mi? |

**QR içeriği** (case 13.2): `{"order_id", "user_id", "shop_id", "created_at", "signature"}`. `signature`, ilk dört alanın sunucudaki `QR_SECRET_KEY` ile alınmış **HMAC-SHA256** imzasıdır. Tek karakter değişse imza tutmaz. `DELIVERED` durumuna geçmek için QR'ın okutulması (`qr_data`) zorunludur.

**Kurallar:** Aktif abonelik yoksa `SUBSCRIPTION_REQUIRED`, hak bittiyse `NO_CREDITS_LEFT` (403). Dükkân kapalıysa `SHOP_CLOSED`. Hak düşme tek bir koşullu `UPDATE` ile yapılır, eşzamanlı siparişlerde eksiye düşmez.

## Veritabanı değişiklikleri (Alembic migration)

Şema değişiklikleri `backend/migrations/versions/` altında numaralı dosyalar olarak tutulur. Backend açılırken bekleyen migration'lar otomatik uygulanır, veriler korunur.

Bir modeli değiştirdikten sonra (`backend` klasöründe, sanal ortam açıkken):

```bash
alembic revision --autogenerate -m "add avatar_url to users"   # değişiklik dosyasını üret
alembic upgrade head                                           # uygula
```

| Komut | Ne yapar |
|---|---|
| `alembic current` | Veritabanının hangi adımda olduğunu gösterir |
| `alembic history` | Tüm adımları listeler |
| `alembic downgrade -1` | Son adımı geri alır |

`tests/test_migrations.py`, modeller ile migration dosyalarının uyumlu olduğunu kontrol eder; migration üretmeyi unutursanız test başarısız olur.

## Testler

```bash
cd backend
source .venv/bin/activate
pytest
```

## API yanıt formatı

Tüm yanıtlar aynı biçimdedir:

```json
{ "success": true, "data": { ... }, "error": null }
```

Hata durumunda:

```json
{ "success": false, "data": null, "error": { "code": "OTP_INVALID", "message": "Doğrulama kodu hatalı.", "details": null } }
```

## Sık karşılaşılan sorunlar

| Hata | Çözüm |
|---|---|
| `cd: no such file or directory: backend` | Zaten `backend` klasörünün içindesiniz; `cd` satırını atlayın. |
| `address already in use` | Sunucu başka bir terminalde zaten çalışıyor. |
| `RATE_LIMITED` | Bir dakikada 10'dan fazla giriş isteği gönderildi; bir dakika bekleyin. |
| Windows'ta `Activate.ps1` çalışmıyor | Bir kez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` çalıştırın. |
