/** İstemci tarafı form doğrulamaları (backend de aynı kuralları ayrıca uygular). */

/** '0555 123 45 67', '5551234567', '+90 555…' biçimlerini kabul eder. */
export function isValidPhone(value) {
  let digits = (value ?? '').replace(/\D/g, '')
  if (digits.length === 12 && digits.startsWith('90')) digits = digits.slice(2)
  else if (digits.length === 11 && digits.startsWith('0')) digits = digits.slice(1)
  return /^5\d{9}$/.test(digits)
}

export function isValidEmail(value) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test((value ?? '').trim())
}
