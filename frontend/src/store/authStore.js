import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * Oturum bilgisi (giriş yapan kullanıcı + anahtarlar).
 * `persist` sayesinde tarayıcıda saklanır; sayfa yenilense de giriş korunur.
 */
export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,

      setSession: ({ user, access_token, refresh_token }) =>
        set((state) => ({
          user: user ?? state.user,
          accessToken: access_token,
          refreshToken: refresh_token,
        })),

      setUser: (user) => set({ user }),

      clearSession: () => set({ user: null, accessToken: null, refreshToken: null }),
    }),
    { name: 'kahvecell-auth' },
  ),
)

export const selectIsLoggedIn = (state) => Boolean(state.accessToken)
