/**
 * Henüz doldurulmamış sayfalar. Her biri sonraki adımlarda kendi dosyasına taşınacak.
 */
import { Link, useParams } from 'react-router-dom'

function Placeholder({ title, children }) {
  return (
    <section>
      <h1>{title}</h1>
      <div className="state">{children}</div>
    </section>
  )
}

export function OrderPage() {
  const { shopId } = useParams()
  return (
    <Placeholder title="Sipariş ver">
      Dükkân <code>{shopId}</code> için boyut, süt, şeker ve ek shot seçimi burada olacak.
    </Placeholder>
  )
}

export function OrderQrPage() {
  const { orderId } = useParams()
  return (
    <Placeholder title="Siparişin QR kodu">
      Sipariş <code>{orderId}</code> için QR kod ve canlı durum burada gösterilecek.
    </Placeholder>
  )
}

export function HistoryPage() {
  return <Placeholder title="Siparişlerim">Geçmiş siparişler, favoriler ve tekrar sipariş burada olacak.</Placeholder>
}

export function SubscriptionPage() {
  return <Placeholder title="Abonelik">Paketler, ödeme formu ve aktif aboneliğin burada olacak.</Placeholder>
}

export function NotFoundPage() {
  return (
    <Placeholder title="Sayfa bulunamadı">
      <Link to="/">Ana sayfaya dön</Link>
    </Placeholder>
  )
}
