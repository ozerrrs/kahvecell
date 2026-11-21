import { create } from 'zustand'

/**
 * Kayıt/giriş ile kod doğrulama ekranı arasında taşınan geçici bilgiler.
 * Bilerek tarayıcıya kaydedilmez (persist yok): şifre sadece bellekte, akış süresince tutulur
 * ve "kodu tekrar gönder" için kullanılır. Doğrulama bitince temizlenir.
 */
export const useOtpFlowStore = create((set) => ({
  flow: null, // { purpose: 'register' | 'login', request: {...}, phone, hint, expiresIn, sentAt, redirectTo }

  start: (flow) => set({ flow: { ...flow, sentAt: Date.now() } }),
  resent: (hint, expiresIn) => set((s) => ({ flow: { ...s.flow, hint, expiresIn, sentAt: Date.now() } })),
  clear: () => set({ flow: null }),
}))
