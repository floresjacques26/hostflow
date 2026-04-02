import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Inbox as InboxIcon, Plus, Send, Clipboard, CheckCircle2, Archive,
  Clock, RefreshCw, X, Mail, MessageSquare, Smartphone, Webhook,
  StickyNote, Bot, User, Building2, Search, AlertTriangle,
  AlertCircle, CheckSquare, Square, ChevronDown, Wifi, WifiOff,
  ExternalLink, Zap, FileText, ChevronRight,
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import Layout from '../components/Layout'
import clsx from 'clsx'

// ── Constants ────────────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  open:     { label: 'Aberta',    color: 'bg-blue-100 text-blue-700',   dot: 'bg-blue-500' },
  pending:  { label: 'Pendente',  color: 'bg-amber-100 text-amber-700', dot: 'bg-amber-500' },
  resolved: { label: 'Resolvida', color: 'bg-green-100 text-green-700', dot: 'bg-green-500' },
  archived: { label: 'Arquivada', color: 'bg-slate-100 text-slate-500', dot: 'bg-slate-400' },
}

const CONTEXT_LABELS = {
  early_checkin: 'Check-in antecipado',
  late_checkout:  'Check-out tardio',
  address:        'Endereço',
  parking:        'Estacionamento',
  pets:           'Animais',
  house_rules:    'Regras da casa',
  pricing:        'Preços',
  availability:   'Disponibilidade',
  cancellation:   'Cancelamento',
  amenities:      'Comodidades',
  complaint:      'Reclamação',
  checkin:        'Check-in',
  checkout:       'Check-out',
  question:       'Dúvida',
  charge:         'Cobrança',
  general:        'Geral',
  other:          'Outro',
}

const SOURCE_ICONS = {
  manual:        MessageSquare,
  email_forward: Mail,
  gmail:         Mail,
  whatsapp:      Smartphone,
  webhook:       Webhook,
}

const BULK_ACTIONS = [
  { action: 'resolve',  label: 'Resolver',  color: 'text-green-700 hover:bg-green-50' },
  { action: 'pending',  label: 'Pendente',  color: 'text-amber-700 hover:bg-amber-50' },
  { action: 'open',     label: 'Reabrir',   color: 'text-blue-700 hover:bg-blue-50' },
  { action: 'archive',  label: 'Arquivar',  color: 'text-slate-600 hover:bg-slate-100' },
]

// ── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(dateStr) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'agora'
  if (m < 60) return `${m}min`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h`
  const d = Math.floor(h / 24)
  if (d < 7) return `${d}d`
  return new Date(dateStr).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
}

function useDebounce(value, delay) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

function StatusBadge({ status, size = 'sm' }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.open
  return (
    <span className={clsx(
      'inline-flex items-center gap-1 rounded-full font-medium',
      size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-2.5 py-1',
      cfg.color,
    )}>
      <span className={clsx('w-1.5 h-1.5 rounded-full', cfg.dot)} />
      {cfg.label}
    </span>
  )
}

function ContextBadge({ context }) {
  if (!context) return null
  return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
      {CONTEXT_LABELS[context] || context}
    </span>
  )
}

function ChannelIcon({ sourceType }) {
  const Icon = SOURCE_ICONS[sourceType] || MessageSquare
  return <Icon className="w-3 h-3 text-slate-400" />
}

function GmailBadge({ syncStatus }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-red-50 text-red-600 font-medium border border-red-100">
      <Mail className="w-3 h-3" />
      Gmail
      {syncStatus === 'error' && <AlertTriangle className="w-3 h-3 text-red-500" />}
    </span>
  )
}

function WhatsAppBadge({ syncStatus }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-green-50 text-green-700 font-medium border border-green-100">
      <Smartphone className="w-3 h-3" />
      WhatsApp
      {syncStatus === 'error' && <AlertTriangle className="w-3 h-3 text-orange-500" />}
    </span>
  )
}

function AutoSendBadge({ decision }) {
  if (!decision) return null
  const cfg = {
    sent:          { label: 'Auto-enviado', cls: 'bg-green-100 text-green-700', icon: CheckCircle2 },
    blocked:       { label: 'Guardrail', cls: 'bg-red-100 text-red-600', icon: AlertTriangle },
    manual_review: { label: 'Revisão', cls: 'bg-yellow-100 text-yellow-700', icon: AlertCircle },
  }[decision]
  if (!cfg) return null
  const Icon = cfg.icon
  return (
    <span className={clsx('inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded font-medium', cfg.cls)}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  )
}

function DeliveryBadge({ status }) {
  if (!status) return null
  const cfg = {
    sent:    { label: 'Enviado', cls: 'text-green-600' },
    failed:  { label: 'Falhou', cls: 'text-red-600' },
    pending: { label: 'Enviando...', cls: 'text-slate-400' },
  }[status] || { label: status, cls: 'text-slate-400' }
  return <span className={clsx('text-xs font-medium', cfg.cls)}>{cfg.label}</span>
}

// ── Thread Card ───────────────────────────────────────────────────────────────

function ThreadCard({ thread, selected, onClick, bulkMode, checked, onCheck }) {
  const hasDraft = thread.draft_status === 'draft_generated'
  const lastMsg = thread.last_message_at || thread.created_at

  return (
    <div
      className={clsx(
        'flex items-start w-full border-b border-slate-100 transition-colors',
        selected ? 'bg-brand-50 border-l-2 border-l-brand-500' : 'hover:bg-slate-50 border-l-2 border-l-transparent',
        thread.is_overdue && !selected && 'border-l-red-400',
        thread.is_stale && !selected && !thread.is_overdue && 'border-l-amber-400',
      )}
    >
      {/* Checkbox in bulk mode */}
      {bulkMode && (
        <button
          onClick={e => { e.stopPropagation(); onCheck(thread.id) }}
          className="pl-3 pt-4 shrink-0 text-slate-400 hover:text-brand-600"
        >
          {checked ? (
            <CheckSquare className="w-4 h-4 text-brand-600" />
          ) : (
            <Square className="w-4 h-4" />
          )}
        </button>
      )}

      <button
        onClick={onClick}
        className="flex-1 text-left px-4 py-3.5"
      >
        <div className="flex items-start justify-between gap-2 mb-1">
          <div className="flex items-center gap-1.5 min-w-0">
            <ChannelIcon sourceType={thread.source_type} />
            <span className="text-sm font-semibold text-slate-800 truncate">
              {thread.guest_name || 'Hóspede desconhecido'}
            </span>
            {/* SLA badges */}
            {thread.is_overdue && (
              <AlertTriangle className="w-3.5 h-3.5 text-red-500 shrink-0" title="Atrasada (>4h)" />
            )}
            {thread.is_stale && !thread.is_overdue && (
              <AlertCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" title="Parada (>24h)" />
            )}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {hasDraft && (
              <span className="text-xs px-1.5 py-0.5 bg-brand-100 text-brand-700 rounded font-medium">
                Rascunho
              </span>
            )}
            <span className="text-xs text-slate-400">{timeAgo(lastMsg)}</span>
          </div>
        </div>

        <p className="text-xs text-slate-500 truncate mb-1.5">
          {thread.subject || 'Sem assunto'}
        </p>

        <div className="flex items-center gap-1.5 flex-wrap">
          <StatusBadge status={thread.status} />
          {thread.source_type === 'gmail' && (
            <GmailBadge syncStatus={thread.sync_status} />
          )}
          {thread.source_type === 'whatsapp' && (
            <WhatsAppBadge syncStatus={thread.sync_status} />
          )}
          {thread.auto_send_decision && (
            <AutoSendBadge decision={thread.auto_send_decision} />
          )}
          {thread.detected_context && <ContextBadge context={thread.detected_context} />}
          {thread.property && (
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <Building2 className="w-3 h-3" />
              {thread.property.name}
            </span>
          )}
        </div>
      </button>
    </div>
  )
}

// ── Guest Profile Panel ───────────────────────────────────────────────────────

function GuestPanel({ profileId, onClose }) {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!profileId) return
    setLoading(true)
    api.get(`/guests/${profileId}`)
      .then(({ data }) => setProfile(data))
      .catch(() => toast.error('Erro ao carregar hóspede'))
      .finally(() => setLoading(false))
  }, [profileId])

  if (loading) {
    return (
      <div className="w-72 shrink-0 border-l border-slate-200 bg-white flex items-center justify-center text-slate-400 text-sm">
        Carregando...
      </div>
    )
  }

  if (!profile) return null

  return (
    <aside className="w-72 shrink-0 border-l border-slate-200 bg-white flex flex-col overflow-y-auto">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1.5">
          <User className="w-3.5 h-3.5" /> Perfil do Hóspede
        </span>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* Identity */}
        <div>
          <p className="text-base font-semibold text-slate-800">{profile.name || 'Sem nome'}</p>
          {profile.primary_email && (
            <p className="text-xs text-slate-500 mt-0.5">{profile.primary_email}</p>
          )}
          {profile.primary_phone && (
            <p className="text-xs text-slate-500">{profile.primary_phone}</p>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-slate-50 rounded-lg px-3 py-2 text-center">
            <p className="text-lg font-bold text-slate-800">{profile.thread_count}</p>
            <p className="text-xs text-slate-500">Conversas</p>
          </div>
          {profile.last_contact_at && (
            <div className="bg-slate-50 rounded-lg px-3 py-2 text-center">
              <p className="text-sm font-semibold text-slate-800">{timeAgo(profile.last_contact_at)}</p>
              <p className="text-xs text-slate-500">Último contato</p>
            </div>
          )}
        </div>

        {/* Common contexts */}
        {profile.common_contexts?.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Assuntos frequentes
            </p>
            <div className="flex flex-wrap gap-1">
              {profile.common_contexts.map(ctx => (
                <ContextBadge key={ctx} context={ctx} />
              ))}
            </div>
          </div>
        )}

        {/* Properties */}
        {profile.properties?.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Imóveis
            </p>
            <div className="space-y-1">
              {profile.properties.map(p => (
                <p key={p.id} className="text-xs text-slate-600 flex items-center gap-1.5">
                  <Building2 className="w-3 h-3 text-slate-400" /> {p.name}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Recent threads */}
        {profile.recent_threads?.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Conversas recentes
            </p>
            <div className="space-y-2">
              {profile.recent_threads.map(t => (
                <div key={t.id} className="text-xs bg-slate-50 rounded-lg px-3 py-2">
                  <p className="font-medium text-slate-700 truncate">{t.subject || 'Sem assunto'}</p>
                  <div className="flex items-center gap-1.5 mt-1">
                    <StatusBadge status={t.status} />
                    {t.detected_context && <ContextBadge context={t.detected_context} />}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Notes */}
        {profile.notes && (
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              Notas
            </p>
            <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-wrap">{profile.notes}</p>
          </div>
        )}
      </div>
    </aside>
  )
}

// ── Message Entry in timeline ─────────────────────────────────────────────────

function EntryBubble({ entry }) {
  const isInbound  = entry.direction === 'inbound'
  const isOutbound = entry.direction === 'outbound'
  const isDraft    = entry.direction === 'ai_draft'
  const isNote     = entry.direction === 'note'

  const copyText = () => {
    navigator.clipboard.writeText(entry.body)
    toast.success('Copiado!')
  }

  return (
    <div className={clsx('flex gap-2 mb-4', isOutbound ? 'flex-row-reverse' : 'flex-row')}>
      <div className={clsx(
        'w-7 h-7 rounded-full flex items-center justify-center shrink-0 text-xs font-bold mt-0.5',
        isInbound  ? 'bg-slate-200 text-slate-600' :
        isOutbound ? 'bg-brand-600 text-white' :
        isDraft    ? 'bg-blue-100 text-blue-700' :
                     'bg-amber-100 text-amber-700',
      )}>
        {isDraft ? <Bot className="w-3.5 h-3.5" /> :
         isNote  ? <StickyNote className="w-3.5 h-3.5" /> :
                   <User className="w-3.5 h-3.5" />}
      </div>

      <div className={clsx('max-w-[75%]', isNote && 'w-full max-w-full')}>
        <div className={clsx(
          'px-3.5 py-2.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap',
          isInbound  ? 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm' :
          isOutbound ? 'bg-brand-600 text-white rounded-tr-sm' :
          isDraft    ? 'bg-blue-50 border border-blue-200 text-slate-800 rounded-tl-sm' :
                       'bg-amber-50 border border-amber-200 text-slate-700 w-full rounded-lg',
        )}>
          {isDraft && (
            <div className="flex items-center gap-1 mb-1.5 text-xs text-blue-600 font-medium">
              <Bot className="w-3 h-3" /> Rascunho IA
            </div>
          )}
          {isNote && (
            <div className="flex items-center gap-1 mb-1 text-xs text-amber-600 font-medium">
              <StickyNote className="w-3 h-3" /> Nota interna
            </div>
          )}
          {entry.body}
        </div>

        <div className={clsx('flex items-center gap-2 mt-1', isOutbound ? 'flex-row-reverse' : 'flex-row')}>
          <span className="text-xs text-slate-400">
            {entry.sender_name && <span className="font-medium">{entry.sender_name} · </span>}
            {timeAgo(entry.created_at)}
          </span>
          {entry.sent_via_provider && (
            <DeliveryBadge status={entry.delivery_status} />
          )}
          {(isDraft || isInbound) && (
            <button
              onClick={copyText}
              className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-0.5"
            >
              <Clipboard className="w-3 h-3" /> copiar
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Template picker overlay ───────────────────────────────────────────────────

function TemplatePicker({ threadId, currentTemplateId, onSelect, onClose }) {
  const [suggestions, setSuggestions] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get(`/templates/suggest?thread_id=${threadId}`)
      .then(({ data }) => setSuggestions(data.suggestions || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [threadId])

  const filtered = suggestions.filter(s =>
    !search || s.template.title.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="absolute bottom-full left-0 right-0 mb-1 z-20 bg-white border border-slate-200 rounded-xl shadow-xl overflow-hidden">
      {/* Search */}
      <div className="p-2 border-b border-slate-100">
        <div className="flex items-center gap-2 px-2 py-1.5 bg-slate-50 rounded-lg">
          <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <input
            autoFocus
            type="text"
            placeholder="Buscar template..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 text-xs bg-transparent outline-none text-slate-700 placeholder:text-slate-400"
          />
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* List */}
      <div className="max-h-56 overflow-y-auto">
        {/* "No template" option */}
        <button
          onClick={() => onSelect(null, true)}
          className={clsx(
            'w-full text-left px-3 py-2.5 flex items-center gap-2 hover:bg-slate-50 transition-colors border-b border-slate-100',
            currentTemplateId === null && 'bg-slate-50',
          )}
        >
          <X className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="text-xs text-slate-500 font-medium">Sem template (IA livre)</span>
        </button>

        {loading ? (
          <p className="text-xs text-slate-400 px-3 py-4 text-center">Carregando...</p>
        ) : filtered.length === 0 ? (
          <p className="text-xs text-slate-400 px-3 py-4 text-center">Nenhum template encontrado</p>
        ) : (
          filtered.map(({ template: t, match_label, is_context_specific, auto_applied }) => (
            <button
              key={t.id}
              onClick={() => onSelect(t.id, false)}
              className={clsx(
                'w-full text-left px-3 py-2.5 hover:bg-brand-50 transition-colors border-b border-slate-50 last:border-0',
                currentTemplateId === t.id && 'bg-brand-50',
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs font-medium text-slate-800 truncate">{t.title}</span>
                    {is_context_specific && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-violet-100 text-violet-700 font-medium shrink-0">
                        {t.context_key ? CONTEXT_LABELS[t.context_key] || t.context_key : ''}
                      </span>
                    )}
                    {t.auto_apply && (
                      <Zap className="w-3 h-3 text-brand-500 shrink-0" title="Auto-apply" />
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5 truncate">{match_label}</p>
                </div>
                {currentTemplateId === t.id && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-brand-500 shrink-0 mt-0.5" />
                )}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}

// ── Draft Panel ───────────────────────────────────────────────────────────────

function DraftPanel({ thread, onRefresh, liveDraft, onClearLiveDraft }) {
  const [draftText, setDraftText] = useState('')
  const [generating, setGenerating] = useState(false)
  const [sending, setSending] = useState(false)
  const [showPicker, setShowPicker] = useState(false)

  // Template selection state
  // selectedTemplateId: null = let backend decide (auto-match), number = forced choice
  // skipTemplate: true = generate without any template
  const [selectedTemplateId, setSelectedTemplateId] = useState(null)
  const [skipTemplate, setSkipTemplate] = useState(false)
  const [appliedTemplate, setAppliedTemplate] = useState(null) // {id, title, auto_applied}

  const isGmail = thread.source_type === 'gmail'
  const isWhatsApp = thread.source_type === 'whatsapp'

  // Sync draft text from existing ai_draft entries
  useEffect(() => {
    const drafts = (thread.entries || []).filter(e => e.direction === 'ai_draft')
    if (drafts.length) {
      const latest = drafts.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0]
      setDraftText(latest.body)
    } else {
      setDraftText('')
    }
    // Reset template state when thread changes
    setSelectedTemplateId(null)
    setSkipTemplate(false)
    setAppliedTemplate(null)
  }, [thread.id])

  // Sync applied template info from thread (after load / refresh)
  useEffect(() => {
    if (thread.applied_template_id) {
      // Fetch template title for display
      api.get(`/templates/suggest?thread_id=${thread.id}`)
        .then(({ data }) => {
          const match = data.suggestions?.find(s => s.template.id === thread.applied_template_id)
          if (match) {
            setAppliedTemplate({
              id: match.template.id,
              title: match.template.title,
              auto_applied: thread.template_auto_applied,
              match_label: match.match_label,
            })
          }
        })
        .catch(() => {})
    } else {
      setAppliedTemplate(null)
    }
  }, [thread.id, thread.applied_template_id, thread.template_auto_applied])

  // Override with live SSE draft when it arrives
  useEffect(() => {
    if (liveDraft) {
      setDraftText(liveDraft)
      onClearLiveDraft()
    }
  }, [liveDraft, onClearLiveDraft])

  const handleGenerate = async (overrideTemplateId, overrideSkip) => {
    setGenerating(true)
    setShowPicker(false)
    const tid = overrideTemplateId !== undefined ? overrideTemplateId : selectedTemplateId
    const skip = overrideSkip !== undefined ? overrideSkip : skipTemplate
    try {
      const payload = {}
      if (tid !== null) payload.template_id = tid
      if (skip) payload.skip_template = true

      const { data } = await api.post(`/inbox/${thread.id}/draft`, payload)
      setDraftText(data.draft)

      if (data.applied_template_id) {
        setAppliedTemplate({
          id: data.applied_template_id,
          auto_applied: data.template_auto_applied,
          title: null, // will be filled on next suggest fetch
        })
      } else {
        setAppliedTemplate(null)
      }

      const msg = data.applied_template_id
        ? data.template_auto_applied ? 'Rascunho gerado com template automático!' : 'Rascunho gerado com template!'
        : 'Rascunho gerado!'
      toast.success(msg)
      onRefresh()
    } catch {
      toast.error('Erro ao gerar rascunho')
    } finally {
      setGenerating(false)
    }
  }

  const handlePickTemplate = (templateId, skip) => {
    setSelectedTemplateId(templateId)
    setSkipTemplate(skip)
    setShowPicker(false)
    // Auto-regenerate with the chosen template
    handleGenerate(templateId, skip)
  }

  const handleMarkSent = async () => {
    if (!draftText.trim()) return
    setSending(true)
    try {
      await api.post(`/inbox/${thread.id}/entries`, { direction: 'outbound', body: draftText })
      toast.success('Resposta registrada como enviada')
      onRefresh()
    } catch {
      toast.error('Erro ao registrar resposta')
    } finally {
      setSending(false)
    }
  }

  const handleSendGmail = async () => {
    if (!draftText.trim()) return
    setSending(true)
    try {
      await api.post(`/inbox/${thread.id}/send`, { direction: 'outbound', body: draftText })
      setDraftText('')
      toast.success('Enviado via Gmail!')
      onRefresh()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao enviar pelo Gmail')
    } finally {
      setSending(false)
    }
  }

  const handleSendWhatsApp = async () => {
    if (!draftText.trim()) return
    setSending(true)
    try {
      await api.post(`/whatsapp/inbox/${thread.id}/send`, { body: draftText })
      setDraftText('')
      toast.success('Enviado via WhatsApp!')
      onRefresh()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao enviar pelo WhatsApp')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="border-t border-slate-200 bg-white p-4 shrink-0">
      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1.5">
          <Bot className="w-3.5 h-3.5 text-blue-500" /> Rascunho IA
        </span>
        <button
          onClick={() => handleGenerate()}
          disabled={generating}
          className="text-xs flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={clsx('w-3 h-3', generating && 'animate-spin')} />
          {generating ? 'Gerando...' : draftText ? 'Regerar' : 'Gerar rascunho'}
        </button>
      </div>

      {/* Applied template indicator */}
      {appliedTemplate && (
        <div className="flex items-center gap-2 mb-2 px-2.5 py-1.5 bg-violet-50 border border-violet-100 rounded-lg">
          <FileText className="w-3.5 h-3.5 text-violet-500 shrink-0" />
          <span className="text-xs text-violet-700 font-medium flex-1 truncate">
            {appliedTemplate.title || 'Template aplicado'}
          </span>
          {appliedTemplate.auto_applied && (
            <span className="text-xs px-1.5 py-0.5 rounded bg-violet-200 text-violet-700 font-medium shrink-0 flex items-center gap-1">
              <Zap className="w-3 h-3" /> Auto
            </span>
          )}
          <button
            onClick={() => handleGenerate(null, true)}
            disabled={generating}
            className="text-violet-400 hover:text-violet-700 shrink-0 disabled:opacity-40"
            title="Remover template e regerar"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Textarea */}
      <textarea
        className="w-full border border-slate-200 rounded-lg p-3 text-sm text-slate-800 resize-none focus:outline-none focus:ring-2 focus:ring-brand-200 bg-blue-50/30 leading-relaxed"
        rows={5}
        placeholder="Clique em 'Gerar rascunho' para criar uma resposta com IA, ou escreva manualmente aqui..."
        value={draftText}
        onChange={e => setDraftText(e.target.value)}
      />

      {/* Action row */}
      <div className="flex items-center gap-2 mt-2 flex-wrap">
        {/* Copy */}
        <button
          onClick={() => { navigator.clipboard.writeText(draftText); toast.success('Copiado!') }}
          disabled={!draftText}
          className="btn-secondary text-xs flex items-center gap-1.5 py-1.5 disabled:opacity-40"
        >
          <Clipboard className="w-3.5 h-3.5" /> Copiar
        </button>

        {/* Template picker trigger */}
        <div className="relative">
          <button
            onClick={() => setShowPicker(v => !v)}
            className={clsx(
              'text-xs flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border transition-colors',
              showPicker
                ? 'bg-violet-50 text-violet-700 border-violet-200'
                : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50',
            )}
          >
            <FileText className="w-3.5 h-3.5" />
            Template
            <ChevronDown className={clsx('w-3 h-3 transition-transform', showPicker && 'rotate-180')} />
          </button>

          {showPicker && (
            <TemplatePicker
              threadId={thread.id}
              currentTemplateId={selectedTemplateId}
              onSelect={handlePickTemplate}
              onClose={() => setShowPicker(false)}
            />
          )}
        </div>

        {/* Send button — Gmail / WhatsApp / regular */}
        <div className="ml-auto">
          {isGmail ? (
            <button
              onClick={handleSendGmail}
              disabled={!draftText || sending}
              className="text-xs flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600 text-white font-medium hover:bg-red-700 transition-colors disabled:opacity-40"
            >
              <Mail className="w-3.5 h-3.5" />
              {sending ? 'Enviando...' : 'Enviar via Gmail'}
            </button>
          ) : isWhatsApp ? (
            <button
              onClick={handleSendWhatsApp}
              disabled={!draftText || sending}
              className="text-xs flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 transition-colors disabled:opacity-40"
            >
              <Smartphone className="w-3.5 h-3.5" />
              {sending ? 'Enviando...' : 'Enviar via WhatsApp'}
            </button>
          ) : (
            <button
              onClick={handleMarkSent}
              disabled={!draftText || sending}
              className="btn-primary text-xs flex items-center gap-1.5 py-1.5 disabled:opacity-40"
            >
              <Send className="w-3.5 h-3.5" />
              {sending ? 'Salvando...' : 'Marcar como enviada'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Thread Detail ─────────────────────────────────────────────────────────────

function ThreadDetail({ thread, onRefresh, liveDraft, onClearLiveDraft }) {
  const [noteText, setNoteText] = useState('')
  const [addingNote, setAddingNote] = useState(false)
  const [showNoteInput, setShowNoteInput] = useState(false)
  const [showGuestPanel, setShowGuestPanel] = useState(false)
  const timelineRef = useRef(null)

  useEffect(() => {
    setTimeout(() => {
      if (timelineRef.current) {
        timelineRef.current.scrollTop = timelineRef.current.scrollHeight
      }
    }, 50)
  }, [thread.id, thread.entries?.length])

  const handleStatusChange = async (newStatus) => {
    try {
      await api.patch(`/inbox/${thread.id}`, { status: newStatus })
      toast.success(`Conversa marcada como ${STATUS_CONFIG[newStatus]?.label || newStatus}`)
      onRefresh()
    } catch {
      toast.error('Erro ao atualizar status')
    }
  }

  const handleAddNote = async () => {
    if (!noteText.trim()) return
    setAddingNote(true)
    try {
      await api.post(`/inbox/${thread.id}/entries`, {
        direction: 'note',
        body: noteText.trim(),
      })
      setNoteText('')
      setShowNoteInput(false)
      onRefresh()
    } catch {
      toast.error('Erro ao salvar nota')
    } finally {
      setAddingNote(false)
    }
  }

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* Main conversation area */}
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-slate-200 bg-white flex items-center justify-between gap-3 shrink-0">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="font-semibold text-slate-800 truncate">
                {thread.guest_name || 'Hóspede desconhecido'}
              </h2>
              {thread.guest_contact && (
                <span className="text-xs text-slate-400">{thread.guest_contact}</span>
              )}
              {/* SLA indicators */}
              {thread.is_overdue && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> Atrasada
                </span>
              )}
              {thread.is_stale && !thread.is_overdue && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Parada
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap mt-1">
              <StatusBadge status={thread.status} />
              {thread.source_type === 'gmail' && (
                <GmailBadge syncStatus={thread.sync_status} />
              )}
              {thread.detected_context && <ContextBadge context={thread.detected_context} />}
              {thread.property && (
                <span className="text-xs text-slate-500 flex items-center gap-1">
                  <Building2 className="w-3 h-3" /> {thread.property.name}
                </span>
              )}
              {thread.subject && (
                <span className="text-xs text-slate-400 truncate max-w-48">{thread.subject}</span>
              )}
              {thread.last_synced_at && (
                <span className="text-xs text-slate-400 flex items-center gap-1">
                  <RefreshCw className="w-3 h-3" />
                  Sync {timeAgo(thread.last_synced_at)}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {/* Guest profile button */}
            {thread.guest_profile_id && (
              <button
                onClick={() => setShowGuestPanel(v => !v)}
                className={clsx(
                  'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
                  showGuestPanel
                    ? 'bg-brand-100 text-brand-700'
                    : 'bg-slate-50 text-slate-500 hover:bg-slate-100',
                )}
              >
                <User className="w-3.5 h-3.5" /> Hóspede
              </button>
            )}
            {thread.status !== 'resolved' && (
              <button
                onClick={() => handleStatusChange('resolved')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 transition-colors"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Resolver
              </button>
            )}
            {thread.status !== 'archived' && (
              <button
                onClick={() => handleStatusChange('archived')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-slate-50 text-slate-500 hover:bg-slate-100 transition-colors"
              >
                <Archive className="w-3.5 h-3.5" /> Arquivar
              </button>
            )}
            {thread.status === 'resolved' && (
              <button
                onClick={() => handleStatusChange('open')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Reabrir
              </button>
            )}
            <button
              onClick={() => setShowNoteInput(!showNoteInput)}
              className={clsx(
                'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
                showNoteInput ? 'bg-amber-100 text-amber-700' : 'bg-slate-50 text-slate-500 hover:bg-slate-100',
              )}
            >
              <StickyNote className="w-3.5 h-3.5" /> Nota
            </button>
          </div>
        </div>

        {/* Note input */}
        {showNoteInput && (
          <div className="px-5 py-3 bg-amber-50 border-b border-amber-200 shrink-0">
            <textarea
              className="w-full border border-amber-200 rounded-lg p-2.5 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-amber-200 bg-white"
              rows={2}
              placeholder="Nota interna (apenas você vê isso)..."
              value={noteText}
              onChange={e => setNoteText(e.target.value)}
              autoFocus
            />
            <div className="flex gap-2 mt-1.5">
              <button onClick={handleAddNote} disabled={!noteText.trim() || addingNote}
                className="btn-primary text-xs py-1 px-3">
                {addingNote ? 'Salvando...' : 'Salvar nota'}
              </button>
              <button onClick={() => setShowNoteInput(false)}
                className="btn-secondary text-xs py-1 px-3">
                Cancelar
              </button>
            </div>
          </div>
        )}

        {/* Timeline */}
        <div ref={timelineRef} className="flex-1 overflow-y-auto px-5 py-4">
          {!thread.entries?.length ? (
            <div className="text-center text-slate-400 text-sm py-10">
              Nenhuma mensagem ainda.
            </div>
          ) : (
            thread.entries.map(entry => (
              <EntryBubble key={entry.id} entry={entry} />
            ))
          )}
        </div>

        {/* Draft panel */}
        <DraftPanel
          thread={thread}
          onRefresh={onRefresh}
          liveDraft={liveDraft}
          onClearLiveDraft={onClearLiveDraft}
        />
      </div>

      {/* Guest panel (slides in from right) */}
      {showGuestPanel && thread.guest_profile_id && (
        <GuestPanel
          profileId={thread.guest_profile_id}
          onClose={() => setShowGuestPanel(false)}
        />
      )}
    </div>
  )
}

// ── New Thread Form ───────────────────────────────────────────────────────────

function NewThreadForm({ onCreated, onCancel, properties }) {
  const [form, setForm] = useState({
    guest_message: '', guest_name: '', guest_contact: '', subject: '', property_id: '',
  })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.guest_message.trim()) return
    setLoading(true)
    try {
      const payload = {
        ...form,
        property_id: form.property_id ? parseInt(form.property_id) : null,
        source_type: 'manual',
      }
      const { data } = await api.post('/inbox', payload)
      toast.success('Conversa criada! Gerando rascunho...')
      onCreated(data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao criar conversa')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-3.5 border-b border-slate-200 bg-white flex items-center justify-between">
        <h2 className="font-semibold text-slate-800">Nova conversa</h2>
        <button onClick={onCancel} className="text-slate-400 hover:text-slate-600">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nome do hóspede</label>
              <input className="input" placeholder="Ex: Maria Silva" value={form.guest_name}
                onChange={e => setForm({ ...form, guest_name: e.target.value })} />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Contato</label>
              <input className="input" placeholder="E-mail ou telefone" value={form.guest_contact}
                onChange={e => setForm({ ...form, guest_contact: e.target.value })} />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Imóvel (opcional)</label>
            <select className="input" value={form.property_id}
              onChange={e => setForm({ ...form, property_id: e.target.value })}>
              <option value="">Sem imóvel específico</option>
              {properties.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Mensagem do hóspede <span className="text-red-500">*</span>
            </label>
            <textarea
              className="input resize-none"
              rows={6}
              placeholder="Cole a mensagem do hóspede aqui..."
              value={form.guest_message}
              onChange={e => setForm({ ...form, guest_message: e.target.value })}
              required
            />
          </div>

          <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2" disabled={loading}>
            <Plus className="w-4 h-4" />
            {loading ? 'Criando e gerando rascunho...' : 'Criar conversa + gerar rascunho'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Bulk Action Toolbar ───────────────────────────────────────────────────────

function BulkToolbar({ selectedIds, onAction, onCancel }) {
  const [loading, setLoading] = useState(false)

  const handleAction = async (action) => {
    setLoading(true)
    try {
      const { data } = await api.post('/inbox/bulk', { ids: selectedIds, action })
      toast.success(`${data.updated} conversas atualizadas`)
      onAction()
    } catch {
      toast.error('Erro ao executar ação em lote')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-brand-50 border-b border-brand-100">
      <span className="text-xs font-semibold text-brand-700">
        {selectedIds.length} selecionadas
      </span>
      <div className="flex items-center gap-1 ml-1">
        {BULK_ACTIONS.map(({ action, label, color }) => (
          <button
            key={action}
            onClick={() => handleAction(action)}
            disabled={loading}
            className={clsx('text-xs px-2.5 py-1 rounded-lg font-medium transition-colors disabled:opacity-50', color)}
          >
            {label}
          </button>
        ))}
      </div>
      <button
        onClick={onCancel}
        className="ml-auto text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
      >
        <X className="w-3.5 h-3.5" /> Cancelar
      </button>
    </div>
  )
}

// ── Inbox Page ────────────────────────────────────────────────────────────────

const STATUS_TABS = [
  { value: 'open',     label: 'Abertas' },
  { value: 'pending',  label: 'Pendentes' },
  { value: 'resolved', label: 'Resolvidas' },
  { value: 'archived', label: 'Arquivadas' },
]

export default function Inbox() {
  const [threads, setThreads] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [threadDetail, setThreadDetail] = useState(null)
  const [showNewThread, setShowNewThread] = useState(false)
  const [properties, setProperties] = useState([])
  const [statusFilter, setStatusFilter] = useState('open')
  const [contextFilter, setContextFilter] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [inboxAddress, setInboxAddress] = useState(null)

  // Bulk selection
  const [bulkMode, setBulkMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState([])

  // SSE live events
  const [liveDraft, setLiveDraft] = useState(null)
  const sseRef = useRef(null)

  const debouncedSearch = useDebounce(searchQuery, 350)

  // ── Load threads ─────────────────────────────────────────────────────────

  const loadThreads = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (statusFilter) params.set('status', statusFilter)
      if (contextFilter) params.set('context', contextFilter)
      if (debouncedSearch.trim()) params.set('q', debouncedSearch.trim())
      const { data } = await api.get(`/inbox?${params}`)
      setThreads(data)
    } catch {
      toast.error('Erro ao carregar conversas')
    } finally {
      setLoading(false)
    }
  }, [statusFilter, contextFilter, debouncedSearch])

  const loadDetail = useCallback(async (id) => {
    setDetailLoading(true)
    try {
      const { data } = await api.get(`/inbox/${id}`)
      setThreadDetail(data)
    } catch {
      toast.error('Erro ao carregar conversa')
    } finally {
      setDetailLoading(false)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    loadThreads()
  }, [loadThreads])

  useEffect(() => {
    api.get('/properties').then(({ data }) => setProperties(data)).catch(() => {})
    api.get('/channels/inbox-address').then(({ data }) => setInboxAddress(data.address)).catch(() => {})
  }, [])

  useEffect(() => {
    if (selectedId) loadDetail(selectedId)
    else setThreadDetail(null)
  }, [selectedId, loadDetail])

  // ── SSE subscription ──────────────────────────────────────────────────────

  useEffect(() => {
    const token = localStorage.getItem('hf_token')
    if (!token) return

    const es = new EventSource(`/api/v1/inbox/events?token=${encodeURIComponent(token)}`)
    sseRef.current = es

    es.addEventListener('thread_created', () => {
      loadThreads()
    })

    es.addEventListener('thread_updated', (e) => {
      const updated = JSON.parse(e.data)
      // Update the thread in the list
      setThreads(prev => prev.map(t => t.id === updated.id ? { ...t, ...updated } : t))
      // If it's the currently open thread, also update the detail header fields
      setThreadDetail(prev => prev && prev.id === updated.id ? { ...prev, ...updated } : prev)
    })

    es.addEventListener('entry_added', (e) => {
      const { thread_id, entry } = JSON.parse(e.data)
      if (thread_id === selectedId) {
        setThreadDetail(prev => {
          if (!prev) return prev
          const alreadyExists = prev.entries?.some(en => en.id === entry.id)
          if (alreadyExists) return prev
          return { ...prev, entries: [...(prev.entries || []), entry] }
        })
      }
      // Also bump thread in list
      setThreads(prev => prev.map(t =>
        t.id === thread_id ? { ...t, last_message_at: entry.created_at } : t
      ))
    })

    es.addEventListener('gmail_synced', (e) => {
      const { new_entries } = JSON.parse(e.data)
      if (new_entries > 0) {
        toast(`Gmail: ${new_entries} novas conversas sincronizadas`, { icon: '📬' })
        loadThreads()
      }
    })

    es.addEventListener('draft_ready', (e) => {
      const { thread_id, draft, applied_template_id, template_auto_applied, auto_send_decision } = JSON.parse(e.data)
      let msg
      if (auto_send_decision === 'sent') {
        msg = 'Resposta enviada automaticamente!'
      } else if (auto_send_decision === 'blocked') {
        msg = 'Rascunho pronto — envio automático bloqueado por guardrail'
      } else if (applied_template_id) {
        msg = template_auto_applied ? 'Rascunho gerado com template automático!' : 'Rascunho gerado com template!'
      } else {
        msg = 'Rascunho pronto!'
      }
      if (auto_send_decision === 'blocked') {
        toast(msg, { icon: '🛡️' })
      } else {
        toast.success(msg, { icon: auto_send_decision === 'sent' ? '⚡' : '🤖' })
      }
      if (thread_id === selectedId) {
        setLiveDraft(draft)
      }
      loadThreads()
    })

    es.addEventListener('entry_status_updated', (e) => {
      const { thread_id, delivery_status } = JSON.parse(e.data)
      // Refresh thread detail if it's currently open
      if (thread_id === selectedId) {
        // Trigger a re-load via loadThreads to update entry delivery_status
        loadThreads()
      }
      if (delivery_status === 'read') {
        toast('Mensagem lida pelo hóspede', { icon: '✅' })
      }
    })

    es.onerror = () => {
      // EventSource auto-reconnects; suppress console noise
    }

    return () => {
      es.close()
    }
  }, [selectedId, loadThreads])

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleSelectThread = (id) => {
    if (bulkMode) return
    setShowNewThread(false)
    setSelectedId(id)
  }

  const handleNewThreadCreated = (thread) => {
    setShowNewThread(false)
    loadThreads()
    setSelectedId(thread.id)
  }

  const handleRefreshDetail = () => {
    if (selectedId) loadDetail(selectedId)
    loadThreads()
  }

  const handleCheckThread = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  const handleBulkDone = () => {
    setSelectedIds([])
    setBulkMode(false)
    loadThreads()
    if (selectedId) loadDetail(selectedId)
  }

  const handleCancelBulk = () => {
    setSelectedIds([])
    setBulkMode(false)
  }

  const toggleBulkMode = () => {
    setBulkMode(v => !v)
    setSelectedIds([])
  }

  const uniqueContexts = [...new Set(threads.map(t => t.detected_context).filter(Boolean))]

  const rightContent = showNewThread ? 'new_form' : threadDetail ? 'detail' : 'empty'

  return (
    <Layout>
      <div className="-m-8 flex overflow-hidden" style={{ height: '100vh' }}>

        {/* ── Left: Thread list ───────────────────────────────────────────── */}
        <aside className="w-80 shrink-0 border-r border-slate-200 bg-white flex flex-col">
          {/* Header */}
          <div className="px-4 py-3.5 border-b border-slate-100">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <InboxIcon className="w-4 h-4 text-brand-600" />
                <h1 className="font-bold text-slate-800">Caixa de entrada</h1>
              </div>
              <div className="flex items-center gap-1">
                {/* Bulk mode toggle */}
                <button
                  onClick={toggleBulkMode}
                  title="Selecionar em lote"
                  className={clsx(
                    'p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors',
                    bulkMode && 'bg-brand-50 text-brand-600',
                  )}
                >
                  <CheckSquare className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => { setLoading(true); loadThreads() }}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => { setShowNewThread(true); setSelectedId(null) }}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-brand-600 text-white text-xs font-medium hover:bg-brand-700 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" /> Nova
                </button>
              </div>
            </div>

            {/* Search */}
            <div className="relative mb-2">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Buscar conversas..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand-200 bg-white"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Status tabs */}
            <div className="flex gap-0.5 bg-slate-100 rounded-lg p-0.5 mb-2">
              {STATUS_TABS.map(tab => (
                <button
                  key={tab.value}
                  onClick={() => { setStatusFilter(tab.value); setSelectedId(null) }}
                  className={clsx(
                    'flex-1 text-xs py-1 rounded-md font-medium transition-colors',
                    statusFilter === tab.value
                      ? 'bg-white text-slate-800 shadow-sm'
                      : 'text-slate-500 hover:text-slate-700',
                  )}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Context filter */}
            {uniqueContexts.length > 0 && (
              <select
                className="w-full text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white text-slate-600 focus:outline-none focus:ring-1 focus:ring-brand-200"
                value={contextFilter}
                onChange={e => setContextFilter(e.target.value)}
              >
                <option value="">Todos os contextos</option>
                {uniqueContexts.map(c => (
                  <option key={c} value={c}>{CONTEXT_LABELS[c] || c}</option>
                ))}
              </select>
            )}
          </div>

          {/* Bulk action toolbar */}
          {bulkMode && selectedIds.length > 0 && (
            <BulkToolbar
              selectedIds={selectedIds}
              onAction={handleBulkDone}
              onCancel={handleCancelBulk}
            />
          )}

          {/* Thread list */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="text-center py-10 text-slate-400 text-sm">Carregando...</div>
            ) : threads.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <InboxIcon className="w-8 h-8 text-slate-300 mx-auto mb-2" />
                <p className="text-sm text-slate-500 mb-1">
                  {debouncedSearch ? 'Nenhum resultado' : 'Nenhuma conversa'}
                </p>
                {!debouncedSearch && statusFilter === 'open' && (
                  <p className="text-xs text-slate-400">Clique em "Nova" para começar</p>
                )}
              </div>
            ) : (
              threads.map(thread => (
                <ThreadCard
                  key={thread.id}
                  thread={thread}
                  selected={selectedId === thread.id}
                  onClick={() => handleSelectThread(thread.id)}
                  bulkMode={bulkMode}
                  checked={selectedIds.includes(thread.id)}
                  onCheck={handleCheckThread}
                />
              ))
            )}
          </div>

          {/* Inbox address hint */}
          {inboxAddress && (
            <div className="px-4 py-3 border-t border-slate-100 bg-slate-50">
              <p className="text-xs text-slate-500 mb-1 font-medium flex items-center gap-1">
                <Mail className="w-3 h-3" /> Encaminhe e-mails para:
              </p>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(inboxAddress)
                  toast.success('Endereço copiado!')
                }}
                className="text-xs text-brand-600 font-mono break-all hover:underline text-left"
              >
                {inboxAddress}
              </button>
            </div>
          )}
        </aside>

        {/* ── Right panel ─────────────────────────────────────────────────── */}
        <main className="flex-1 flex overflow-hidden bg-slate-50">
          {rightContent === 'new_form' && (
            <div className="flex-1 flex flex-col">
              <NewThreadForm
                onCreated={handleNewThreadCreated}
                onCancel={() => setShowNewThread(false)}
                properties={properties}
              />
            </div>
          )}

          {rightContent === 'detail' && (
            detailLoading ? (
              <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
                Carregando conversa...
              </div>
            ) : (
              <ThreadDetail
                thread={threadDetail}
                onRefresh={handleRefreshDetail}
                liveDraft={liveDraft}
                onClearLiveDraft={() => setLiveDraft(null)}
              />
            )
          )}

          {rightContent === 'empty' && (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
              <InboxIcon className="w-12 h-12 mb-3 text-slate-300" />
              <p className="text-base font-medium text-slate-500">Selecione uma conversa</p>
              <p className="text-sm mt-1 text-slate-400">ou crie uma nova</p>
              <div className="mt-6 space-y-2 text-xs text-slate-400 text-center max-w-xs">
                <p>
                  Encaminhe e-mails de hóspedes para o seu endereço de ingestion e o HostFlow
                  criará automaticamente a conversa.
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </Layout>
  )
}
