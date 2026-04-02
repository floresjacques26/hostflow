import { useState, useMemo } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { MessageSquare, Gift } from 'lucide-react'
import toast from 'react-hot-toast'
import useAuth from '../hooks/useAuth'

export default function Register() {
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const attribution = useMemo(() => ({
    ref: searchParams.get('ref') || undefined,
    partner_code: searchParams.get('partner') || undefined,
    utm_source: searchParams.get('utm_source') || undefined,
    utm_medium: searchParams.get('utm_medium') || undefined,
    utm_campaign: searchParams.get('utm_campaign') || undefined,
  }), [searchParams])

  const refCode = searchParams.get('ref')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.password.length < 6) {
      toast.error('Senha deve ter pelo menos 6 caracteres')
      return
    }
    setLoading(true)
    try {
      await register(form.name, form.email, form.password, attribution)
      toast.success('Conta criada com sucesso!')
      navigate('/dashboard')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Erro ao criar conta')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-slate-100 px-4">
      <div className="card w-full max-w-md p-8">
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-brand-600 rounded-xl flex items-center justify-center">
            <MessageSquare className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-xl text-slate-800">HostFlow</h1>
            <p className="text-xs text-slate-500">Atendimento inteligente</p>
          </div>
        </div>

        {refCode && (
          <div className="flex items-center gap-2 mb-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
            <Gift className="w-4 h-4 shrink-0" />
            <span>Você foi indicado! Crie sua conta e comece com trial estendido.</span>
          </div>
        )}

        <h2 className="text-xl font-semibold text-slate-800 mb-1">Criar conta grátis</h2>
        <p className="text-sm text-slate-500 mb-6">
          Já tem conta?{' '}
          <Link to="/login" className="text-brand-600 hover:underline font-medium">
            Fazer login
          </Link>
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Nome</label>
            <input
              className="input"
              type="text"
              placeholder="Seu nome"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">E-mail</label>
            <input
              className="input"
              type="email"
              placeholder="seu@email.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Senha</label>
            <input
              className="input"
              type="password"
              placeholder="Mínimo 6 caracteres"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
              minLength={6}
            />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={loading}>
            {loading ? 'Criando conta...' : 'Criar conta grátis'}
          </button>
        </form>

        <p className="text-xs text-slate-400 text-center mt-4">
          Ao se cadastrar, você concorda com os termos de uso.
        </p>
      </div>
    </div>
  )
}
