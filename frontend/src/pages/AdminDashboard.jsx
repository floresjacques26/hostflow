import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Users, TrendingUp, DollarSign, AlertTriangle, Clock, Zap,
  CheckCircle2, XCircle, ArrowUpRight, BarChart3, RefreshCw,
  Gift, Star, Globe, Inbox, Mail,
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import Layout from '../components/Layout'
import clsx from 'clsx'

// ── Helpers ──────────────────────────────────────────────────────────────────

function brl(cents) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
    .format(cents / 100)
}

function pct(n) {
  return `${n.toFixed(1)}%`
}

// ── Metric card ──────────────────────────────────────────────────────────────

function MetricCard({ icon: Icon, label, value, sub, color = 'brand', highlight = false }) {
  const colors = {
    brand:  { bg: 'bg-brand-50',  icon: 'text-brand-600',  val: 'text-slate-900' },
    green:  { bg: 'bg-green-50',  icon: 'text-green-600',  val: 'text-slate-900' },
    purple: { bg: 'bg-purple-50', icon: 'text-purple-600', val: 'text-slate-900' },
    orange: { bg: 'bg-orange-50', icon: 'text-orange-600', val: 'text-slate-900' },
    red:    { bg: 'bg-red-50',    icon: 'text-red-600',    val: 'text-slate-900' },
    slate:  { bg: 'bg-slate-50',  icon: 'text-slate-500',  val: 'text-slate-900' },
    blue:   { bg: 'bg-blue-50',   icon: 'text-blue-600',   val: 'text-slate-900' },
  }
  const c = colors[color] || colors.brand

  return (
    <div className={clsx('card p-5', highlight && 'ring-2 ring-brand-200')}>
      <div className="flex items-start gap-3">
        <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center shrink-0', c.bg)}>
          <Icon className={clsx('w-4 h-4', c.icon)} />
        </div>
        <div className="min-w-0">
          <p className="text-xs text-slate-500 mb-1">{label}</p>
          <p className={clsx('text-2xl font-bold leading-none', c.val)}>{value}</p>
          {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
        </div>
      </div>
    </div>
  )
}

// ── Cohort table ─────────────────────────────────────────────────────────────

function CohortTable({ cohorts }) {
  if (!cohorts.length) return <p className="text-sm text-slate-400 py-4">Sem dados</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-100">
            {['Mês', 'Cadastros', 'Ativados', '% Ativ.', 'Convertidos', '% Conv.', 'Trial', 'Cancelados'].map(h => (
              <th key={h} className="pb-2 pr-4 text-left text-xs text-slate-500 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {cohorts.map(row => (
            <tr key={row.month} className="border-b border-slate-50 hover:bg-slate-50">
              <td className="py-2 pr-4 font-medium text-slate-700">{row.month}</td>
              <td className="py-2 pr-4 text-slate-600">{row.signups}</td>
              <td className="py-2 pr-4 text-slate-600">{row.activated}</td>
              <td className="py-2 pr-4">
                <span className={clsx(
                  'text-xs font-medium px-1.5 py-0.5 rounded',
                  row.activation_rate >= 50 ? 'bg-green-100 text-green-700' :
                  row.activation_rate >= 20 ? 'bg-yellow-100 text-yellow-700' :
                  'bg-red-100 text-red-700'
                )}>
                  {pct(row.activation_rate)}
                </span>
              </td>
              <td className="py-2 pr-4 text-slate-600">{row.converted}</td>
              <td className="py-2 pr-4">
                <span className={clsx(
                  'text-xs font-medium px-1.5 py-0.5 rounded',
                  row.conversion_rate >= 20 ? 'bg-green-100 text-green-700' :
                  row.conversion_rate >= 5  ? 'bg-yellow-100 text-yellow-700' :
                  'bg-slate-100 text-slate-600'
                )}>
                  {pct(row.conversion_rate)}
                </span>
              </td>
              <td className="py-2 pr-4 text-slate-500">{row.trialing}</td>
              <td className="py-2 text-slate-500">{row.canceled}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── MRR breakdown ─────────────────────────────────────────────────────────────

function MrrBreakdown({ mrrByPlan }) {
  const PLAN_COLORS = { pro: 'bg-brand-500', business: 'bg-purple-500', free: 'bg-slate-300' }
  const total = mrrByPlan.reduce((s, r) => s + r.mrr_cents, 0)

  return (
    <div className="space-y-3">
      {mrrByPlan.map(row => (
        <div key={row.plan} className="flex items-center gap-3">
          <div className={clsx('w-2.5 h-2.5 rounded-full shrink-0', PLAN_COLORS[row.plan] || 'bg-slate-300')} />
          <div className="flex-1">
            <div className="flex justify-between text-sm mb-1">
              <span className="capitalize font-medium text-slate-700">{row.plan}</span>
              <span className="text-slate-500">{row.users} usuários · {brl(row.mrr_cents)}</span>
            </div>
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={clsx('h-full rounded-full', PLAN_COLORS[row.plan] || 'bg-slate-300')}
                style={{ width: total > 0 ? `${(row.mrr_cents / total * 100).toFixed(1)}%` : '0%' }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

// ── Acquisition section ───────────────────────────────────────────────────────

function AcquisitionSection({ acq }) {
  if (!acq) return null
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      {/* By source */}
      <div className="card p-6">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4 flex items-center gap-2">
          <Globe className="w-3.5 h-3.5" /> Usuários por origem
        </h2>
        <div className="space-y-2">
          {acq.by_source.slice(0, 6).map(s => (
            <div key={s.source} className="flex justify-between items-center text-sm">
              <span className="font-medium text-slate-700 capitalize">{s.source}</span>
              <span className="text-xs text-slate-500">
                {s.total} · {s.activation_rate}% ativ. · {s.conversion_rate}% conv.
              </span>
            </div>
          ))}
          {!acq.by_source.length && <p className="text-xs text-slate-400">Sem dados</p>}
        </div>
      </div>

      {/* Referrals */}
      <div className="card p-6">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4 flex items-center gap-2">
          <Gift className="w-3.5 h-3.5" /> Indicações
        </h2>
        <div className="grid grid-cols-3 gap-3 mb-4">
          {[
            { label: 'Total', value: acq.referrals.total, color: 'text-slate-800' },
            { label: 'Recompensadas', value: acq.referrals.rewarded, color: 'text-green-600' },
            { label: 'Pendentes', value: acq.referrals.pending, color: 'text-orange-500' },
          ].map(item => (
            <div key={item.label} className="text-center">
              <p className={`text-xl font-bold ${item.color}`}>{item.value}</p>
              <p className="text-xs text-slate-400">{item.label}</p>
            </div>
          ))}
        </div>
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-slate-500 mb-2">Top indicadores</p>
          {acq.top_referrers.slice(0, 4).map(r => (
            <div key={r.user_id} className="flex justify-between text-xs">
              <span className="text-slate-700 truncate max-w-32">{r.name}</span>
              <span className="text-slate-400">{r.referral_count} indicações · {r.rewarded_count} ✓</span>
            </div>
          ))}
          {!acq.top_referrers.length && <p className="text-xs text-slate-400">Nenhuma indicação ainda</p>}
        </div>
      </div>

      {/* Testimonials */}
      <div className="card p-6">
        <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4 flex items-center gap-2">
          <Star className="w-3.5 h-3.5" /> Avaliações
        </h2>
        <div className="flex items-center gap-3 mb-4">
          <div className="text-3xl font-bold text-slate-800">{acq.testimonials.avg_rating.toFixed(1)}</div>
          <div>
            <div className="flex gap-0.5">
              {[1,2,3,4,5].map(n => (
                <Star key={n} className="w-4 h-4" fill={n <= Math.round(acq.testimonials.avg_rating) ? '#f59e0b' : 'none'} stroke={n <= Math.round(acq.testimonials.avg_rating) ? '#f59e0b' : '#cbd5e1'} />
              ))}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{acq.testimonials.total} avaliações</p>
          </div>
        </div>
        <div className="space-y-1.5">
          <div className="flex justify-between text-sm">
            <span className="text-slate-600">Aprovadas</span>
            <span className="font-medium text-green-600">{acq.testimonials.approved}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-600">Pendentes</span>
            <span className="font-medium text-orange-500">{acq.testimonials.pending}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState(null)
  const [cohorts, setCohorts] = useState([])
  const [mrrByPlan, setMrrByPlan] = useState([])
  const [acq, setAcq] = useState(null)
  const [inboxStats, setInboxStats] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const [mRes, cRes, mbrRes, acqRes, inbRes] = await Promise.all([
        api.get('/admin/dashboard/metrics'),
        api.get('/admin/dashboard/cohorts'),
        api.get('/admin/dashboard/mrr-by-plan'),
        api.get('/admin/acquisition/overview'),
        api.get('/admin/inbox/stats'),
      ])
      setMetrics(mRes.data)
      setCohorts(cRes.data)
      setMrrByPlan(mbrRes.data)
      setAcq(acqRes.data)
      setInboxStats(inbRes.data)
    } catch (err) {
      if (err.response?.status === 403) {
        toast.error('Acesso restrito a administradores')
      } else {
        toast.error('Erro ao carregar métricas')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <Layout>
      <div className="max-w-6xl mx-auto py-20 text-center text-slate-400 text-sm">Carregando...</div>
    </Layout>
  )

  if (!metrics) return (
    <Layout>
      <div className="max-w-6xl mx-auto py-20 text-center text-slate-400 text-sm">
        Acesso negado ou erro ao carregar dados.
      </div>
    </Layout>
  )

  const m = metrics

  return (
    <Layout>
      <div className="max-w-6xl mx-auto">

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Admin Dashboard</h1>
            <p className="text-slate-500 text-sm mt-1">Métricas de receita e crescimento em tempo real.</p>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/admin/users" className="btn-secondary text-sm flex items-center gap-2">
              <Users className="w-4 h-4" /> CRM de Usuários
            </Link>
            <button onClick={load} className="text-slate-400 hover:text-slate-600">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Revenue highlight row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MetricCard icon={DollarSign}    label="MRR (estimado)"     value={brl(m.mrr_cents)}     sub={`ARR: ${brl(m.arr_cents)}`} color="green" highlight />
          <MetricCard icon={TrendingUp}    label="ARPPU"              value={brl(m.arppu_cents)}   sub="por assinante/mês" color="brand" />
          <MetricCard icon={Users}         label="Assinantes ativos"  value={m.paying_users}       sub={`+${m.new_users_30d} novos (30d)`} color="purple" />
          <MetricCard icon={BarChart3}     label="Taxa de conversão"  value={pct(m.trial_conversion_rate_pct)} sub="trial → pago" color="brand" />
        </div>

        {/* User funnel */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <MetricCard icon={Users}         label="Total de usuários"  value={m.total_users}        color="slate" />
          <MetricCard icon={Zap}           label="Ativados"           value={m.activated_users}    sub={pct(m.activation_rate_pct)} color="brand" />
          <MetricCard icon={Clock}         label="Em trial"           value={m.trial_users}        sub={`${m.trials_expiring_7d} expiram em 7d`} color="orange" />
          <MetricCard icon={CheckCircle2}  label="Pagantes"           value={m.paying_users}       sub={`Pro: ${m.pro_users} · Business: ${m.business_users}`} color="green" />
        </div>

        {/* Risk / operations */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <MetricCard icon={AlertTriangle} label="Pagamento pendente" value={m.past_due_users}     color="orange" />
          <MetricCard icon={XCircle}       label="Cancelamentos (30d)" value={m.canceled_last_30d} sub={`Churn: ${pct(m.churn_rate_pct)}`} color="red" />
          <MetricCard icon={ArrowUpRight}  label="Upgrades (30d)"     value={m.upgrades_last_30d} color="green" />
          <MetricCard icon={Users}         label="Plano gratuito"     value={m.free_users}         color="slate" />
        </div>

        {/* Acquisition */}
        <AcquisitionSection acq={acq} />

        {/* Inbox Operations */}
        {inboxStats && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-2">
              <Inbox className="w-3.5 h-3.5" /> Operações de Inbox
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
              <MetricCard icon={Mail}         label="Total de conversas"  value={inboxStats.total_threads}         color="brand" />
              <MetricCard icon={Inbox}        label="Abertas"             value={inboxStats.open}                  color="blue" sub={`Pendentes: ${inboxStats.pending}`} />
              <MetricCard icon={CheckCircle2} label="Resolvidas"          value={inboxStats.resolved}              color="green" sub={`Taxa: ${inboxStats.resolved_rate_pct}%`} />
              <MetricCard icon={Zap}          label="Rascunhos gerados"   value={inboxStats.total_ai_drafts_generated} color="purple" sub={`Respondidas: ${inboxStats.replied}`} />
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="card p-4">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Por canal</p>
                <div className="space-y-1.5">
                  {inboxStats.by_source.map(s => (
                    <div key={s.source} className="flex justify-between text-sm">
                      <span className="text-slate-700 capitalize">{s.source.replace('_', ' ')}</span>
                      <span className="text-slate-500 font-medium">{s.count}</span>
                    </div>
                  ))}
                  {!inboxStats.by_source.length && <p className="text-xs text-slate-400">Sem dados</p>}
                </div>
              </div>
              <div className="card p-4">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Por contexto detectado</p>
                <div className="space-y-1.5">
                  {inboxStats.by_context.slice(0, 6).map(c => (
                    <div key={c.context} className="flex justify-between text-sm">
                      <span className="text-slate-700 capitalize">{c.context.replace('_', ' ')}</span>
                      <span className="text-slate-500 font-medium">{c.count}</span>
                    </div>
                  ))}
                  {!inboxStats.by_context.length && <p className="text-xs text-slate-400">Sem dados</p>}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Bottom row: MRR by plan + cohorts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="card p-6">
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-4">MRR por plano</h2>
            <MrrBreakdown mrrByPlan={mrrByPlan} />
          </div>

          <div className="lg:col-span-2 card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Cohorts por mês de cadastro</h2>
              <span className="text-xs text-slate-400">últimos 12 meses</span>
            </div>
            <CohortTable cohorts={cohorts} />
          </div>
        </div>

      </div>
    </Layout>
  )
}
