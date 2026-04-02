import { CheckCircle2, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import { PLAN_META, PLAN_BULLETS } from '../lib/plans'

/**
 * Reusable pricing card — used on /pricing (public) and Billing page (in-app).
 *
 * Props:
 *   planName        'free' | 'pro' | 'business'
 *   priceId         Stripe price ID (null if not configured)
 *   mode            'public' | 'inapp'
 *   isCurrentPlan   bool
 *   onSelect        (priceId) => void  — called in inapp mode
 *   loading         bool
 *   trialDays       number
 */
export default function PricingCard({
  planName,
  priceId,
  mode = 'public',
  isCurrentPlan = false,
  onSelect,
  loading = false,
  trialDays = 0,
}) {
  const meta = PLAN_META[planName]
  const bullets = PLAN_BULLETS[planName] || []
  const isFree = planName === 'free'
  const isHighlight = meta.highlight

  const ringClass = {
    brand: 'border-brand-400 shadow-lg shadow-brand-100',
    purple: 'border-purple-300 shadow-sm shadow-purple-100',
    slate: 'border-slate-200',
  }[meta.color]

  const ctaLabel = mode === 'public' ? meta.cta.public : meta.cta.inApp

  return (
    <div
      className={clsx(
        'relative rounded-2xl border p-6 flex flex-col',
        isHighlight ? ringClass : 'border-slate-200',
        isCurrentPlan && 'border-green-300 bg-green-50/20',
      )}
    >
      {/* Popular badge */}
      {isHighlight && !isCurrentPlan && (
        <div className="absolute -top-3.5 left-1/2 -translate-x-1/2">
          <span className="bg-brand-600 text-white text-xs font-bold px-3 py-1 rounded-full tracking-wide">
            MAIS POPULAR
          </span>
        </div>
      )}

      {/* Header */}
      <div className="mb-5">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="font-bold text-xl text-slate-900">{meta.displayName}</h3>
          {meta.badge && !isCurrentPlan && (
            <span className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">
              {meta.badge}
            </span>
          )}
          {isCurrentPlan && (
            <span className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full">
              Plano atual
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500">{meta.description}</p>
      </div>

      {/* Price */}
      <div className="flex items-end gap-1 mb-6">
        <span className="text-3xl font-extrabold text-slate-900">{meta.price}</span>
        <span className="text-sm text-slate-400 mb-1">{meta.priceNote}</span>
      </div>

      {/* Features */}
      <ul className="space-y-2.5 flex-1 mb-6">
        {bullets.map((f) => (
          <li key={f} className="flex items-start gap-2.5 text-sm text-slate-600">
            <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
            {f}
          </li>
        ))}
      </ul>

      {/* CTA */}
      {isCurrentPlan ? (
        <div className="text-center py-2.5 text-sm font-medium text-green-700 bg-green-50 rounded-xl border border-green-200">
          Plano atual ativo
        </div>
      ) : isFree ? (
        mode === 'public' ? (
          <Link
            to="/register"
            className="block text-center text-sm font-semibold py-2.5 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 transition-colors"
          >
            {ctaLabel}
          </Link>
        ) : (
          <div className="text-center py-2.5 text-sm text-slate-400">—</div>
        )
      ) : mode === 'public' ? (
        <Link
          to="/register"
          className={clsx(
            'block text-center text-sm font-semibold py-2.5 rounded-xl transition-colors',
            isHighlight
              ? 'bg-brand-600 text-white hover:bg-brand-700'
              : 'bg-purple-600 text-white hover:bg-purple-700',
          )}
        >
          {ctaLabel}
        </Link>
      ) : (
        <button
          onClick={() => onSelect?.(priceId)}
          disabled={loading || !priceId}
          className={clsx(
            'w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-colors',
            isHighlight
              ? 'bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50'
              : 'bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50',
          )}
        >
          <Zap className="w-4 h-4" />
          {loading ? 'Aguarde...' : ctaLabel}
        </button>
      )}

      {trialDays > 0 && !isCurrentPlan && !isFree && mode === 'inapp' && (
        <p className="text-center text-xs text-slate-400 mt-2">
          {trialDays} dias grátis · sem cartão de crédito
        </p>
      )}
    </div>
  )
}
