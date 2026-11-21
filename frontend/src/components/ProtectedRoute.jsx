import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { selectIsLoggedIn, useAuthStore } from '../store/authStore'

/** Giriş gerektiren sayfaları korur; giriş yoksa /login'e yollar, sonra kaldığı yere döner. */
export default function ProtectedRoute() {
  const isLoggedIn = useAuthStore(selectIsLoggedIn)
  const location = useLocation()
  if (!isLoggedIn) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
