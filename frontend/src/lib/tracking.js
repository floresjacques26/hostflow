/**
 * Conversion event tracking.
 *
 * Fires a fire-and-forget POST to /events so admin analytics can surface
 * pricing funnel data. Silently swallows errors — tracking must never
 * break the user experience.
 *
 * Usage:
 *   import { trackEvent } from '../lib/tracking'
 *   trackEvent('viewed_pricing_page')
 *   trackEvent('clicked_plan_cta', { plan: 'pro', source: 'pricing_page' })
 */
import api from './api'

export function trackEvent(name, properties = {}) {
  // Fire-and-forget — intentionally not awaited
  api.post('/events/track', { name, properties }).catch(() => {})
}
