import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
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
 *  /login, /register        Giriş / kayıt                                (herkes)
 *  /shops/:shopId           Dükkân detayı + menü                          (herkes)
 *  /shops/:shopId/order     Sipariş ekranı                                (giriş gerekli)
 *  /orders/:orderId         Sipariş QR kodu ve durumu                     (giriş gerekli)
 *  /history                 Sipariş geçmişi                               (giriş gerekli)
 *  /subscription            Abonelik ve ödeme                             (giriş gerekli)
 */
export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
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
