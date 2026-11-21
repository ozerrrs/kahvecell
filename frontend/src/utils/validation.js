/** İstemci tarafı form doğrulamaları (backend de aynı kuralları ayrıca uygular). */

function phoneDigits(value) {
  let digits = (value ?? '').replace(/\D/g, '')
  if (digits.length === 12 && digits.startsWith('90')) digits = digits.slice(2)
  else if (digits.startsWith('0')) digits = digits.slice(1)
  return digits
}

/** '0555 123 45 67', '5551234567', '+90 555…' biçimlerini kabul eder. */
export function isValidPhone(value) {
  return /^5\d{9}$/.test(phoneDigits(value))
}

/** Yazarken '0555 123 45 67' biçimine sokar. */
export function formatPhone(value) {
  const d = phoneDigits(value).slice(0, 10)
  const parts = [d.slice(0, 3), d.slice(3, 6), d.slice(6, 8), d.slice(8, 10)].filter(Boolean)
  return d ? `0${parts.join(' ')}` : ''
}

export function isValidEmail(value) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test((value ?? '').trim())
}

/** Backend ile aynı kural: en az 8 karakter, en az bir harf ve bir rakam. Hata yoksa null döner. */
export function passwordError(value) {
  if (!value || value.length < 8) return 'Şifre en az 8 karakter olmalı.'
  if (!/[A-Za-zÇĞİÖŞÜçğıöşü]/.test(value) || !/\d/.test(value)) return 'Şifre en az bir harf ve bir rakam içermeli.'
  return null
}
