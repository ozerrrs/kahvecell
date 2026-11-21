import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { authApi } from '../api/endpoints'
import { selectIsLoggedIn, useAuthStore } from '../store/authStore'

export default function Layout() {
  const isLoggedIn = useAuthStore(selectIsLoggedIn)
  const user = useAuthStore((s) => s.user)
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const clearSession = useAuthStore((s) => s.clearSession)
  const navigate = useNavigate()

  async function handleLogout() {
    try {
      if (refreshToken) await authApi.logout(refreshToken)
    } catch {
      // Çıkış isteği başarısız olsa da yerel oturumu kapat.
    }
    clearSession()
    navigate('/login')
  }

  return (
    <div className="app">
      <header className="header">
        <div className="container header-inner">
          <Link to="/" className="brand">☕ KahveCell</Link>
          <nav className="nav" aria-label="Ana menü">
            <NavLink to="/" end>Dükkânlar</NavLink>
            {isLoggedIn ? (
              <>
                <NavLink to="/history">Siparişlerim</NavLink>
                <NavLink to="/subscription">Abonelik</NavLink>
                <span className="nav-user">{user?.full_name ?? user?.phone_number}</span>
                <button type="button" className="btn btn-link" onClick={handleLogout}>Çıkış</button>
              </>
            ) : (
              <>
                <NavLink to="/login">Giriş</NavLink>
                <NavLink to="/register">Kayıt ol</NavLink>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="container main">
        <Outlet />
      </main>
    </div>
  )
}
