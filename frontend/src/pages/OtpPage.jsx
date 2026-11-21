import { useEffect, useRef, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { authApi } from '../api/endpoints'
import { useAuthStore } from '../store/authStore'
import { useOtpFlowStore } from '../store/otpFlowStore'

const LENGTH = 4
const RESEND_AFTER_SECONDS = 30

function useSecondsSince(timestamp) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  return Math.max(0, Math.floor((now - timestamp) / 1000))
}

const mmss = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`

/** Kayıt ve girişin ortak 2. adımı: telefona gelen 4 haneli kodu doğrular. */
export default function OtpPage() {
  const flow = useOtpFlowStore((s) => s.flow)
  const isLoggedIn = useAuthStore((s) => Boolean(s.accessToken))
  // Akış bilgisi yoksa (sayfa yenilendi ya da doğrulama yeni bitti): giriş yapılmışsa ana sayfa, değilse giriş.
  if (!flow) return <Navigate to={isLoggedIn ? '/' : '/login'} replace />
  return <OtpForm flow={flow} />
}

function OtpForm({ flow }) {
  const navigate = useNavigate()
  const setSession = useAuthStore((s) => s.setSession)
  const { resent, clear } = useOtpFlowStore()
  const [digits, setDigits] = useState(Array(LENGTH).fill(''))
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const inputs = useRef([])

  const elapsed = useSecondsSince(flow.sentAt)
  const remaining = Math.max(0, (flow.expiresIn ?? 300) - elapsed)
  const canResend = elapsed >= RESEND_AFTER_SECONDS

  useEffect(() => { inputs.current[0]?.focus() }, [flow.sentAt])

  async function submit(code) {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      const session = await authApi.verifyOtp(flow.phone, code)
      setSession(session)
      navigate(flow.redirectTo ?? '/', { replace: true })
      clear() // şifre artık bellekte tutulmasın
    } catch (err) {
      setError(err.message)
      setDigits(Array(LENGTH).fill(''))
      inputs.current[0]?.focus()
    } finally {
      setBusy(false)
    }
  }

  function fill(index, value) {
    const next = [...digits]
    value.split('').forEach((char, offset) => {
      if (index + offset < LENGTH) next[index + offset] = char
    })
    setDigits(next)
    const nextEmpty = next.findIndex((d) => !d)
    if (nextEmpty === -1) {
      inputs.current[LENGTH - 1]?.blur()
      submit(next.join('')) // 4 hane dolunca otomatik doğrula
    } else {
      inputs.current[Math.min(index + value.length, LENGTH - 1)]?.focus()
    }
  }

  function handleChange(index, event) {
    const value = event.target.value.replace(/\D/g, '')
    if (!value) {
      const next = [...digits]
      next[index] = ''
      setDigits(next)
      return
    }
    fill(index, value.slice(-LENGTH))
  }

  function handleKeyDown(index, event) {
    if (event.key === 'Backspace' && !digits[index] && index > 0) inputs.current[index - 1]?.focus()
    if (event.key === 'ArrowLeft' && index > 0) inputs.current[index - 1]?.focus()
    if (event.key === 'ArrowRight' && index < LENGTH - 1) inputs.current[index + 1]?.focus()
  }

  function handlePaste(event) {
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, LENGTH)
    if (pasted) {
      event.preventDefault()
      fill(0, pasted)
    }
  }

  async function resend() {
    setError(null)
    try {
      const { request } = flow
      const res = flow.purpose === 'register'
        ? await authApi.register(request)
        : await authApi.login(request.phone_number, request.password)
      resent(res.dev_otp_hint, res.otp_expires_in_seconds)
      setDigits(Array(LENGTH).fill(''))
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <>
      <h1>Numaranı doğrula</h1>
      <p className="auth-subtitle">
        <span className="otp-phone">{flow.phone}</span> numarasına gelen 4 haneli kodu gir.
      </p>

      <form className="form" onSubmit={(e) => { e.preventDefault(); submit(digits.join('')) }} noValidate>
        <div className="otp-inputs" role="group" aria-label="Doğrulama kodu" aria-invalid={!!error || undefined}>
          {digits.map((digit, index) => (
            <input
              key={index}
              ref={(el) => { inputs.current[index] = el }}
              value={digit}
              inputMode="numeric"
              autoComplete={index === 0 ? 'one-time-code' : 'off'}
              maxLength={LENGTH}
              aria-label={`${index + 1}. hane`}
              disabled={busy}
              onChange={(e) => handleChange(index, e)}
              onKeyDown={(e) => handleKeyDown(index, e)}
              onPaste={handlePaste}
              onFocus={(e) => e.target.select()}
            />
          ))}
        </div>

        {flow.hint && (
          <p className="test-note">🧪 Test ortamı: kod her zaman <strong>{flow.hint}</strong></p>
        )}
        {error && <p className="form-error" role="alert">{error}</p>}

        <button className="btn" disabled={busy || digits.some((d) => !d)}>
          {busy ? 'Doğrulanıyor…' : 'Doğrula'}
        </button>

        <div className="otp-meta">
          <span aria-live="polite">{remaining > 0 ? `Kod ${mmss(remaining)} geçerli` : 'Kodun süresi doldu'}</span>
          <button type="button" className="btn btn-link" onClick={resend} disabled={!canResend}>
            {canResend ? 'Kodu tekrar gönder' : `Tekrar gönder (${RESEND_AFTER_SECONDS - elapsed})`}
          </button>
        </div>
      </form>

      <p className="auth-footer">
        <button
          type="button" className="btn btn-link"
          onClick={() => navigate(flow.purpose === 'register' ? '/register' : '/login', { replace: true })}
        >
          ← Numarayı değiştir
        </button>
      </p>
    </>
  )
}
