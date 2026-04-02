import { useState, useEffect } from 'react'
import { Plus, Pencil, Trash2, Building2, ChevronDown, ChevronUp, Clock, DollarSign } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import Layout from '../components/Layout'
import UpgradeModal from '../components/UpgradeModal'
import useProperties from '../hooks/useProperties'

const PROPERTY_TYPES = [
  { value: 'apartamento', label: 'Apartamento' },
  { value: 'casa', label: 'Casa' },
  { value: 'guest_house', label: 'Guest House' },
  { value: 'quarto_privativo', label: 'Quarto Privativo' },
  { value: 'studio', label: 'Studio' },
  { value: 'kitnet', label: 'Kitnet' },
]

const TYPE_LABELS = Object.fromEntries(PROPERTY_TYPES.map((t) => [t.value, t.label]))

const EMPTY_FORM = {
  name: '',
  type: 'apartamento',
  address_label: '',
  check_in_time: '14:00',
  check_out_time: '11:00',
  daily_rate: '',
  half_day_rate: '',
  early_checkin_policy: '',
  late_checkout_policy: '',
  accepts_pets: false,
  has_parking: false,
  parking_policy: '',
  house_rules: '',
}

function Field({ label, hint, children }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      {hint && <p className="text-xs text-slate-400 mb-1.5">{hint}</p>}
      {children}
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="space-y-4">
      <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100 pb-2">
        {title}
      </h3>
      {children}
    </div>
  )
}

function PropertyForm({ initial, onSave, onCancel, saving }) {
  const [form, setForm] = useState(initial ? {
    ...EMPTY_FORM,
    ...initial,
    daily_rate: initial.daily_rate ?? '',
    half_day_rate: initial.half_day_rate ?? '',
  } : { ...EMPTY_FORM })

  const set = (key, val) => setForm((f) => ({ ...f, [key]: val }))

  const handleSubmit = (e) => {
    e.preventDefault()
    const payload = { ...form }
    if (!payload.daily_rate) payload.daily_rate = null
    else payload.daily_rate = parseFloat(payload.daily_rate)
    if (!payload.half_day_rate) payload.half_day_rate = null
    else payload.half_day_rate = parseFloat(payload.half_day_rate)
    // strip empty strings to null
    ;['address_label','early_checkin_policy','late_checkout_policy','parking_policy','house_rules'].forEach((k) => {
      if (!payload[k]) payload[k] = null
    })
    onSave(payload)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Section title="Informações gerais">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Nome do imóvel *">
            <input className="input" value={form.name} onChange={(e) => set('name', e.target.value)} required placeholder="Ex: Apto Centro - Quarto 2" />
          </Field>
          <Field label="Tipo">
            <select className="input" value={form.type} onChange={(e) => set('type', e.target.value)}>
              {PROPERTY_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </Field>
        </div>
        <Field label="Identificação interna" hint="Nome ou referência para você. Não é mostrado ao hóspede.">
          <input className="input" value={form.address_label} onChange={(e) => set('address_label', e.target.value)} placeholder="Ex: Bloco B, Apt 42 — Centro" />
        </Field>
      </Section>

      <Section title="Horários">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Check-in padrão">
            <input className="input" type="time" value={form.check_in_time} onChange={(e) => set('check_in_time', e.target.value)} required />
          </Field>
          <Field label="Check-out padrão">
            <input className="input" type="time" value={form.check_out_time} onChange={(e) => set('check_out_time', e.target.value)} required />
          </Field>
        </div>
      </Section>

      <Section title="Preços">
        <div className="grid grid-cols-2 gap-4">
          <Field label="Valor da diária (R$)">
            <input className="input" type="number" min="0" step="0.01" value={form.daily_rate} onChange={(e) => set('daily_rate', e.target.value)} placeholder="Ex: 250.00" />
          </Field>
          <Field label="Meia diária (R$)" hint="Deixe em branco para usar 50% da diária">
            <input className="input" type="number" min="0" step="0.01" value={form.half_day_rate} onChange={(e) => set('half_day_rate', e.target.value)} placeholder="Automático: diária ÷ 2" />
          </Field>
        </div>
      </Section>

      <Section title="Políticas">
        <Field label="Política de early check-in" hint="Mensagem que será usada pela IA. Deixe em branco para usar o padrão.">
          <textarea className="input resize-none" rows={3} value={form.early_checkin_policy} onChange={(e) => set('early_checkin_policy', e.target.value)} placeholder="Ex: Disponível a partir das 10h mediante pagamento de meia diária..." />
        </Field>
        <Field label="Política de late check-out" hint="Deixe em branco para usar o padrão.">
          <textarea className="input resize-none" rows={3} value={form.late_checkout_policy} onChange={(e) => set('late_checkout_policy', e.target.value)} placeholder="Ex: Saída estendida até 15h por meia diária..." />
        </Field>

        <div className="flex flex-col gap-3">
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" className="w-4 h-4 accent-brand-600" checked={form.accepts_pets} onChange={(e) => set('accepts_pets', e.target.checked)} />
            <span className="text-sm text-slate-700">Aceita animais de estimação</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" className="w-4 h-4 accent-brand-600" checked={form.has_parking} onChange={(e) => set('has_parking', e.target.checked)} />
            <span className="text-sm text-slate-700">Tem estacionamento</span>
          </label>
        </div>

        {form.has_parking && (
          <Field label="Política de estacionamento">
            <input className="input" value={form.parking_policy} onChange={(e) => set('parking_policy', e.target.value)} placeholder="Ex: 1 vaga inclusa. Vaga extra: R$ 20/dia" />
          </Field>
        )}
      </Section>

      <Section title="Regras da casa">
        <Field label="Regras gerais" hint="Estas regras serão incluídas no contexto da IA ao gerar respostas.">
          <textarea className="input resize-none" rows={5} value={form.house_rules} onChange={(e) => set('house_rules', e.target.value)} placeholder="Ex: Proibido fumar. Silêncio após 22h. Não são permitidas festas..." />
        </Field>
      </Section>

      <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
        <button type="button" onClick={onCancel} className="btn-secondary">Cancelar</button>
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? 'Salvando...' : initial ? 'Salvar alterações' : 'Criar imóvel'}
        </button>
      </div>
    </form>
  )
}

function PropertyCard({ property, onEdit, onDelete }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className="w-9 h-9 bg-brand-50 rounded-lg flex items-center justify-center shrink-0 mt-0.5">
            <Building2 className="w-4 h-4 text-brand-600" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="font-semibold text-slate-800">{property.name}</h3>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {TYPE_LABELS[property.type] || property.type}
              </span>
            </div>
            {property.address_label && (
              <p className="text-xs text-slate-400 mt-0.5">{property.address_label}</p>
            )}
            <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {property.check_in_time} → {property.check_out_time}
              </span>
              {property.daily_rate && (
                <span className="flex items-center gap-1">
                  <DollarSign className="w-3 h-3" />
                  {Number(property.daily_rate).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button onClick={onEdit} className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors" title="Editar">
            <Pencil className="w-4 h-4" />
          </button>
          <button onClick={onDelete} className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Excluir">
            <Trash2 className="w-4 h-4" />
          </button>
          <button onClick={() => setExpanded(!expanded)} className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-slate-100 grid grid-cols-2 gap-3 text-sm">
          <InfoRow label="Aceita pets" value={property.accepts_pets ? 'Sim' : 'Não'} />
          <InfoRow label="Estacionamento" value={property.has_parking ? 'Sim' : 'Não'} />
          {property.parking_policy && <InfoRow label="Política de estacionamento" value={property.parking_policy} full />}
          {property.early_checkin_policy && <InfoRow label="Early check-in" value={property.early_checkin_policy} full />}
          {property.late_checkout_policy && <InfoRow label="Late check-out" value={property.late_checkout_policy} full />}
          {property.house_rules && <InfoRow label="Regras da casa" value={property.house_rules} full />}
        </div>
      )}
    </div>
  )
}

function InfoRow({ label, value, full }) {
  return (
    <div className={full ? 'col-span-2' : ''}>
      <p className="text-xs font-medium text-slate-400 mb-0.5">{label}</p>
      <p className="text-slate-700 whitespace-pre-wrap">{value}</p>
    </div>
  )
}

export default function Properties() {
  const { properties, loaded, fetch, add, update, remove } = useProperties()
  const [loading, setLoading] = useState(!loaded)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [saving, setSaving] = useState(false)
  const [upgradeError, setUpgradeError] = useState(null)

  useEffect(() => {
    if (!loaded) {
      fetch().finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const handleSave = async (form) => {
    setSaving(true)
    try {
      if (editing) {
        const { data } = await api.put(`/properties/${editing.id}`, form)
        update(data)
        toast.success('Imóvel atualizado!')
      } else {
        const { data } = await api.post('/properties/', form)
        add(data)
        toast.success('Imóvel criado!')
      }
      setShowForm(false)
      setEditing(null)
    } catch (err) {
      if (err.response?.status === 402) {
        setUpgradeError(err.response.data.detail)
        setShowForm(false)
      } else {
        toast.error(err.response?.data?.detail || 'Erro ao salvar imóvel')
      }
    } finally {
      setSaving(false)
    }
  }

  const handleEdit = (property) => {
    setEditing(property)
    setShowForm(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleDelete = async (id) => {
    if (!confirm('Excluir este imóvel? As conversas vinculadas perderão a referência, mas não serão excluídas.')) return
    try {
      await api.delete(`/properties/${id}`)
      remove(id)
      toast.success('Imóvel excluído')
    } catch {
      toast.error('Erro ao excluir imóvel')
    }
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Meus imóveis</h1>
            <p className="text-slate-500 text-sm mt-1">
              Configure regras por imóvel para respostas mais precisas.
            </p>
          </div>
          {!showForm && (
            <button
              onClick={() => { setEditing(null); setShowForm(true) }}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> Novo imóvel
            </button>
          )}
        </div>

        {showForm && (
          <div className="card p-6 mb-6">
            <h2 className="font-semibold text-slate-800 mb-5">
              {editing ? `Editar: ${editing.name}` : 'Cadastrar novo imóvel'}
            </h2>
            <PropertyForm
              initial={editing}
              onSave={handleSave}
              onCancel={() => { setShowForm(false); setEditing(null) }}
              saving={saving}
            />
          </div>
        )}

        {loading ? (
          <div className="text-center py-10 text-slate-400 text-sm">Carregando...</div>
        ) : properties.length === 0 && !showForm ? (
          <div className="card p-10 text-center">
            <Building2 className="w-10 h-10 text-slate-200 mx-auto mb-3" />
            <p className="font-medium text-slate-600 mb-1">Nenhum imóvel cadastrado</p>
            <p className="text-sm text-slate-400 mb-4">
              Cadastre seu primeiro imóvel para personalizar check-in, check-out, preços e regras.
            </p>
            <button
              onClick={() => setShowForm(true)}
              className="btn-primary inline-flex items-center gap-2"
            >
              <Plus className="w-4 h-4" /> Cadastrar imóvel
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {properties.map((p) => (
              <PropertyCard
                key={p.id}
                property={p}
                onEdit={() => handleEdit(p)}
                onDelete={() => handleDelete(p.id)}
              />
            ))}
          </div>
        )}
      </div>

      <UpgradeModal
        error={upgradeError}
        onClose={() => setUpgradeError(null)}
      />
    </Layout>
  )
}
