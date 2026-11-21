/**
 * Backend endpoint'leri tek yerde. Sayfalar doğrudan URL yazmaz, bu fonksiyonları kullanır.
 * Her fonksiyon backend yanıtındaki `data` kısmını döndürür; hata olursa ApiError fırlatır.
 */
import { api } from './client'

export const authApi = {
  register: (body) => api.post('/auth/register', body),
  login: (phone_number, password) => api.post('/auth/login', { phone_number, password }),
  verifyOtp: (phone_number, code) => api.post('/auth/verify-otp', { phone_number, code }),
  logout: (refresh_token) => api.post('/auth/logout', { refresh_token }),
}

export const usersApi = {
  me: () => api.get('/users/me'),
  updateMe: (body) => api.patch('/users/me', body),
}

export const shopsApi = {
  list: (params) => api.get('/shops', { params }),
  get: (shopId, params) => api.get(`/shops/${shopId}`, { params }),
  menu: (shopId) => api.get(`/shops/${shopId}/menu`),
}

export const subscriptionsApi = {
  plans: () => api.get('/subscriptions/plans'),
  me: () => api.get('/subscriptions/me'),
  start: (transaction_id) => api.post('/subscriptions', { transaction_id }),
  changePlan: (body) => api.patch('/subscriptions/me', body),
  cancel: () => api.delete('/subscriptions/me'),
}

export const paymentsApi = {
  process: (body) => api.post('/payments/process', body),
  history: () => api.get('/payments/me'),
}

export const ordersApi = {
  create: (body) => api.post('/orders', body),
  get: (orderId) => api.get(`/orders/${orderId}`),
  history: (params) => api.get('/orders/history', { params }),
  setFavorite: (orderId, is_favorite) => api.patch(`/orders/${orderId}/favorite`, { is_favorite }),
  reorder: (orderId) => api.post(`/orders/${orderId}/reorder`),
  incoming: (params) => api.get('/orders/incoming', { params }),
  updateStatus: (orderId, body) => api.patch(`/orders/${orderId}/status`, body),
  verifyQr: (qr_data) => api.post('/orders/verify-qr', { qr_data }),
}
