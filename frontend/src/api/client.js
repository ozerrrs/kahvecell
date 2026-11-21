import axios from 'axios'
import { useAuthStore } from '../store/authStore'

export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

/** Backend'den gelen hata ({ success:false, error:{ code, message, details } }). */
export class ApiError extends Error {
  constructor({ code, message, details, status }) {
    super(message)
    this.code = code
    this.details = details
    this.status = status
  }
}

export const api = axios.create({ baseURL: API_URL, timeout: 15000 })

// Her isteğe giriş anahtarını ekle.
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Aynı anda birden çok istek 401 alırsa tek bir yenileme isteği yapılır.
let refreshPromise = null

async function refreshTokens() {
  const { refreshToken, setSession, clearSession } = useAuthStore.getState()
  if (!refreshToken) throw new Error('no refresh token')
  try {
    // Yenileme isteği interceptor'lara takılmasın diye düz axios ile atılır.
    const res = await axios.post(`${API_URL}/auth/refresh`, { refresh_token: refreshToken })
    setSession(res.data.data)
    return res.data.data.access_token
  } catch (error) {
    clearSession()
    throw error
  }
}

api.interceptors.response.use(
  // Başarılı yanıtlarda sadece `data` kısmını döndür.
  (response) => (response.config.responseType === 'blob' ? response.data : response.data.data),
  async (error) => {
    const { config, response } = error
    const code = response?.data?.error?.code

    // Erişim anahtarının süresi dolduysa: sessizce yenile ve isteği bir kez tekrarla.
    if (response?.status === 401 && code === 'TOKEN_EXPIRED' && !config._retried) {
      config._retried = true
      try {
        refreshPromise ??= refreshTokens().finally(() => { refreshPromise = null })
        const token = await refreshPromise
        config.headers.Authorization = `Bearer ${token}`
        return api(config)
      } catch {
        // Yenileme de başarısızsa aşağıdaki hata akışına düş (oturum temizlendi).
      }
    }

    if (response?.data?.error) {
      throw new ApiError({ ...response.data.error, status: response.status })
    }
    throw new ApiError({
      code: 'NETWORK_ERROR',
      message: 'Sunucuya ulaşılamadı. Backend çalışıyor mu?',
      status: response?.status ?? 0,
    })
  },
)
