import { useState, useEffect } from 'react'
import { Plus, Copy, Pencil, Trash2, X, Check, Building2, Zap, Bot } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import Layout from '../components/Layout'
import PropertySelect from '../components/PropertySelect'
import useProperties from '../hooks/useProperties'
import clsx from 'clsx'

// ── Constants ────────────────────────────────────────────────────────────────

const CATEGORY_LABELS = {
  welcome:  { label: 'Boas-vindas', color: 'bg-green-100 text-green-700' },
  rules:    { label: 'Regras',      color: 'bg-blue-100 text-blue-700' },
  refusal:  { label: 'Recusa',      color: 'bg-red-100 text-red-700' },
  charge:   { label: 'Cobrança',    color: 'bg-orange-100 text-orange-700' },
  issue:    { label: 'Problema',    color: 'bg-yellow-100 text-yellow-700' },
  other:    { label: 'Outro',       color: 'bg-slate-100 text-slate-600' },
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
}

const CONTEXT_OPTIONS = [
  { value: '', label: '— Nenhum —' },
  ...Object.entries(CONTEXT_LABELS).map(([value, label]) => ({ value, label })),
]

const TONE_OPTIONS = [
  { value: '', label: '— Padrão —' },
  { value: 'friendly', label: 'Amigável' },
  { value: 'formal',   label: 'Formal' },
  { value: 'brief',    label: 'Breve' },
]

const CHANNEL_OPTIONS = [
  { value: '', label: '— Qualquer canal —' },
  { value: 'manual',        label: 'Manual' },
  { value: 'email_forward', label: 'E-mail encaminhado' },
  { value: 'gmail',         label: 'Gmail' },
  { value: 'whatsapp',      label: 'WhatsApp' },
  { value: 'webhook',       label: 'Webhook' },
]

const CATEGORIES = Object.entries(CATEGORY_LABELS).map(([value, { label }]) => ({ value, label }))

// ── Template form modal ───────────────────────────────────────────────────────

function TemplateModal({ initial, onSave, onClose }) {
  const [form, setForm] = useState(
    initial
      ? {
          title: initial.title,
          category: initial.category,
          content: initial.content,
          property_id: initial.property_id ?? null,
          context_key: initial.context_key ?? '',
          channel_type: initial.channel_type ?? '',
          tone: initial.tone ?? '',
          priority: initial.priority ?? 0,
          auto_apply: initial.auto_apply ?? false,
          active: initial.active ?? true,
        }
      : {
          title: '',
          category: 'other',
          content: '',
          property_id: null,
          context_key: '',
          channel_type: '',
          tone: '',
          priority: 0,
          auto_apply: false,
          active: true,
        }
  )

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  const handleSave = () => {
    const payload = {
      ...form,
      context_key: form.context_key || null,
      channel_type: form.channel_type || null,
      tone: form.tone || null,
    }
    onSave(payload)
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4 overflow-y-auto">
      <div className="card w-full max-w-xl p-6 my-4">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-slate-800">
            {initial ? 'Editar template' : 'Novo template'}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Título</label>
            <input
              className="input"
              value={form.title}
              onChange={e => set('title', e.target.value)}
              placeholder="Ex: Resposta para early check-in"
            />
          </div>

          {/* Category + Property */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">Categoria</label>
              <select className="input" value={form.category} onChange={e => set('category', e.target.value)}>
                {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Imóvel <span className="text-slate-400 font-normal">opcional</span>
              </label>
              <PropertySelect
                value={form.property_id}
                onChange={id => set('property_id', id)}
                placeholder="Global (todos imóveis)"
              />
            </div>
          </div>

          {/* Smart-match section */}
          <div className="rounded-xl border border-brand-100 bg-brand-50/40 p-4 space-y-3">
            <p className="text-xs font-semibold text-brand-700 uppercase tracking-wide flex items-center gap-1.5">
              <Bot className="w-3.5 h-3.5" /> Match automático
            </p>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Contexto</label>
                <select className="input text-sm" value={form.context_key} onChange={e => set('context_key', e.target.value)}>
                  {CONTEXT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Canal</label>
                <select className="input text-sm" value={form.channel_type} onChange={e => set('channel_type', e.target.value)}>
                  {CHANNEL_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">Tom</label>
                <select className="input text-sm" value={form.tone} onChange={e => set('tone', e.target.value)}>
                  {TONE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Prioridade
                  <span className="ml-1 text-slate-400 font-normal">(maior = preferido)</span>
                </label>
                <input
                  type="number"
                  className="input text-sm"
                  value={form.priority}
                  onChange={e => set('priority', parseInt(e.target.value, 10) || 0)}
                  min={-10}
                  max={100}
                />
              </div>
            </div>

            {/* Auto-apply toggle */}
            <label className="flex items-start gap-3 cursor-pointer">
              <div className="relative mt-0.5">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={form.auto_apply}
                  onChange={e => set('auto_apply', e.target.checked)}
                />
                <div className={clsx(
                  'w-9 h-5 rounded-full transition-colors',
                  form.auto_apply ? 'bg-brand-600' : 'bg-slate-200',
                )} />
                <div className={clsx(
                  'absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform',
                  form.auto_apply ? 'translate-x-4' : 'translate-x-0',
                )} />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-700">Aplicar automaticamente</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  Quando o contexto for detectado, usar este template como base para o rascunho IA.
                </p>
              </div>
            </label>
          </div>

          {/* Content */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Conteúdo</label>
            <textarea
              className="input resize-none"
              rows={6}
              value={form.content}
              onChange={e => set('content', e.target.value)}
              placeholder="Digite o texto do template..."
            />
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-5">
          <button onClick={onClose} className="btn-secondary">Cancelar</button>
          <button
            onClick={handleSave}
            className="btn-primary flex items-center gap-1.5"
            disabled={!form.title || !form.content}
          >
            <Check className="w-4 h-4" /> Salvar
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Template card ─────────────────────────────────────────────────────────────

function TemplateCard({ t, propertyName, onEdit, onDelete, onCopy }) {
  const cat = CATEGORY_LABELS[t.category] || CATEGORY_LABELS.other
  const ctxLabel = t.context_key ? CONTEXT_LABELS[t.context_key] : null

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Badges row */}
          <div className="flex items-center gap-1.5 flex-wrap mb-2">
            <h3 className="font-medium text-slate-800 text-sm">{t.title}</h3>
            <span className={clsx('text-xs px-2 py-0.5 rounded-full font-medium', cat.color)}>
              {cat.label}
            </span>
            {ctxLabel && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 font-medium flex items-center gap-1">
                <Bot className="w-3 h-3" /> {ctxLabel}
              </span>
            )}
            {t.auto_apply && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-100 text-brand-700 font-medium flex items-center gap-1">
                <Zap className="w-3 h-3" /> Auto
              </span>
            )}
            {propertyName && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700 flex items-center gap-1">
                <Building2 className="w-3 h-3" /> {propertyName}
              </span>
            )}
            {t.tone && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                {t.tone}
              </span>
            )}
            {t.priority > 0 && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
                P{t.priority}
              </span>
            )}
            {t.is_default && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-400">
                padrão
              </span>
            )}
            {!t.active && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-50 text-red-500">
                inativo
              </span>
            )}
          </div>
          <p className="text-sm text-slate-600 whitespace-pre-wrap leading-relaxed line-clamp-4">
            {t.content}
          </p>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => onCopy(t.content)}
            className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
            title="Copiar"
          >
            <Copy className="w-4 h-4" />
          </button>
          {!t.is_default && (
            <>
              <button
                onClick={() => onEdit(t)}
                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                title="Editar"
              >
                <Pencil className="w-4 h-4" />
              </button>
              <button
                onClick={() => onDelete(t.id)}
                className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                title="Excluir"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Templates() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState(null)
  const [filterCategory, setFilterCategory] = useState('all')
  const [filterContext, setFilterContext] = useState('all')
  const [filterPropertyId, setFilterPropertyId] = useState(null)
  const { properties, loaded: propertiesLoaded, fetch: fetchProps } = useProperties()

  useEffect(() => {
    if (!propertiesLoaded) fetchProps()
    fetchTemplates()
  }, [filterPropertyId])

  const fetchTemplates = async () => {
    try {
      const params = new URLSearchParams()
      if (filterPropertyId) params.set('property_id', filterPropertyId)
      params.set('active_only', 'false') // show inactive too, so user can re-enable
      const { data } = await api.get(`/templates/?${params}`)
      setTemplates(data)
    } catch {
      toast.error('Erro ao carregar templates')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (form) => {
    try {
      if (editing) {
        const { data } = await api.put(`/templates/${editing.id}`, form)
        setTemplates(prev => prev.map(t => t.id === editing.id ? data : t))
        toast.success('Template atualizado!')
      } else {
        const { data } = await api.post('/templates/', form)
        setTemplates(prev => [data, ...prev])
        toast.success('Template criado!')
      }
      setShowModal(false)
      setEditing(null)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao salvar template')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Excluir este template?')) return
    try {
      await api.delete(`/templates/${id}`)
      setTemplates(prev => prev.filter(t => t.id !== id))
      toast.success('Template excluído')
    } catch {
      toast.error('Não é possível excluir templates padrão')
    }
  }

  const getPropertyName = id => properties.find(p => p.id === id)?.name

  const filtered = templates.filter(t => {
    if (filterCategory !== 'all' && t.category !== filterCategory) return false
    if (filterContext !== 'all') {
      if (filterContext === 'none' && t.context_key) return false
      if (filterContext !== 'none' && t.context_key !== filterContext) return false
    }
    return true
  })

  // Group: context-specific first, then generic
  const withContext = filtered.filter(t => t.context_key)
  const withoutContext = filtered.filter(t => !t.context_key)

  return (
    <Layout>
      <div className="max-w-3xl mx-auto">
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Templates</h1>
            <p className="text-slate-500 text-sm mt-1">
              Mensagens prontas. Globais ou por imóvel. A IA usa automaticamente o template certo.
            </p>
          </div>
          <button
            onClick={() => { setEditing(null); setShowModal(true) }}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" /> Novo template
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mb-5">
          {/* Category filter */}
          <div className="flex gap-2 flex-wrap flex-1 min-w-0">
            {[{ value: 'all', label: `Todos (${templates.length})` }, ...CATEGORIES].map(c => {
              const count = c.value === 'all' ? templates.length : templates.filter(t => t.category === c.value).length
              if (c.value !== 'all' && !count) return null
              return (
                <button
                  key={c.value}
                  onClick={() => setFilterCategory(c.value)}
                  className={clsx(
                    'text-xs px-3 py-1.5 rounded-full font-medium transition-colors',
                    filterCategory === c.value
                      ? 'bg-brand-600 text-white'
                      : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50',
                  )}
                >
                  {c.value === 'all' ? c.label : `${c.label} (${count})`}
                </button>
              )
            })}
          </div>
          <div className="w-44 shrink-0">
            <PropertySelect
              value={filterPropertyId}
              onChange={setFilterPropertyId}
              placeholder="Todos os imóveis"
            />
          </div>
        </div>

        {/* Context filter pills */}
        <div className="flex gap-1.5 flex-wrap mb-5">
          {[
            { value: 'all', label: 'Todos os contextos' },
            { value: 'none', label: 'Sem contexto' },
            ...Object.entries(CONTEXT_LABELS)
              .filter(([ctx]) => templates.some(t => t.context_key === ctx))
              .map(([value, label]) => ({ value, label })),
          ].map(c => (
            <button
              key={c.value}
              onClick={() => setFilterContext(c.value)}
              className={clsx(
                'text-xs px-2.5 py-1 rounded-lg font-medium transition-colors border',
                filterContext === c.value
                  ? 'bg-violet-600 text-white border-violet-600'
                  : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50',
              )}
            >
              {c.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-10 text-slate-400 text-sm">Carregando...</div>
        ) : (
          <div className="space-y-3">
            {/* Context-specific group */}
            {withContext.length > 0 && (
              <>
                <div className="flex items-center gap-2 py-1">
                  <Bot className="w-3.5 h-3.5 text-violet-500" />
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Com contexto detectável ({withContext.length})
                  </span>
                </div>
                {withContext.map(t => (
                  <TemplateCard
                    key={t.id}
                    t={t}
                    propertyName={t.property_id ? getPropertyName(t.property_id) : null}
                    onEdit={t => { setEditing(t); setShowModal(true) }}
                    onDelete={handleDelete}
                    onCopy={content => { navigator.clipboard.writeText(content); toast.success('Copiado!') }}
                  />
                ))}
              </>
            )}

            {/* Generic group */}
            {withoutContext.length > 0 && (
              <>
                <div className="flex items-center gap-2 py-1 mt-2">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                    Genéricos ({withoutContext.length})
                  </span>
                </div>
                {withoutContext.map(t => (
                  <TemplateCard
                    key={t.id}
                    t={t}
                    propertyName={t.property_id ? getPropertyName(t.property_id) : null}
                    onEdit={t => { setEditing(t); setShowModal(true) }}
                    onDelete={handleDelete}
                    onCopy={content => { navigator.clipboard.writeText(content); toast.success('Copiado!') }}
                  />
                ))}
              </>
            )}

            {filtered.length === 0 && (
              <div className="text-center py-10 text-slate-400 text-sm">
                Nenhum template neste filtro.
              </div>
            )}
          </div>
        )}
      </div>

      {showModal && (
        <TemplateModal
          initial={editing}
          onSave={handleSave}
          onClose={() => { setShowModal(false); setEditing(null) }}
        />
      )}
    </Layout>
  )
}
