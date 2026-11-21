import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api/endpoints'
import { isValidEmail, isValidPhone } from '../utils/validation'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({ phone_number: '', full_name: '', email: '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState(null)
  const [busy, setBusy] = useState(false)

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  function validate() {
    const next = {}
    if (!isValidPhone(form.phone_number)) next.phone_number = 'Geçerli bir GSM numarası girin.'
    if (form.full_name.trim().length < 2) next.full_name = 'Ad soyad en az 2 karakter olmalı.'
    if (form.email && !isValidEmail(form.email)) next.email = 'Geçerli bir e-posta girin.'
    setErrors(next)
    return Object.keys(next).length === 0
  }

  async function submit(event) {
    event.preventDefault()
    if (!validate()) return
    setBusy(true)
    setServerError(null)
    try {
      const res = await authApi.register({ ...form, email: form.email || null })
      // Kod gönderildi; doğrulama giriş sayfasının 2. adımında yapılır.
      navigate('/login', { state: { phone: form.phone_number, hint: res.dev_otp_hint } })
    } catch (err) {
      setServerError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="narrow">
      <h1>Kayıt ol</h1>
      <form onSubmit={submit} className="form" noValidate>
        <label>
          GSM numarası
          <input type="tel" inputMode="tel" autoComplete="tel" placeholder="0555 123 45 67"
            value={form.phone_number} onChange={update('phone_number')} aria-invalid={!!errors.phone_number} />
          {errors.phone_number && <span className="field-error">{errors.phone_number}</span>}
        </label>
        <label>
          Ad soyad
          <input autoComplete="name" value={form.full_name} onChange={update('full_name')}
            aria-invalid={!!errors.full_name} />
          {errors.full_name && <span className="field-error">{errors.full_name}</span>}
        </label>
        <label>
          E-posta <span className="muted">(isteğe bağlı)</span>
          <input type="email" autoComplete="email" value={form.email} onChange={update('email')}
            aria-invalid={!!errors.email} />
          {errors.email && <span className="field-error">{errors.email}</span>}
        </label>
        {serverError && <p className="form-error" role="alert">{serverError}</p>}
        <button className="btn" disabled={busy}>{busy ? 'Gönderiliyor…' : 'Kayıt ol'}</button>
        <p className="muted">Zaten hesabın var mı? <Link to="/login">Giriş yap</Link></p>
      </form>
    </section>
  )
}
