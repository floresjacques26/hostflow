import { useState, useEffect, useCallback } from 'react'
import {
  Mail, CheckCircle2, XCircle, RefreshCw, Unlink, ExternalLink,
  Clock, AlertTriangle, Zap, Plus, Copy, Eye, EyeOff, Send,
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import Layout from '../components/Layout'
import clsx from 'clsx'

// ── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(isoStr) {
  if (!isoStr) return null
  const diff = Date.now() - new Date(isoStr).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'agora mesmo'
  if (m < 60) return `há ${m}min`
  const h = Math.floor(m / 60)
  if (h < 24) return `há ${h}h`
  return `há ${Math.floor(h / 24)}d`
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => toast.success('Copiado!'))
}

const WA_STATUS_CFG = {
  connected:            { label: 'Conectado',          color: 'bg-green-100 text-green-700' },
  pending_verification: { label: 'Aguardando webhook', color: 'bg-amber-100 text-amber-700' },
  error:                { label: 'Erro',               color: 'bg-red-100 text-red-700' },
  disconnected:         { label: 'Desconectado',       color: 'bg-slate-100 text-slate-500' },
}

// ── WhatsApp SVG icon ─────────────────────────────────────────────────────────

function WhatsAppIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
    </svg>
  )
}

// ── Gmail card ────────────────────────────────────────────────────────────────

function GmailCard() {
  const [status, setStatus] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/gmail/status')
      setStatus(data)
    } catch {
      setStatus({ connected: false })
    }
  }, [])

  useEffect(() => {
    load()
    const params = new URLSearchParams(window.location.search)
    if (params.get('gmail_connected') === '1') {
      toast.success('Gmail conectado com sucesso!')
      window.history.replaceState({}, '', '/integrations')
    }
    if (params.get('gmail_error')) {
      toast.error(`Erro ao conectar Gmail: ${params.get('gmail_error')}`)
      window.history.replaceState({}, '', '/integrations')
    }
  }, [load])

  const handleConnect = async () => {
    try {
      const { data } = await api.get('/gmail/auth')
      window.location.href = data.auth_url
    } catch {
      toast.error('Erro ao iniciar conexão com Gmail')
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      const { data } = await api.post('/gmail/sync')
      toast.success(`Sincronizado! ${data.threads_processed} threads, ${data.new_entries} novas.`)
      await load()
    } catch {
      toast.error('Erro ao sincronizar Gmail')
    } finally {
      setSyncing(false)
    }
  }

  const handleDisconnect = async () => {
    if (!window.confirm('Desconectar Gmail? As conversas existentes serão mantidas.')) return
    setDisconnecting(true)
    try {
      await api.delete('/gmail/disconnect')
      toast.success('Gmail desconectado.')
      setStatus({ connected: false })
    } catch {
      toast.error('Erro ao desconectar Gmail')
    } finally {
      setDisconnecting(false)
    }
  }

  const isLoading = status === null

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
      <div className="px-6 py-5 border-b border-slate-100 flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center shrink-0">
          <Mail className="w-5 h-5 text-red-500" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-800">Gmail</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Sincronize e responda e-mails de hóspedes diretamente no HostFlow
          </p>
        </div>
        {!isLoading && (
          <span className={clsx(
            'inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full shrink-0',
            status?.connected ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-500',
          )}>
            {status?.connected
              ? <><CheckCircle2 className="w-3.5 h-3.5" /> Conectado</>
              : <><XCircle className="w-3.5 h-3.5" /> Desconectado</>}
          </span>
        )}
      </div>

      <div className="px-6 py-5">
        {isLoading ? (
          <div className="h-16 flex items-center justify-center text-slate-400 text-sm">Carregando...</div>
        ) : status?.connected ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
              <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center shrink-0">
                <Mail className="w-4 h-4 text-red-500" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-800 truncate">{status.gmail_email}</p>
                <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                  <Clock className="w-3 h-3" />
                  {status.last_sync_at ? `Última sincronização: ${timeAgo(status.last_sync_at)}` : 'Nunca sincronizado'}
                </p>
              </div>
            </div>
            {status.sync_error && (
              <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>{status.sync_error}</span>
              </div>
            )}
            <div className="flex items-center gap-2 flex-wrap">
              <button onClick={handleSync} disabled={syncing}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors disabled:opacity-50">
                <RefreshCw className={clsx('w-4 h-4', syncing && 'animate-spin')} />
                {syncing ? 'Sincronizando...' : 'Sincronizar agora'}
              </button>
              <button onClick={handleDisconnect} disabled={disconnecting}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-600 text-sm font-medium hover:bg-red-50 hover:text-red-700 hover:border-red-200 transition-colors disabled:opacity-50">
                <Unlink className="w-4 h-4" />
                {disconnecting ? 'Desconectando...' : 'Desconectar'}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-slate-600 leading-relaxed">
              Conecte sua conta do Gmail para que o HostFlow sincronize automaticamente as mensagens de hóspedes.
            </p>
            <button onClick={handleConnect}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors">
              <ExternalLink className="w-4 h-4" />
              Conectar Gmail
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── WhatsApp card ─────────────────────────────────────────────────────────────

function WhatsAppCard() {
  const [status, setStatus] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [showToken, setShowToken] = useState(false)
  const [testing, setTesting] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    phone_number: '',
    phone_number_id: '',
    access_token: '',
    business_account_id: '',
  })

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/whatsapp/status')
      setStatus(data)
    } catch {
      setStatus({ connected: false, status: 'disconnected' })
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleSave = async (e) => {
    e.preventDefault()
    if (!form.phone_number || !form.phone_number_id || !form.access_token) {
      toast.error('Preencha número, Phone Number ID e token de acesso')
      return
    }
    setSaving(true)
    try {
      const { data } = await api.post('/whatsapp/connect', form)
      setStatus(data)
      setShowForm(false)
      toast.success('WhatsApp configurado! Configure o webhook conforme as instruções abaixo.')
    } catch (err) {
      toast.error(err.response?.data?.detail ?? 'Erro ao salvar configuração WhatsApp')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    try {
      const { data } = await api.post('/whatsapp/test', {
        body: '✅ HostFlow WhatsApp conectado com sucesso! Esta é uma mensagem de teste.',
      })
      toast.success(`Mensagem de teste enviada para ${data.to}`)
      await load()
    } catch (err) {
      toast.error(err.response?.data?.detail ?? 'Falha no teste — verifique o token e o número')
    } finally {
      setTesting(false)
    }
  }

  const handleDisconnect = async () => {
    if (!window.confirm('Desconectar WhatsApp? As conversas existentes serão mantidas.')) return
    setDisconnecting(true)
    try {
      await api.delete('/whatsapp/disconnect')
      toast.success('WhatsApp desconectado.')
      setStatus({ connected: false, status: 'disconnected' })
      setShowForm(false)
    } catch {
      toast.error('Erro ao desconectar')
    } finally {
      setDisconnecting(false)
    }
  }

  const isLoading = status === null
  const isConfigured = status && status.status && status.status !== 'disconnected'
  const statusCfg = WA_STATUS_CFG[status?.status] ?? WA_STATUS_CFG.disconnected

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-5 border-b border-slate-100 flex items-center gap-4">
        <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center shrink-0">
          <WhatsAppIcon className="w-5 h-5 text-green-600" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-800">WhatsApp Business</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Receba e responda mensagens WhatsApp dos hóspedes na caixa de entrada unificada
          </p>
        </div>
        {!isLoading && (
          <span className={clsx('inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full shrink-0', statusCfg.color)}>
            {statusCfg.label}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="px-6 py-5">
        {isLoading ? (
          <div className="h-16 flex items-center justify-center text-slate-400 text-sm">Carregando...</div>
        ) : isConfigured ? (
          <div className="space-y-4">
            {/* Account info */}
            <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl">
              <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center shrink-0">
                <WhatsAppIcon className="w-4 h-4 text-green-600" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800">{status.phone_number}</p>
                <p className="text-xs text-slate-500">
                  ID: {status.phone_number_id} · {status.provider?.toUpperCase() ?? 'META'}
                </p>
              </div>
            </div>

            {/* Error */}
            {status.last_error && (
              <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700">
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>{status.last_error}</span>
              </div>
            )}

            {/* Webhook config (shown when pending verification or always for reference) */}
            {status.status === 'pending_verification' && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-3">
                <p className="text-xs font-semibold text-amber-800 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Configure o webhook no Meta App Dashboard para ativar
                </p>
                <div className="space-y-2">
                  <div>
                    <p className="text-xs text-amber-700 mb-1">URL do Webhook</p>
                    <div className="flex items-center gap-2">
                      <code className="text-xs bg-white border border-amber-200 rounded px-2 py-1 flex-1 truncate">
                        {status.webhook_url}
                      </code>
                      <button onClick={() => copyToClipboard(status.webhook_url)}
                        className="p-1.5 hover:bg-amber-100 rounded text-amber-700">
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-amber-700 mb-1">Token de Verificação</p>
                    <div className="flex items-center gap-2">
                      <code className="text-xs bg-white border border-amber-200 rounded px-2 py-1 flex-1 truncate">
                        {status.webhook_verify_token}
                      </code>
                      <button onClick={() => copyToClipboard(status.webhook_verify_token)}
                        className="p-1.5 hover:bg-amber-100 rounded text-amber-700">
                        <Copy className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <p className="text-xs text-amber-600">
                    No Meta App Dashboard → WhatsApp → Configuração → Webhooks: assine o campo <strong>messages</strong>.
                  </p>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex items-center gap-2 flex-wrap">
              <button onClick={handleTest} disabled={testing}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-green-600 text-white text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-50">
                <Send className={clsx('w-4 h-4', testing && 'animate-pulse')} />
                {testing ? 'Enviando...' : 'Enviar teste'}
              </button>
              <button onClick={() => setShowForm(v => !v)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-600 text-sm font-medium hover:bg-slate-50 transition-colors">
                Editar configuração
              </button>
              <button onClick={handleDisconnect} disabled={disconnecting}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-600 text-sm font-medium hover:bg-red-50 hover:text-red-700 hover:border-red-200 transition-colors disabled:opacity-50">
                <Unlink className="w-4 h-4" />
                {disconnecting ? 'Removendo...' : 'Remover'}
              </button>
            </div>

            {/* Connected feature list */}
            {status.status === 'connected' && (
              <div className="pt-2 border-t border-slate-100">
                <ul className="space-y-1 text-xs text-slate-600">
                  {[
                    'Mensagens recebidas automaticamente via webhook',
                    'Contexto detectado por IA para cada conversa',
                    'Rascunhos automáticos para respostas rápidas',
                    'Histórico de entrega (enviado → lido)',
                  ].map(item => (
                    <li key={item} className="flex items-start gap-2">
                      <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : (
          /* Not configured at all */
          <div className="space-y-4">
            <p className="text-sm text-slate-600 leading-relaxed">
              Conecte sua conta do <strong>WhatsApp Business Cloud API</strong> (Meta) para receber e
              responder mensagens de hóspedes diretamente no HostFlow.
            </p>
            <ul className="space-y-1.5 text-sm text-slate-600">
              {[
                'Mensagens recebidas em tempo real via webhook',
                'IA gera rascunhos de resposta automaticamente',
                'Histórico de status: enviado, entregue, lido',
                'Mesma caixa de entrada que Gmail e e-mail',
              ].map(item => (
                <li key={item} className="flex items-start gap-2">
                  <Zap className="w-3.5 h-3.5 text-green-500 shrink-0 mt-0.5" />
                  {item}
                </li>
              ))}
            </ul>
            <p className="text-xs text-slate-400">
              Requer conta no <strong>Meta Business Suite</strong> com WhatsApp Business API habilitada.
            </p>
          </div>
        )}

        {/* Config form — shown when not configured OR when editing */}
        {(showForm || !isConfigured) && (
          <form onSubmit={handleSave} className="mt-5 space-y-3 border-t border-slate-100 pt-5">
            <p className="text-sm font-semibold text-slate-700">
              {isConfigured ? 'Editar configuração' : 'Configurar WhatsApp Business API'}
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Número de telefone (E.164)
                </label>
                <input
                  type="text"
                  placeholder="+5511999990000"
                  value={form.phone_number}
                  onChange={e => setForm(f => ({ ...f, phone_number: e.target.value }))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  Phone Number ID
                </label>
                <input
                  type="text"
                  placeholder="123456789012345"
                  value={form.phone_number_id}
                  onChange={e => setForm(f => ({ ...f, phone_number_id: e.target.value }))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                WABA ID (opcional)
              </label>
              <input
                type="text"
                placeholder="WhatsApp Business Account ID"
                value={form.business_account_id}
                onChange={e => setForm(f => ({ ...f, business_account_id: e.target.value }))}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Token de acesso permanente (System User Token)
              </label>
              <div className="relative">
                <input
                  type={showToken ? 'text' : 'password'}
                  placeholder="EAAxxxxxxxxxxxxxxxxxxxxxxxx"
                  value={form.access_token}
                  onChange={e => setForm(f => ({ ...f, access_token: e.target.value }))}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  required
                />
                <button type="button" onClick={() => setShowToken(v => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600">
                  {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Gerado em Meta Business Suite → Usuários do sistema → Token permanente.
                O token é criptografado antes de ser armazenado.
              </p>
            </div>

            <div className="flex gap-3">
              <button type="submit" disabled={saving}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium">
                {saving ? 'Salvando...' : isConfigured ? 'Salvar alterações' : 'Conectar WhatsApp'}
              </button>
              {isConfigured && (
                <button type="button" onClick={() => setShowForm(false)}
                  className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900">
                  Cancelar
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  )
}

// ── Placeholder card ──────────────────────────────────────────────────────────

function ComingSoonCard({ name, description, icon: Icon, color }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden opacity-60">
      <div className="px-6 py-5 border-b border-slate-100 flex items-center gap-4">
        <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center shrink-0', color)}>
          <Icon className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-slate-800">{name}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{description}</p>
        </div>
        <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 shrink-0">
          Em breve
        </span>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function Integrations() {
  return (
    <Layout>
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-800">Integrações</h1>
          <p className="text-slate-500 mt-1">
            Conecte seus canais de comunicação para centralizar todas as mensagens de hóspedes.
          </p>
        </div>

        <div className="space-y-4">
          <GmailCard />
          <WhatsAppCard />

          <ComingSoonCard
            name="Airbnb Messaging"
            description="Integração nativa com mensagens da plataforma Airbnb"
            icon={({ className }) => (
              <svg className={className} viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.372 0 0 5.373 0 12s5.372 12 12 12 12-5.373 12-12S18.628 0 12 0zm5.27 16.054c-.152.454-.454.83-.832 1.098-.378.265-.823.4-1.334.4-.512 0-.985-.152-1.411-.455l-1.693-1.2-1.697 1.2c-.426.303-.9.455-1.411.455-.512 0-.957-.135-1.335-.4-.378-.267-.68-.644-.83-1.098-.151-.455-.12-.946.09-1.38l1.51-3.195c.24-.512.664-.877 1.168-1.017l.182-.046V6.8c0-.756.615-1.37 1.37-1.37s1.37.614 1.37 1.37v3.616l.183.046c.503.14.928.505 1.168 1.017l1.51 3.194c.21.435.24.926.09 1.381z"/>
              </svg>
            )}
            color="bg-red-500"
          />

          <ComingSoonCard
            name="Booking.com"
            description="Centralize mensagens de hóspedes do Booking.com"
            icon={Plus}
            color="bg-blue-600"
          />
        </div>

        <div className="mt-8 p-5 bg-slate-50 border border-slate-200 rounded-2xl">
          <p className="text-sm font-medium text-slate-700 mb-1">
            Precisa de uma integração específica?
          </p>
          <p className="text-xs text-slate-500">
            Entre em contato com nosso suporte. Priorizamos integrações baseadas na demanda dos usuários.
          </p>
        </div>
      </div>
    </Layout>
  )
}
