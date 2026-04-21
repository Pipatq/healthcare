import axios from 'axios'

// In Docker: empty string → same-origin requests proxied by nginx to the backend.
// For local dev outside Docker: set VITE_API_BASE_URL=http://localhost:8000 in .env.local
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

const httpClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT from localStorage on every request.
httpClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Surface 401s clearly so the caller can redirect to login.
httpClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default httpClient
