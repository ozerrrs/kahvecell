import { Link, Outlet } from 'react-router-dom'

/** Giriş / kayıt / doğrulama sayfaları: üst menü yok, ortada tek kart. */
export default function AuthLayout() {
  return (
    <main className="auth-page">
      <div className="auth-card">
        <Link to="/" className="auth-brand" aria-label="KahveCell ana sayfa">
          <span className="auth-logo" aria-hidden="true">☕</span>
          <span className="auth-brand-name">KahveCell</span>
        </Link>
        <Outlet />
      </div>
    </main>
  )
}
