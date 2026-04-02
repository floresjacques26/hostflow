import { create } from 'zustand'
import api from '../lib/api'

const useOnboarding = create((set, get) => ({
  state: null,
  loaded: false,

  fetch: async () => {
    try {
      const { data } = await api.get('/onboarding/')
      set({ state: data, loaded: true })
      return data
    } catch {
      return null
    }
  },

  skip: async () => {
    const { data } = await api.post('/onboarding/skip', { reason: 'user_skipped' })
    set({ state: data })
    return data
  },

  // Called locally after an action — optimistic update before next fetch
  markStep: (stepKey) => {
    const { state } = get()
    if (!state) return
    const STEP_MAP = { property: 1, ai_response: 2, integration: 3, template: 4 }
    const stepVal = STEP_MAP[stepKey]
    if (!stepVal) return
    const newStep = Math.max(state.current_step, stepVal)
    const newCompleted = newStep >= state.total_steps
    set({
      state: {
        ...state,
        current_step: newStep,
        completed_count: state.steps.filter((s) => s.step <= newStep).length,
        completed: newCompleted,
        steps: state.steps.map((s) => ({ ...s, done: s.step <= newStep })),
      },
    })
  },
}))

export default useOnboarding
