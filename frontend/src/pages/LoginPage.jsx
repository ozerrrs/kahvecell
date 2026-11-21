import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { authApi } from '../api/endpoints'
import { useAuthStore } from '../store/authStore'
import { isValidPhone } from '../utils/validation'

/** Giriş: 1) telefon → SMS kodu  2) kod → oturum. Kayıt sonrası doğrulama da bu sayfadan yapılır. */
export default function LoginPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)

  // Kayıt sayfasından gelindiyse kod zaten gönderilmiştir: doğrudan 2. adım.
  const [phone, setPhone] = useState(location.state?.phone ?? '')
  const [step, setStep] = useState(location.state?.phone ? 'code' : 'phone')
  const [code, setCode] = useState('')
  const [hint, setHint] = useState(location.state?.hint ?? null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function requestCode(event) {
    event.preventDefault()
    if (!isValidPhone(phone)) return setError('Geçerli bir GSM numarası girin (örn. 0555 123 45 67).')
    setBusy(true)
    setError(null)
    try {
      const res = await authApi.requestOtp(phone)
      setHint(res.dev_otp_hint)
      setStep('code')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function verify(event) {
    event.preventDefault()
    if (!/^\d{4,6}$/.test(code)) return setError('Kod 4-6 haneli olmalı.')
    setBusy(true)
    setError(null)
    try {
      const session = await authApi.verifyOtp(phone, code)
      setSession(session)
      navigate(location.state?.from ?? '/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="narrow">
      <h1>Giriş yap</h1>
      {step === 'phone' ? (
        <form onSubmit={requestCode} className="form" noValidate>
          <label>
            GSM numarası
            <input
              type="tel" inputMode="tel" autoComplete="tel" placeholder="0555 123 45 67"
              value={phone} onChange={(e) => setPhone(e.target.value)} required
            />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="btn" disabled={busy}>{busy ? 'Gönderiliyor…' : 'Kod gönder'}</button>
          <p className="muted">Hesabın yok mu? <Link to="/register">Kayıt ol</Link></p>
        </form>
      ) : (
        <form onSubmit={verify} className="form" noValidate>
          <p className="muted">{phone} numarasına gönderilen kodu girin.</p>
          {hint && <p className="hint">Test ortamı: kod <strong>{hint}</strong></p>}
          <label>
            Doğrulama kodu
            <input
              inputMode="numeric" autoComplete="one-time-code" maxLength={6} autoFocus
              value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} required
            />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="btn" disabled={busy}>{busy ? 'Doğrulanıyor…' : 'Giriş yap'}</button>
          <button type="button" className="btn btn-link" onClick={() => { setStep('phone'); setCode(''); setError(null) }}>
            Numarayı değiştir
          </button>
        </form>
      )}
    </section>
  )
}
