import { X, Zap, CheckCircle2, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { PLAN_BULLETS, PLAN_META, CONVERSION_EVENTS } from '../lib/plans'
import { trackEvent } from '../lib/tracking'

// Limit-type → human heading + upgrade nudge copy
const LIMIT_COPY = {
  ai_limit: {
    heading: 'Limite de respostas atingido',
    nudge: 'Você usou todas as respostas com IA deste mês.',
  },
  property_limit: {
    heading: 'Limite de imóveis atingido',
    nudge: 'Você atingiu o número máximo de imóveis do seu plano.',
  },
  template_limit: {
    heading: 'Limite de templates atingido',
    nudge: 'Você atingiu o limite de templates personalizados.',
  },
  channel_limit: {
    heading: 'Recurso do plano Pro',
    nudge: 'Esta integração está disponível a partir do plano Pro.',
  },
}

/**
 * Upgrade modal shown when user hits a plan limit.
 *
 * Props:
 *   error      { code, message, upgrade_to }  — from backend 402 response
 *   onClose    () => void
 */
export default function UpgradeModal({ error, onClose }) {
  const navigate = useNavigate()

  if (!error) return null

  const targetPlan = error.upgrade_to || 'pro'
  const meta = PLAN_META[targetPlan] || PLAN_META.pro
  const bullets = PLAN_BULLETS[targetPlan] || []

  // Pick copy based on error code if available, else generic
  const limitCopy = LIMIT_COPY[error.code] || {
    heading: 'Recurso indisponível no plano atual',
    nudge: error.message,
  }

  const handleUpgrade = () => {
    trackEvent(CONVERSION_EVENTS.UPGRADED_IN_APP, { plan: targetPlan, trigger: error.code })
    onClose()
    navigate('/billing')
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="w-10 h-10 bg-brand-100 rounded-xl flex items-center justify-center">
            <Zap className="w-5 h-5 text-brand-600" />
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 mt-1">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Copy */}
        <h3 className="font-bold text-slate-800 text-lg mb-1">{limitCopy.heading}</h3>
        <p className="text-slate-500 text-sm leading-relaxed mb-4">{limitCopy.nudge}</p>

        {/* Plan preview */}
        <div className="bg-brand-50 border border-brand-100 rounded-xl p-4 mb-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs font-bold text-brand-700 uppercase tracking-wide">
              Plano {meta.displayName}
            </span>
            {meta.badge && (
              <span className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                {meta.badge}
              </span>
            )}
          </div>
          <ul className="space-y-1.5">
            {bullets.slice(0, 5).map((f) => (
              <li key={f} className="flex items-center gap-2 text-xs text-slate-700">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />
                {f}
              </li>
            ))}
          </ul>
          <p className="text-xs text-brand-600 font-semibold mt-3">
            {meta.price}{' '}
            <span className="text-brand-400 font-normal">{meta.priceNote}</span>
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={handleUpgrade}
            className="btn-primary flex-1 flex items-center justify-center gap-2"
          >
            <ArrowRight className="w-4 h-4" />
            Ver planos e fazer upgrade
          </button>
          <button onClick={onClose} className="btn-secondary px-4 text-sm">
            Agora não
          </button>
        </div>

        <p className="text-center text-xs text-slate-400 mt-3">
          14 dias grátis · sem cartão de crédito
        </p>
      </div>
    </div>
  )
}
