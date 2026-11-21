import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '../api/endpoints'
import PasswordInput from '../components/PasswordInput'
import { useOtpFlowStore } from '../store/otpFlowStore'
import { formatPhone, isValidPhone } from '../utils/validation'

/** Giriş 1. adım: telefon + şifre. Doğruysa SMS kodu gönderilir ve /verify ekranına geçilir. */
export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const startFlow = useOtpFlowStore((s) => s.start)
  const [form, setForm] = useState({ phone_number: '', password: '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function submit(event) {
    event.preventDefault()
    const next = {}
    if (!isValidPhone(form.phone_number)) next.phone_number = 'Geçerli bir GSM numarası girin.'
    if (!form.password) next.password = 'Şifrenizi girin.'
    setErrors(next)
    if (Object.keys(next).length) return

    setBusy(true)
    setServerError(null)
    try {
      const res = await authApi.login(form.phone_number, form.password)
      startFlow({
        purpose: 'login', request: form, phone: form.phone_number,
        hint: res.dev_otp_hint, expiresIn: res.otp_expires_in_seconds,
        redirectTo: location.state?.from ?? '/',
      })
      navigate('/verify')
    } catch (err) {
      setServerError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <h1>Tekrar hoş geldin</h1>
      <p className="auth-subtitle">Hesabına giriş yap.</p>
      <form onSubmit={submit} className="form" noValidate>
        <label>
          GSM numarası
          <input
            type="tel" inputMode="tel" autoComplete="tel" placeholder="0555 123 45 67"
            value={form.phone_number}
            onChange={(e) => setForm({ ...form, phone_number: formatPhone(e.target.value) })}
            aria-invalid={!!errors.phone_number || undefined}
          />
          {errors.phone_number && <span className="field-error">{errors.phone_number}</span>}
        </label>
        <label htmlFor="login-password">
          Şifre
          <PasswordInput
            id="login-password" value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            invalid={!!errors.password}
          />
          {errors.password && <span className="field-error">{errors.password}</span>}
        </label>
        {serverError && <p className="form-error" role="alert">{serverError}</p>}
        <button className="btn" disabled={busy}>{busy ? 'Kontrol ediliyor…' : 'Giriş yap'}</button>
      </form>
      <p className="auth-footer">Hesabın yok mu? <Link to="/register">Kayıt ol</Link></p>
    </>
  )
}
