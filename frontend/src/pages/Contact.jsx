import { useState } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquare, Mail, Clock, CheckCircle2 } from 'lucide-react'

function PublicLayout({ children }) {
  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-slate-100">
        <div className="max-w-4xl mx-auto px-6 h-16 flex items-center">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-brand-600 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-bold text-slate-800">HostFlow</span>
          </Link>
        </div>
      </header>
      <main className="max-w-2xl mx-auto px-6 py-12">{children}</main>
      <footer className="border-t border-slate-100 py-6 text-center text-sm text-slate-400">
        <div className="flex justify-center gap-6">
          <Link to="/" className="hover:text-slate-600">Início</Link>
          <Link to="/pricing" className="hover:text-slate-600">Preços</Link>
          <Link to="/privacy" className="hover:text-slate-600">Privacidade</Link>
          <Link to="/terms" className="hover:text-slate-600">Termos</Link>
        </div>
      </footer>
    </div>
  )
}

export default function Contact() {
  const [sent, setSent] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', subject: 'suporte', message: '' })
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    // In production, wire this to a backend endpoint or Resend form.
    // For now, simulate a successful submission.
    await new Promise((r) => setTimeout(r, 800))
    setSent(true)
    setSubmitting(false)
  }

  if (sent) {
    return (
      <PublicLayout>
        <div className="text-center py-12">
          <div className="flex justify-center mb-4">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
              <CheckCircle2 className="w-8 h-8 text-green-500" />
            </div>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Mensagem enviada!</h1>
          <p className="text-slate-500 text-sm mb-6">
            Recebemos seu contato. Retornaremos em até 1 dia útil.
          </p>
          <Link to="/" className="text-brand-600 text-sm font-medium hover:underline">
            Voltar para o início
          </Link>
        </div>
      </PublicLayout>
    )
  }

  return (
    <PublicLayout>
      <div>
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Fale com a gente</h1>
        <p className="text-slate-500 text-sm mb-8">
          Tem uma dúvida, problema ou sugestão? Estamos aqui para ajudar.
        </p>

        {/* Contact info */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          <div className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl">
            <Mail className="w-4 h-4 text-brand-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-slate-800">E-mail</p>
              <p className="text-xs text-slate-500">suporte@hostflow.com.br</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-4 bg-slate-50 rounded-xl">
            <Clock className="w-4 h-4 text-brand-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-slate-800">Tempo de resposta</p>
              <p className="text-xs text-slate-500">Até 1 dia útil</p>
            </div>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">Nome</label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="input w-full"
                placeholder="Seu nome"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">E-mail</label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className="input w-full"
                placeholder="seu@email.com"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Assunto</label>
            <select
              value={form.subject}
              onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
              className="input w-full"
            >
              <option value="suporte">Suporte técnico</option>
              <option value="cobranca">Cobrança / pagamento</option>
              <option value="integracao">Integração (Gmail / WhatsApp)</option>
              <option value="feedback">Feedback ou sugestão</option>
              <option value="outro">Outro</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Mensagem</label>
            <textarea
              required
              rows={5}
              value={form.message}
              onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
              className="input w-full resize-none"
              placeholder="Descreva sua dúvida ou problema..."
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full"
          >
            {submitting ? 'Enviando...' : 'Enviar mensagem'}
          </button>
        </form>
      </div>
    </PublicLayout>
  )
}
