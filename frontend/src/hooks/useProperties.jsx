import { create } from 'zustand'
import api from '../lib/api'

const useProperties = create((set, get) => ({
  properties: [],
  loaded: false,

  fetch: async () => {
    const { data } = await api.get('/properties/')
    set({ properties: data, loaded: true })
    return data
  },

  add: (property) => set((s) => ({ properties: [...s.properties, property] })),

  update: (property) =>
    set((s) => ({
      properties: s.properties.map((p) => (p.id === property.id ? property : p)),
    })),

  remove: (id) =>
    set((s) => ({ properties: s.properties.filter((p) => p.id !== id) })),
}))

export default useProperties
