import { useEffect, useState } from 'react'
import { X, AlertTriangle, CheckCircle2, Circle, Clock, Mail, Building2, FileText, Zap, ExternalLink } from 'lucide-react'
import api from '../lib/api'
import PlanBadge from './PlanBadge'
import clsx from 'clsx'

// ── Status/risk displays ──────────────────────────────────────────────────────

const STATUS_LABELS = {
  active: 'Ativo', trialing: 'Trial', free: 'Free',
  past_due: 'Pag. pendente', canceled: 'Cancelado', unpaid: 'Não pago',
}
const STATUS_COLORS = {
  active: 'text-green-700 bg-green-100',
  trialing: 'text-brand-700 bg-brand-100',
  free: 'text-slate-600 bg-slate-100',
  past_due: 'text-orange-700 bg-orange-100',
  canceled: 'text-red-600 bg-red-100',
}
const RISK_COLORS = {
  low: 'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high: 'bg-red-100 text-red-600',
}
const RISK_LABELS = { low: 'Baixo', medium: 'Médio', high: 'Alto' }

// ── Section ───────────────────────────────────────────────────────────────────

function Section({ title, children }) {
  return (
    <div className="mb-6">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">{title}</h3>
      {children}
    </div>
  )
}

function Row({ label, value, valueClass = '' }) {
  return (
    <div className="flex justify-between items-start py-1.5 border-b border-slate-50 last:border-0">
      <span className="text-xs text-slate-500">{label}</span>
      <span className={clsx('text-xs font-medium text-slate-700 text-right max-w-48', valueClass)}>{value ?? '—'}</span>
    </div>
  )
}

// ── Onboarding steps ──────────────────────────────────────────────────────────

function OnboardingSteps({ step }) {
  const steps = [
    { n: 1, label: 'Cadastrou imóvel' },
    { n: 2, label: 'Gerou resposta com IA' },
    { n: 3, label: 'Usou calculadora' },
  ]
  return (
    <div className="space-y-1.5">
      {steps.map(s => (
        <div key={s.n} className="flex items-center gap-2">
          {step >= s.n
            ? <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />
            : <Circle className="w-3.5 h-3.5 text-slate-300 shrink-0" />}
          <span className={clsx('text-xs', step >= s.n ? 'text-slate-700' : 'text-slate-400')}>
            {s.label}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Health bar ────────────────────────────────────────────────────────────────

function HealthBar({ score }) {
  const color = score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={clsx('h-full rounded-full transition-all', color)} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs font-semibold text-slate-600 w-6 text-right">{score}</span>
    </div>
  )
}

// ── Event log ─────────────────────────────────────────────────────────────────

const EVENT_ICONS = {
  signup: '🆕',
  login: '🔑',
  generated_response: '🤖',
  created_property: '🏠',
  used_calculator: '🧮',
  upgraded_plan: '⬆️',
  started_trial: '🎁',
  opened_billing: '💳',
  hit_usage_limit: '🚫',
  onboarding_completed: '✅',
  onboarding_skipped: '⏭️',
}

// ── Drawer ────────────────────────────────────────────────────────────────────

export default function UserDetailDrawer({ userId, onClose }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api.get(`/admin/users/${userId}`)
      .then(({ data }) => { if (!cancelled) setUser(data) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [userId])

  const fmt = (dt) => dt ? new Date(dt).toLocaleString('pt-BR') : '—'
  const fmtDate = (dt) => dt ? new Date(dt).toLocaleDateString('pt-BR') : '—'

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/20 backdrop-blur-[1px]"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-lg bg-white shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-brand-100 flex items-center justify-center text-brand-600 font-bold text-sm">
              {user?.name?.[0]?.toUpperCase() || '?'}
            </div>
            <div>
              <p className="font-semibold text-slate-800 text-sm">{user?.name || '...'}</p>
              <p className="text-xs text-slate-400">{user?.email || ''}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-50">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">Carregando...</div>
        ) : !user ? (
          <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">Erro ao carregar usuário</div>
        ) : (
          <div className="flex-1 overflow-y-auto p-5">

            {/* Health + Risk + Action */}
            <div className="mb-6 p-4 bg-slate-50 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500 font-medium">Saúde do usuário</span>
                <div className="flex items-center gap-2">
                  <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full', RISK_COLORS[user.churn_risk])}>
                    Risco: {RISK_LABELS[user.churn_risk]}
                  </span>
                  <PlanBadge plan={user.effective_plan} />
                </div>
              </div>
              <HealthBar score={user.health_score} />
              <div className="flex items-start gap-2 pt-1">
                {user.churn_risk === 'high'
                  ? <AlertTriangle className="w-3.5 h-3.5 text-orange-500 shrink-0 mt-0.5" />
                  : <Zap className="w-3.5 h-3.5 text-brand-500 shrink-0 mt-0.5" />}
                <p className="text-xs text-slate-600 font-medium">{user.recommended_action}</p>
              </div>
            </div>

            {/* Billing */}
            <Section title="Assinatura & Billing">
              <div className="space-y-0">
                <Row label="Status" value={
                  <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full', STATUS_COLORS[user.subscription_status])}>
                    {STATUS_LABELS[user.subscription_status] || user.subscription_status}
                  </span>
                } />
                <Row label="Trial ativo" value={user.is_trial_active ? `Sim (${user.trial_days_remaining}d restantes)` : 'Não'} />
                <Row label="Trial expira" value={fmtDate(user.trial_ends_at)} />
                <Row label="Próx. cobrança" value={fmtDate(user.current_period_end)} />
                <Row label="Cancelado em" value={fmtDate(user.canceled_at)} />
              </div>
            </Section>

            {/* Usage */}
            <Section title="Uso">
              <div className="space-y-0">
                <Row label="Respostas IA este mês" value={user.ai_responses_month} />
                <Row label="Imóveis cadastrados" value={user.properties_count} />
                <Row label="Templates personalizados" value={user.templates_count} />
              </div>
            </Section>

            {/* Account */}
            <Section title="Conta">
              <div className="space-y-0">
                <Row label="Cadastro" value={fmt(user.created_at)} />
                <Row label="Último login" value={fmt(user.last_login_at)} />
                <Row label="Última atividade" value={fmt(user.last_event_at)} />
                <Row label="Onboarding" value={user.onboarding_completed ? 'Concluído' : `Passo ${user.onboarding_step}/3`} />
              </div>
            </Section>

            {/* Onboarding steps */}
            <Section title="Checklist de onboarding">
              <OnboardingSteps step={user.onboarding_step} />
            </Section>

            {/* Recent events */}
            {user.recent_events?.length > 0 && (
              <Section title="Eventos recentes">
                <div className="space-y-1.5 max-h-44 overflow-y-auto">
                  {user.recent_events.map((e, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span className="text-base leading-none mt-0.5">{EVENT_ICONS[e.event_name] || '·'}</span>
                      <div>
                        <p className="text-xs font-medium text-slate-700">{e.event_name}</p>
                        <p className="text-xs text-slate-400">{fmt(e.created_at)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Recent emails */}
            {user.recent_emails?.length > 0 && (
              <Section title="E-mails enviados">
                <div className="space-y-2">
                  {user.recent_emails.map((e, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs">
                      <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-slate-700">{e.email_type}</p>
                        <p className="text-slate-400">{fmtDate(e.sent_at)} · {e.status === 'sent' ? '✅ enviado' : '❌ falhou'}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </Section>
            )}

          </div>
        )}
      </div>
    </>
  )
}
