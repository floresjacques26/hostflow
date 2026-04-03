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

export const CONVERSION_EVENTS = {
  VIEWED_PRICING_PAGE:  'viewed_pricing_page',
  CLICKED_PLAN_CTA:     'clicked_plan_cta',
  STARTED_CHECKOUT:     'started_checkout',
  CHECKOUT_COMPLETED:   'checkout_completed',
  CHECKOUT_CANCELED:    'checkout_canceled',
  VIEWED_SUCCESS_PAGE:  'viewed_success_page',
  UPGRADED_IN_APP:      'upgraded_in_app',
  STARTED_TRIAL:        'started_trial',
  CLICKED_COMPARISON:   'clicked_comparison',
}

export function trackEvent(name, properties = {}) {
  // Fire-and-forget — intentionally not awaited
  api.post('/events/track', { name, properties }).catch(() => {})
}
