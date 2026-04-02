import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  AlertCircle, Clock, CreditCard, ExternalLink, RefreshCw,
  CheckCircle2, ArrowRight, Zap,
} from 'lucide-react'
import toast from 'react-hot-toast'
import Layout from '../components/Layout'
import PlanBadge from '../components/PlanBadge'
import UsageBar from '../components/UsageBar'
import PricingCard from '../components/PricingCard'
import useBilling from '../hooks/useBilling'
import { trackEvent } from '../lib/tracking'
import { CONVERSION_EVENTS } from '../lib/plans'
import clsx from 'clsx'

const STATUS_INFO = {
  free:      { label: 'Plano gratuito',    color: 'text-slate-600',  bg: 'bg-slate-100' },
  trialing:  { label: 'Trial ativo',        color: 'text-brand-700',  bg: 'bg-brand-100' },
  active:    { label: 'Assinatura ativa',   color: 'text-green-700',  bg: 'bg-green-100' },
  past_due:  { label: 'Pagamento pendente', color: 'text-orange-700', bg: 'bg-orange-100' },
  canceled:  { label: 'Cancelado',          color: 'text-red-700',    bg: 'bg-red-100' },
  unpaid:    { label: 'Não pago',           color: 'text-red-700',    bg: 'bg-red-100' },
}

function daysUntil(isoDate) {
  if (!isoDate) return null
  const ms = new Date(isoDate) - Date.now()
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)))
}

// ── Post-checkout success banner (shown after Stripe redirects back) ──────────

function SuccessBanner({ planName, onDismiss }) {
  return (
    <div className="mb-6 p-5 bg-green-50 border border-green-200 rounded-xl flex items-start gap-4">
      <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center shrink-0">
        <CheckCircle2 className="w-5 h-5 text-green-600" />
      </div>
      <div className="flex-1">
        <p className="font-semibold text-green-800 text-sm">Assinatura ativada com sucesso!</p>
        <p className="text-green-700 text-xs mt-0.5">
          Seu plano <strong className="capitalize">{planName}</strong> está ativo. Explore todos os recursos disponíveis.
        </p>
        <div className="flex gap-3 mt-3">
          <Link to="/integrations" className="text-xs text-green-700 font-semibold hover:underline flex items-center gap-1">
            Conectar Gmail / WhatsApp <ArrowRight className="w-3 h-3" />
          </Link>
          <Link to="/inbox" className="text-xs text-green-700 font-semibold hover:underline flex items-center gap-1">
            Abrir caixa de entrada <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
      <button onClick={onDismiss} className="text-green-400 hover:text-green-600 text-lg leading-none shrink-0">×</button>
    </div>
  )
}

export default function Billing() {
  const [searchParams] = useSearchParams()
  const { subscription, usage, plans, loaded, fetchAll, startTrial, createCheckout, openPortal } = useBilling()
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [trialLoading, setTrialLoading] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)

  useEffect(() => {
    fetchAll().catch(() => toast.error('Erro ao carregar dados de billing'))
  }, [])

  useEffect(() => {
    if (searchParams.get('success') === '1') {
      setShowSuccess(true)
      trackEvent(CONVERSION_EVENTS.CHECKOUT_COMPLETED, { source: 'stripe_redirect' })
      fetchAll()
    }
    if (searchParams.get('canceled') === '1') {
      toast('Checkout cancelado.')
      trackEvent(CONVERSION_EVENTS.CHECKOUT_CANCELED)
    }
  }, [])

  const handleCheckout = async (priceId) => {
    if (!priceId) {
      toast.error('Plano não configurado. Adicione o STRIPE_PRICE_ID no backend.')
      return
    }
    setCheckoutLoading(true)
    trackEvent(CONVERSION_EVENTS.STARTED_CHECKOUT, { source: 'billing_page' })
    try {
      const url = await createCheckout(priceId)
      window.location.href = url
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao iniciar checkout')
    } finally {
      setCheckoutLoading(false)
    }
  }

  const handleStartTrial = async () => {
    setTrialLoading(true)
    try {
      await startTrial()
      trackEvent(CONVERSION_EVENTS.STARTED_TRIAL)
      toast.success('Trial de 14 dias iniciado! Aproveite todos os recursos Pro.')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao iniciar trial')
    } finally {
      setTrialLoading(false)
    }
  }

  if (!loaded) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto text-center py-20 text-slate-400 text-sm">
          Carregando...
        </div>
      </Layout>
    )
  }

  const sub = subscription
  const statusInfo = STATUS_INFO[sub.subscription_status] || STATUS_INFO.free
  const effectivePlan = sub.effective_plan
  const isFreePlan = effectivePlan === 'free'
  const canStartTrial = sub.subscription_status === 'free' && !sub.stripe_subscription_id
  const hasActiveSubscription = ['active', 'trialing', 'past_due'].includes(sub.subscription_status)
  const trialDaysLeft = daysUntil(sub.trial_ends_at)

  const fmt = (dt) => dt ? new Date(dt).toLocaleDateString('pt-BR') : '—'

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-800">Assinatura</h1>
          <p className="text-slate-500 text-sm mt-1">Gerencie seu plano e acompanhe o uso.</p>
        </div>

        {/* Post-checkout success banner */}
        {showSuccess && (
          <SuccessBanner planName={effectivePlan} onDismiss={() => setShowSuccess(false)} />
        )}

        {/* Past due warning */}
        {sub.subscription_status === 'past_due' && (
          <div className="mb-6 p-4 bg-orange-50 border border-orange-200 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-orange-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-orange-800 text-sm">Pagamento pendente</p>
              <p className="text-orange-700 text-xs mt-0.5">
                Houve uma falha no seu pagamento. Atualize seu método de pagamento para manter o acesso.
              </p>
              <button onClick={openPortal} className="text-xs text-orange-600 hover:underline mt-1 font-medium flex items-center gap-1">
                <ExternalLink className="w-3 h-3" /> Atualizar pagamento
              </button>
            </div>
          </div>
        )}

        {/* Trial active banner */}
        {sub.is_trial_active && (
          <div className={clsx(
            'mb-6 p-4 rounded-xl flex items-start gap-3 border',
            trialDaysLeft !== null && trialDaysLeft <= 3
              ? 'bg-orange-50 border-orange-200'
              : 'bg-brand-50 border-brand-200',
          )}>
            <Clock className={clsx('w-5 h-5 shrink-0 mt-0.5', trialDaysLeft !== null && trialDaysLeft <= 3 ? 'text-orange-500' : 'text-brand-500')} />
            <div className="flex-1">
              <p className={clsx('font-medium text-sm', trialDaysLeft !== null && trialDaysLeft <= 3 ? 'text-orange-800' : 'text-brand-800')}>
                {trialDaysLeft !== null && trialDaysLeft <= 1
                  ? 'Trial expira hoje!'
                  : trialDaysLeft !== null && trialDaysLeft <= 3
                    ? `Trial expira em ${trialDaysLeft} dias!`
                    : 'Trial Pro ativo'}
              </p>
              <p className={clsx('text-xs mt-0.5', trialDaysLeft !== null && trialDaysLeft <= 3 ? 'text-orange-700' : 'text-brand-700')}>
                Expira em <strong>{fmt(sub.trial_ends_at)}</strong>. Assine antes para não perder o acesso.
              </p>
            </div>
            <button
              onClick={() => handleCheckout(plans.find(p => p.name === 'pro')?.price_id)}
              disabled={checkoutLoading}
              className="btn-primary text-xs py-1.5 px-3 shrink-0"
            >
              Assinar agora
            </button>
          </div>
        )}

        {/* Current plan + usage */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <div className="lg:col-span-1 card p-6">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Plano atual</h2>

            <div className="flex items-center gap-2 mb-4">
              <PlanBadge plan={effectivePlan} size="md" />
              <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full', statusInfo.bg, statusInfo.color)}>
                {statusInfo.label}
              </span>
            </div>

            <div className="space-y-2 text-sm text-slate-600 mb-5">
              {sub.current_period_end && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Próxima cobrança</span>
                  <span className="font-medium text-slate-800">{fmt(sub.current_period_end)}</span>
                </div>
              )}
              {sub.trial_ends_at && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Trial expira</span>
                  <span className={clsx('font-medium', trialDaysLeft !== null && trialDaysLeft <= 3 ? 'text-orange-600' : 'text-slate-800')}>
                    {fmt(sub.trial_ends_at)}
                    {trialDaysLeft !== null && ` (${trialDaysLeft}d)`}
                  </span>
                </div>
              )}
              {sub.canceled_at && (
                <div className="flex justify-between">
                  <span className="text-slate-500">Cancelado em</span>
                  <span className="font-medium text-slate-800">{fmt(sub.canceled_at)}</span>
                </div>
              )}
            </div>

            <div className="space-y-2">
              {hasActiveSubscription && (
                <button
                  onClick={openPortal}
                  className="btn-secondary w-full flex items-center justify-center gap-2 text-sm"
                >
                  <CreditCard className="w-4 h-4" />
                  Gerenciar assinatura
                  <ExternalLink className="w-3 h-3" />
                </button>
              )}
              {canStartTrial && (
                <button
                  onClick={handleStartTrial}
                  disabled={trialLoading}
                  className="w-full text-sm py-2.5 px-4 rounded-xl border-2 border-brand-300 text-brand-700 font-semibold hover:bg-brand-50 transition-colors flex items-center justify-center gap-2"
                >
                  <Zap className="w-4 h-4" />
                  {trialLoading ? 'Iniciando...' : 'Testar Pro grátis por 14 dias'}
                </button>
              )}
              {canStartTrial && (
                <p className="text-center text-xs text-slate-400">Sem cartão de crédito</p>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Uso este mês {usage?.month ? `— ${usage.month}` : ''}
              </h2>
              <button
                onClick={() => useBilling.getState().refreshUsage()}
                className="text-slate-400 hover:text-slate-600"
                title="Atualizar"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-5">
              <UsageBar
                label="Respostas geradas com IA"
                used={usage?.ai_responses ?? 0}
                limit={usage?.ai_responses_limit}
              />
              <UsageBar
                label="Imóveis cadastrados"
                used={usage?.properties_count ?? 0}
                limit={usage?.properties_limit}
              />
              <UsageBar
                label="Templates personalizados"
                used={usage?.custom_templates_count ?? 0}
                limit={usage?.custom_templates_limit}
              />
            </div>

            {isFreePlan && (
              <div className="mt-5 p-3 bg-brand-50 border border-brand-100 rounded-xl text-xs text-brand-700 flex items-center gap-2">
                <Zap className="w-3.5 h-3.5 shrink-0" />
                Faça upgrade para o Pro e acesse Gmail, WhatsApp, auto-envio e muito mais.
              </div>
            )}
          </div>
        </div>

        {/* Plan selection */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-slate-800">Planos disponíveis</h2>
            <p className="text-sm text-slate-500">Escolha o plano ideal para o seu negócio.</p>
          </div>
          <Link to="/pricing" className="text-xs text-brand-600 font-medium hover:underline">
            Comparativo completo →
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {plans.map((plan) => (
            <PricingCard
              key={plan.name}
              planName={plan.name}
              priceId={plan.price_id}
              mode="inapp"
              isCurrentPlan={effectivePlan === plan.name}
              onSelect={handleCheckout}
              loading={checkoutLoading}
              trialDays={plan.trial_days || 0}
            />
          ))}
        </div>

        {/* Downgrade note */}
        {hasActiveSubscription && (
          <div className="mt-6 p-4 bg-slate-50 rounded-xl text-xs text-slate-500">
            <strong className="text-slate-700">Para cancelar ou fazer downgrade:</strong>{' '}
            acesse o portal de gerenciamento de assinatura acima. Após o cancelamento, você mantém o
            acesso até o fim do período pago. No downgrade para Free, seus dados são preservados e
            os limites do plano Free passam a valer no próximo ciclo.
          </div>
        )}
      </div>
    </Layout>
  )
}
