import { create } from 'zustand'
import api from '../lib/api'

const useBilling = create((set, get) => ({
  subscription: null,
  usage: null,
  plans: [],
  loaded: false,

  fetchAll: async () => {
    const [subRes, usageRes, plansRes] = await Promise.all([
      api.get('/billing/subscription'),
      api.get('/billing/usage'),
      api.get('/billing/plans'),
    ])
    set({
      subscription: subRes.data,
      usage: usageRes.data,
      plans: plansRes.data,
      loaded: true,
    })
  },

  refreshSubscription: async () => {
    const { data } = await api.get('/billing/subscription')
    set({ subscription: data })
    return data
  },

  refreshUsage: async () => {
    const { data } = await api.get('/billing/usage')
    set({ usage: data })
    return data
  },

  startTrial: async () => {
    const { data } = await api.post('/billing/start-trial')
    set({ subscription: data })
    return data
  },

  createCheckout: async (priceId) => {
    const { data } = await api.post('/billing/checkout', { price_id: priceId })
    return data.checkout_url
  },

  openPortal: async () => {
    const { data } = await api.post('/billing/portal', {
      return_url: window.location.origin + '/billing',
    })
    window.location.href = data.portal_url
  },
}))

export default useBilling
