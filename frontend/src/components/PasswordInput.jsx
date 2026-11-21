import { useState } from 'react'

/** Göster/gizle düğmeli şifre alanı. */
export default function PasswordInput({ id, value, onChange, autoComplete = 'current-password', invalid, describedBy }) {
  const [visible, setVisible] = useState(false)
  return (
    <div className="password-field">
      <input
        id={id}
        type={visible ? 'text' : 'password'}
        autoComplete={autoComplete}
        value={value}
        onChange={onChange}
        aria-invalid={invalid || undefined}
        aria-describedby={describedBy}
      />
      <button
        type="button"
        className="password-toggle"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? 'Şifreyi gizle' : 'Şifreyi göster'}
        aria-pressed={visible}
      >
        {visible ? 'Gizle' : 'Göster'}
      </button>
    </div>
  )
}
