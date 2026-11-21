import { Route, Routes } from 'react-router-dom'
import AuthLayout from './components/AuthLayout'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import OtpPage from './pages/OtpPage'
import {
  HistoryPage,
  NotFoundPage,
  OrderPage,
  OrderQrPage,
  SubscriptionPage,
} from './pages/Placeholders'
import RegisterPage from './pages/RegisterPage'
import ShopDetailPage from './pages/ShopDetailPage'

/**
 * Sayfa haritası
 *
 *  /                        Ana sayfa: harita + yakındaki dükkânlar      (herkes)
 *  /login                   Giriş: telefon + şifre                       (herkes)
 *  /register                Kayıt: telefon + ad soyad + şifre            (herkes)
 *  /verify                  SMS kodu doğrulama (kayıt ve giriş 2. adımı)  (herkes)
 *  /shops/:shopId           Dükkân detayı + menü                          (herkes)
 *  /shops/:shopId/order     Sipariş ekranı                                (giriş gerekli)
 *  /orders/:orderId         Sipariş QR kodu ve durumu                     (giriş gerekli)
 *  /history                 Sipariş geçmişi                               (giriş gerekli)
 *  /subscription            Abonelik ve ödeme                             (giriş gerekli)
 */
export default function App() {
  return (
    <Routes>
      {/* Üst menüsüz, ortada kart */}
      <Route element={<AuthLayout />}>
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="verify" element={<OtpPage />} />
      </Route>

      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="shops/:shopId" element={<ShopDetailPage />} />

        <Route element={<ProtectedRoute />}>
          <Route path="shops/:shopId/order" element={<OrderPage />} />
          <Route path="orders/:orderId" element={<OrderQrPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="subscription" element={<SubscriptionPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
