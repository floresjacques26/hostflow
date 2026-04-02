import { create } from 'zustand'
import api from '../lib/api'

const useAuth = create((set) => ({
  user: JSON.parse(localStorage.getItem('hf_user') || 'null'),
  token: localStorage.getItem('hf_token') || null,

  login: async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password })
    localStorage.setItem('hf_token', data.access_token)
    localStorage.setItem('hf_user', JSON.stringify(data.user))
    set({ user: data.user, token: data.access_token })
    return data.user
  },

  register: async (name, email, password, attribution = {}) => {
    const { data } = await api.post('/auth/register', { name, email, password, ...attribution })
    localStorage.setItem('hf_token', data.access_token)
    localStorage.setItem('hf_user', JSON.stringify(data.user))
    set({ user: data.user, token: data.access_token })
    return data.user
  },

  logout: () => {
    localStorage.removeItem('hf_token')
    localStorage.removeItem('hf_user')
    set({ user: null, token: null })
  },
}))

export default useAuth
