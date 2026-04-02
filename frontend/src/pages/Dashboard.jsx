import { useState, useEffect, useRef } from 'react'
import { Send, Trash2, Copy, Clock, ChevronDown, ChevronUp, Building2, Zap, Timer, MessageSquare } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import Layout from '../components/Layout'
import PropertySelect from '../components/PropertySelect'
import UpgradeModal from '../components/UpgradeModal'
import UsageBar from '../components/UsageBar'
import InAppMessages from '../components/InAppMessages'
import ReferralCard from '../components/ReferralCard'
import TestimonialModal from '../components/TestimonialModal'
import useBilling from '../hooks/useBilling'
import useOnboarding from '../hooks/useOnboarding'
import clsx from 'clsx'

const CONTEXT_LABELS = {
  checkin:   { label: 'Check-in',   color: 'bg-blue-100 text-blue-700' },
  checkout:  { label: 'Check-out',  color: 'bg-purple-100 text-purple-700' },
  complaint: { label: 'Reclamação', color: 'bg-red-100 text-red-700' },
  question:  { label: 'Dúvida',     color: 'bg-yellow-100 text-yellow-700' },
  charge:    { label: 'Cobrança',   color: 'bg-orange-100 text-orange-700' },
  other:     { label: 'Outro',      color: 'bg-slate-100 text-slate-600' },
}

function StatCard({ icon: Icon, value, label, color = 'brand' }) {
  const colorMap = {
    brand:  { bg: 'bg-brand-50',  text: 'text-brand-600' },
    green:  { bg: 'bg-green-50',  text: 'text-green-600' },
    purple: { bg: 'bg-purple-50', text: 'text-purple-600' },
  }
  const c = colorMap[color] || colorMap.brand
  return (
    <div className="card p-4 flex items-center gap-3">
      <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center shrink-0', c.bg)}>
        <Icon className={clsx('w-4 h-4', c.text)} />
      </div>
      <div>
        <p className="text-lg font-bold text-slate-800 leading-none">{value}</p>
        <p className="text-xs text-slate-500 mt-0.5">{label}</p>
      </div>
    </div>
  )
}

function ProNudge({ responses }) {
  if (responses < 3) return null
  return (
    <div className="flex items-start gap-3 p-3 bg-brand-50 border border-brand-100 rounded-lg text-sm">
      <Zap className="w-4 h-4 text-brand-500 shrink-0 mt-0.5" />
      <p className="text-brand-700">
        Você já gerou {responses} respostas. Imagine isso{' '}
        <strong>ilimitado no plano Pro</strong> — mais imóveis, mais histórico, sem interrupções.
      </p>
    </div>
  )
}

function HistoryItem({ item, onDelete }) {
  const [expanded, setExpanded] = useState(false)
  const ctx = CONTEXT_LABELS[item.context] || CONTEXT_LABELS.other

  const copyResponse = () => {
    navigator.clipboard.writeText(item.ai_response)
    toast.success('Resposta copiada!')
  }

  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1.5">
            <span className={clsx('text-xs px-2 py-0.5 rounded-full font-medium', ctx.color)}>
              {ctx.label}
            </span>
            {item.property && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 flex items-center gap-1">
                <Building2 className="w-3 h-3" />
                {item.property.name}
              </span>
            )}
            <span className="text-xs text-slate-400">
              {new Date(item.created_at).toLocaleString('pt-BR')}
            </span>
          </div>
          <p className="text-sm text-slate-600 line-clamp-2">{item.guest_message}</p>
        </div>
        <button onClick={() => setExpanded(!expanded)} className="text-slate-400 hover:text-slate-600 mt-1 shrink-0">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-slate-100">
          <div className="bg-slate-50 rounded-lg p-3 mb-2">
            <p className="text-xs font-medium text-slate-500 mb-1">Mensagem do hóspede</p>
            <p className="text-sm text-slate-700 whitespace-pre-wrap">{item.guest_message}</p>
          </div>
          <div className="bg-brand-50 rounded-lg p-3">
            <p className="text-xs font-medium text-brand-600 mb-1">Resposta sugerida</p>
            <p className="text-sm text-slate-700 whitespace-pre-wrap">{item.ai_response}</p>
          </div>
          <div className="flex gap-2 mt-2">
            <button onClick={copyResponse} className="btn-secondary text-xs flex items-center gap-1.5 py-1.5">
              <Copy className="w-3.5 h-3.5" /> Copiar resposta
            </button>
            <button
              onClick={() => onDelete(item.id)}
              className="text-xs flex items-center gap-1.5 py-1.5 px-3 rounded-lg text-red-500 hover:bg-red-50 transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" /> Excluir
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const [message, setMessage] = useState('')
  const [propertyId, setPropertyId] = useState(null)
  const [dailyRate, setDailyRate] = useState('')
  const [response, setResponse] = useState(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [filterPropertyId, setFilterPropertyId] = useState(null)
  const [upgradeError, setUpgradeError] = useState(null)
  const [stats, setStats] = useState(null)
  const [testimonialTrigger, setTestimonialTrigger] = useState(null)
  const [shownTestimonial, setShownTestimonial] = useState(
    () => new Set(JSON.parse(localStorage.getItem('hf_testimonial_shown') || '[]'))
  )
  const { usage, refreshUsage } = useBilling()
  const { state: onboardingState, markStep } = useOnboarding()
  const responseRef = useRef(null)

  useEffect(() => {
    fetchHistory()
    fetchStats()
  }, [filterPropertyId])

  const fetchHistory = async () => {
    setLoadingHistory(true)
    try {
      const params = filterPropertyId ? `?property_id=${filterPropertyId}` : ''
      const { data } = await api.get(`/messages/history${params}`)
      setHistory(data)
    } catch {
      toast.error('Erro ao carregar histórico')
    } finally {
      setLoadingHistory(false)
    }
  }

  const fetchStats = async () => {
    try {
      const { data } = await api.get('/analytics/dashboard-stats')
      setStats(data)
    } catch {
      // Non-critical — fail silently
    }
  }

  const handleGenerate = async (e) => {
    e.preventDefault()
    if (!message.trim()) return
    setLoading(true)
    setResponse(null)
    try {
      const payload = { guest_message: message }
      if (propertyId) payload.property_id = propertyId
      else if (dailyRate) payload.daily_rate = parseFloat(dailyRate)

      const { data } = await api.post('/messages/generate', payload)
      setResponse(data)
      setHistory((prev) => [
        {
          id: data.conversation_id,
          guest_message: message,
          ai_response: data.ai_response,
          context: data.context,
          property: null,
          property_id: propertyId,
          created_at: new Date().toISOString(),
        },
        ...prev,
      ])
      markStep('ai_response')
      // Refresh stats after generation
      fetchStats()
      refreshUsage()
      // Prompt for testimonial after 10th AI response
      const newStats = data  // stats will refresh async; check after fetch
      setTimeout(async () => {
        try {
          const { data: s } = await api.get('/analytics/dashboard-stats')
          if (s.ai_responses_total >= 10 && !shownTestimonial.has('responses_10')) {
            setShownTestimonial(prev => { const n = new Set(prev); n.add('responses_10'); localStorage.setItem('hf_testimonial_shown', JSON.stringify([...n])); return n })
            setTestimonialTrigger('responses_10')
          }
        } catch {}
      }, 1500)
      setTimeout(() => responseRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    } catch (err) {
      if (err.response?.status === 402) {
        setUpgradeError(err.response.data.detail)
      } else {
        toast.error(err.response?.data?.detail || 'Erro ao gerar resposta')
      }
    } finally {
      setLoading(false)
    }
  }

  const copyResponse = () => {
    if (!response) return
    navigator.clipboard.writeText(response.ai_response)
    toast.success('Resposta copiada!')
  }

  const handleDelete = async (id) => {
    try {
      await api.delete(`/messages/${id}`)
      setHistory((prev) => prev.filter((h) => h.id !== id))
      toast.success('Conversa excluída')
    } catch {
      toast.error('Erro ao excluir')
    }
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto">
        <div className="mb-5">
          <h1 className="text-2xl font-bold text-slate-800">Dashboard</h1>
          <p className="text-slate-500 text-sm mt-1">
            Cole a mensagem do hóspede e gere uma resposta profissional em segundos.
          </p>
        </div>

        <InAppMessages />

        {/* First-value moment: nudge brand-new users to set up a property */}
        {onboardingState && onboardingState.current_step === 0 && !onboardingState.completed && (
          <div className="card p-5 mb-5 border-brand-100 bg-gradient-to-r from-brand-50 to-white">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-brand-100 rounded-xl flex items-center justify-center shrink-0">
                <Zap className="w-5 h-5 text-brand-600" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-slate-800 mb-1">Bem-vindo ao HostFlow!</p>
                <p className="text-sm text-slate-500 mb-3">
                  Cadastre seu primeiro imóvel e cole uma mensagem de hóspede abaixo — a IA responde em segundos.
                </p>
                <a href="/properties" className="btn-primary text-sm inline-flex items-center gap-2">
                  <Building2 className="w-4 h-4" />
                  Cadastrar meu imóvel
                </a>
              </div>
            </div>
          </div>
        )}

        {/* Value stats */}
        {stats && (
          <div className="grid grid-cols-3 gap-3 mb-5">
            <StatCard
              icon={MessageSquare}
              value={stats.ai_responses_month}
              label="Respostas este mês"
              color="brand"
            />
            <StatCard
              icon={Timer}
              value={`${stats.minutes_saved_month} min`}
              label="Economizados este mês"
              color="green"
            />
            <StatCard
              icon={Zap}
              value={stats.ai_responses_total}
              label="Total automatizados"
              color="purple"
            />
          </div>
        )}

        {/* Usage bar only when near/at limit */}
        {usage && usage.ai_responses_limit !== null && (
          usage.ai_responses / usage.ai_responses_limit >= 0.6
        ) && (
          <div className="card p-4 mb-5">
            <UsageBar
              label="Respostas este mês"
              used={usage.ai_responses}
              limit={usage.ai_responses_limit}
            />
          </div>
        )}

        {/* Pro nudge */}
        {stats && usage?.ai_responses_limit !== null && (
          <div className="mb-5">
            <ProNudge responses={stats.ai_responses_total} />
          </div>
        )}

        {/* Referral card */}
        <div className="mb-5">
          <ReferralCard />
        </div>

        {/* Generator */}
        <div className="card p-6 mb-6">
          <form onSubmit={handleGenerate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Mensagem do hóspede
              </label>
              <textarea
                className="input resize-none"
                rows={5}
                placeholder="Cole aqui a mensagem recebida no Airbnb..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3 items-end">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Imóvel <span className="text-slate-400 font-normal">opcional</span>
                </label>
                <PropertySelect
                  value={propertyId}
                  onChange={(id) => { setPropertyId(id); if (id) setDailyRate('') }}
                  placeholder="Sem imóvel (regras padrão)"
                />
              </div>

              {!propertyId && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Valor da diária (R$) <span className="text-slate-400 font-normal">opcional</span>
                  </label>
                  <input
                    className="input"
                    type="number"
                    placeholder="Ex: 250"
                    min="0"
                    step="0.01"
                    value={dailyRate}
                    onChange={(e) => setDailyRate(e.target.value)}
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                className="btn-primary flex items-center gap-2"
                disabled={loading || !message.trim()}
              >
                <Send className="w-4 h-4" />
                {loading ? 'Gerando...' : 'Gerar resposta'}
              </button>
            </div>
          </form>

          {response && (
            <div ref={responseRef} className="mt-5 pt-5 border-t border-slate-100">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-slate-800">Resposta sugerida</span>
                  {response.context && (
                    <span className={clsx('text-xs px-2 py-0.5 rounded-full font-medium', CONTEXT_LABELS[response.context]?.color)}>
                      {CONTEXT_LABELS[response.context]?.label}
                    </span>
                  )}
                </div>
                <button onClick={copyResponse} className="btn-secondary text-xs flex items-center gap-1.5 py-1.5">
                  <Copy className="w-3.5 h-3.5" /> Copiar
                </button>
              </div>
              <div className="bg-brand-50 border border-brand-100 rounded-lg p-4">
                <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">{response.ai_response}</p>
              </div>
              <p className="text-xs text-slate-400 mt-2 text-right">
                ~2 minutos economizados nesta resposta
              </p>
            </div>
          )}
        </div>

        {/* History */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-400" />
              <h2 className="font-semibold text-slate-700">Histórico</h2>
              <span className="text-xs text-slate-400">({history.length})</span>
            </div>
            <div className="w-48">
              <PropertySelect
                value={filterPropertyId}
                onChange={setFilterPropertyId}
                placeholder="Todos os imóveis"
              />
            </div>
          </div>

          {loadingHistory ? (
            <div className="text-center py-8 text-slate-400 text-sm">Carregando...</div>
          ) : history.length === 0 ? (
            <div className="text-center py-10 card">
              <p className="text-slate-400 text-sm">
                {filterPropertyId ? 'Nenhuma conversa para este imóvel.' : 'Nenhuma conversa ainda. Gere sua primeira resposta acima!'}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {history.map((item) => (
                <HistoryItem key={item.id} item={item} onDelete={handleDelete} />
              ))}
            </div>
          )}
        </div>
      </div>

      <UpgradeModal
        error={upgradeError}
        onClose={() => { setUpgradeError(null); refreshUsage() }}
      />

      {testimonialTrigger && (
        <TestimonialModal
          triggerEvent={testimonialTrigger}
          onClose={() => setTestimonialTrigger(null)}
        />
      )}
    </Layout>
  )
}
