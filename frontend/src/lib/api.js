import axios from 'axios'

// In production (Vercel), VITE_API_URL must point to the Railway backend,
// e.g. https://api.hostflow.com.br/api/v1
// In development, falls back to '/api/v1' which is proxied by vite.config.js.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('hf_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('hf_token')
      localStorage.removeItem('hf_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api
