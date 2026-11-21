import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/endpoints'
import PasswordInput from '../components/PasswordInput'
import { useOtpFlowStore } from '../store/otpFlowStore'
import { formatPhone, isValidPhone, passwordError } from '../utils/validation'

export default function RegisterPage() {
  const navigate = useNavigate()
  const startFlow = useOtpFlowStore((s) => s.start)
  const [form, setForm] = useState({ phone_number: '', full_name: '', password: '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState(null)
  const [busy, setBusy] = useState(false)

  const update = (field, transform = (v) => v) => (e) => setForm({ ...form, [field]: transform(e.target.value) })

  function validate() {
    const next = {}
    if (!isValidPhone(form.phone_number)) next.phone_number = 'Geçerli bir GSM numarası girin (örn. 0555 123 45 67).'
    if (form.full_name.trim().length < 2) next.full_name = 'Ad soyad en az 2 karakter olmalı.'
    const pwError = passwordError(form.password)
    if (pwError) next.password = pwError
    setErrors(next)
    return Object.keys(next).length === 0
  }

  async function submit(event) {
    event.preventDefault()
    if (!validate()) return
    setBusy(true)
    setServerError(null)
    try {
      const res = await authApi.register(form)
      startFlow({
        purpose: 'register', request: form, phone: form.phone_number,
        hint: res.dev_otp_hint, expiresIn: res.otp_expires_in_seconds,
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
      <h1>Hesap oluştur</h1>
      <p className="auth-subtitle">Günlük kahven bir dokunuş uzağında.</p>
      <form onSubmit={submit} className="form" noValidate>
        <label>
          GSM numarası
          <input
            type="tel" inputMode="tel" autoComplete="tel" placeholder="0555 123 45 67"
            value={form.phone_number} onChange={update('phone_number', formatPhone)}
            aria-invalid={!!errors.phone_number || undefined}
          />
          {errors.phone_number && <span className="field-error">{errors.phone_number}</span>}
        </label>
        <label>
          Ad soyad
          <input autoComplete="name" value={form.full_name} onChange={update('full_name')}
            aria-invalid={!!errors.full_name || undefined} />
          {errors.full_name && <span className="field-error">{errors.full_name}</span>}
        </label>
        <label htmlFor="register-password">
          Şifre
          <PasswordInput
            id="register-password" autoComplete="new-password"
            value={form.password} onChange={update('password')}
            invalid={!!errors.password} describedBy="password-help"
          />
          {errors.password
            ? <span className="field-error">{errors.password}</span>
            : <span id="password-help" className="field-help">En az 8 karakter, bir harf ve bir rakam.</span>}
        </label>
        {serverError && <p className="form-error" role="alert">{serverError}</p>}
        <button className="btn" disabled={busy}>{busy ? 'Gönderiliyor…' : 'Kayıt ol'}</button>
      </form>
      <p className="auth-footer">Zaten hesabın var mı? <Link to="/login">Giriş yap</Link></p>
    </>
  )
}
