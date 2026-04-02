import { useState } from 'react'
import { Calculator as CalcIcon, Copy, DollarSign, Building2 } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import Layout from '../components/Layout'
import PropertySelect from '../components/PropertySelect'

const fmt = (v) => Number(v).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

function ValueCard({ label, value }) {
  return (
    <div className="bg-slate-50 rounded-lg p-4">
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className="text-xl font-bold text-slate-800">{fmt(value)}</p>
    </div>
  )
}

function MessageBlock({ label, content }) {
  const copy = () => {
    navigator.clipboard.writeText(content)
    toast.success('Mensagem copiada!')
  }
  return (
    <div className="bg-brand-50 border border-brand-100 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">{label}</p>
        <button onClick={copy} className="text-slate-400 hover:text-slate-600">
          <Copy className="w-3.5 h-3.5" />
        </button>
      </div>
      <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{content}</p>
    </div>
  )
}

export default function Calculator() {
  const [propertyId, setPropertyId] = useState(null)
  const [dailyRate, setDailyRate] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleCalculate = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const payload = {}
      if (propertyId) payload.property_id = propertyId
      if (dailyRate) payload.daily_rate = parseFloat(dailyRate)

      const { data } = await api.post('/calculator/', payload)
      setResult(data)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao calcular')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-800">Calculadora</h1>
          <p className="text-slate-500 text-sm mt-1">
            Selecione o imóvel para usar as regras e valores cadastrados, ou informe manualmente.
          </p>
        </div>

        <div className="card p-6 mb-6">
          <form onSubmit={handleCalculate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Imóvel <span className="text-slate-400 font-normal">opcional</span>
              </label>
              <PropertySelect
                value={propertyId}
                onChange={(id) => { setPropertyId(id); setResult(null) }}
                placeholder="Sem imóvel (inserir valor manualmente)"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                Valor da diária (R$)
                {propertyId && <span className="text-slate-400 font-normal ml-1">— sobrescreve o valor do imóvel</span>}
              </label>
              <div className="relative">
                <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  className="input pl-9"
                  type="number"
                  placeholder={propertyId ? 'Opcional — usa valor cadastrado no imóvel' : 'Ex: 300.00'}
                  min="1"
                  step="0.01"
                  value={dailyRate}
                  onChange={(e) => setDailyRate(e.target.value)}
                  required={!propertyId}
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn-primary flex items-center gap-2 w-full justify-center"
              disabled={loading || (!propertyId && !dailyRate)}
            >
              <CalcIcon className="w-4 h-4" />
              {loading ? 'Calculando...' : 'Calcular'}
            </button>
          </form>
        </div>

        {result && (
          <div className="space-y-5">
            {result.property_name && (
              <div className="flex items-center gap-2 text-sm text-brand-700 bg-brand-50 rounded-lg px-4 py-2.5">
                <Building2 className="w-4 h-4" />
                <span className="font-medium">{result.property_name}</span>
                <span className="text-brand-500">•</span>
                <span>Check-in {result.check_in_time} · Check-out {result.check_out_time}</span>
              </div>
            )}

            <div className="card p-6">
              <h2 className="font-semibold text-slate-800 mb-4">Valores calculados</h2>
              <div className="grid grid-cols-2 gap-3 mb-3">
                <ValueCard label="Diária completa" value={result.daily_rate} />
                <ValueCard label="Meia diária" value={result.half_day_rate} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <ValueCard label="Valor por hora" value={result.hourly_rate} />
                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-xs text-slate-500 mb-1">Referência rápida</p>
                  <p className="text-sm text-slate-600">
                    2h = {fmt(result.hourly_rate * 2)}<br />
                    3h = {fmt(result.hourly_rate * 3)}<br />
                    4h = {fmt(result.hourly_rate * 4)}
                  </p>
                </div>
              </div>
            </div>

            <div className="card p-6">
              <h2 className="font-semibold text-slate-800 mb-4">Mensagens prontas para enviar</h2>
              <div className="space-y-3">
                <MessageBlock label="Early Check-in" content={result.early_checkin_message} />
                <MessageBlock label="Late Check-out" content={result.late_checkout_message} />
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
