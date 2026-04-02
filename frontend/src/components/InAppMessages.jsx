/**
 * Context-aware in-app banners.
 * Renders the single highest-priority message at the top of each page.
 * All rules are centralised in _computeMessages — easy to extend.
 */
import { Link } from 'react-router-dom'
import { Clock, Zap, AlertTriangle, XCircle, RefreshCw } from 'lucide-react'
import useBilling from '../hooks/useBilling'
import clsx from 'clsx'

export default function InAppMessages() {
  const { subscription, usage } = useBilling()

  if (!subscription || !usage) return null

  const messages = _computeMessages(subscription, usage)
  if (messages.length === 0) return null

  const msg = messages[0]

  return (
    <div className={clsx(
      'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm mb-5',
      msg.variant === 'warning' && 'bg-orange-50 border border-orange-200 text-orange-800',
      msg.variant === 'info'    && 'bg-brand-50 border border-brand-200 text-brand-800',
      msg.variant === 'danger'  && 'bg-red-50 border border-red-200 text-red-800',
      msg.variant === 'success' && 'bg-green-50 border border-green-200 text-green-800',
    )}>
      <msg.Icon className="w-4 h-4 shrink-0" />
      <span className="flex-1">{msg.text}</span>
      {msg.cta && (
        <Link
          to={msg.cta.to}
          className={clsx(
            'text-xs font-semibold whitespace-nowrap underline underline-offset-2',
            msg.variant === 'warning' && 'text-orange-700',
            msg.variant === 'info'    && 'text-brand-700',
            msg.variant === 'danger'  && 'text-red-700',
            msg.variant === 'success' && 'text-green-700',
          )}
        >
          {msg.cta.label}
        </Link>
      )}
    </div>
  )
}

function _computeMessages(subscription, usage) {
  const msgs = []

  // ── Payment failed / past_due ─────────────────────────────────────
  if (subscription.subscription_status === 'past_due') {
    msgs.push({
      Icon: AlertTriangle,
      variant: 'danger',
      text: 'Seu pagamento falhou. Atualize o método de pagamento para não perder o acesso.',
      cta: { to: '/billing', label: 'Resolver agora' },
      priority: 30,
    })
  }

  // ── Subscription canceled ─────────────────────────────────────────
  if (subscription.subscription_status === 'canceled') {
    msgs.push({
      Icon: XCircle,
      variant: 'danger',
      text: 'Sua assinatura foi cancelada. Você está no plano Free.',
      cta: { to: '/billing', label: 'Reativar' },
      priority: 25,
    })
  }

  // ── AI response limit reached ─────────────────────────────────────
  if (usage.ai_responses_limit !== null) {
    const pct = usage.ai_responses / usage.ai_responses_limit
    if (pct >= 1) {
      msgs.push({
        Icon: AlertTriangle,
        variant: 'danger',
        text: `Você atingiu o limite de ${usage.ai_responses_limit} respostas do plano Free.`,
        cta: { to: '/billing', label: 'Fazer upgrade' },
        priority: 20,
      })
    } else if (pct >= 0.8) {
      msgs.push({
        Icon: Zap,
        variant: 'warning',
        text: `Você usou ${usage.ai_responses} de ${usage.ai_responses_limit} respostas este mês.`,
        cta: { to: '/billing', label: 'Ver planos' },
        priority: 8,
      })
    }
  }

  // ── Trial ending soon ─────────────────────────────────────────────
  if (subscription.is_trial_active) {
    const daysLeft = _daysUntil(subscription.trial_ends_at)
    if (daysLeft <= 1) {
      msgs.push({
        Icon: Clock,
        variant: 'warning',
        text: 'Seu trial Pro termina hoje. Assine agora para não perder o acesso.',
        cta: { to: '/billing', label: 'Assinar Pro' },
        priority: 15,
      })
    } else if (daysLeft <= 3) {
      msgs.push({
        Icon: Clock,
        variant: 'warning',
        text: `Seu trial Pro termina em ${daysLeft} dias. Assine para não perder o acesso.`,
        cta: { to: '/billing', label: 'Assinar Pro' },
        priority: 10,
      })
    } else {
      msgs.push({
        Icon: Clock,
        variant: 'info',
        text: `Você está no trial Pro — ${daysLeft} dias restantes.`,
        cta: { to: '/billing', label: 'Ver planos' },
        priority: 1,
      })
    }
  }

  // ── Trial just expired (subscription_status still "trialing" but trial_ends_at in the past) ──
  if (
    subscription.subscription_status === 'trialing' &&
    subscription.trial_ends_at &&
    new Date(subscription.trial_ends_at) < new Date() &&
    !subscription.is_trial_active
  ) {
    msgs.push({
      Icon: RefreshCw,
      variant: 'warning',
      text: 'Seu trial Pro expirou. Assine para manter o acesso completo.',
      cta: { to: '/billing', label: 'Assinar agora' },
      priority: 12,
    })
  }

  return msgs.sort((a, b) => b.priority - a.priority)
}

function _daysUntil(dateStr) {
  if (!dateStr) return 0
  const diff = new Date(dateStr) - new Date()
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)))
}
