import { useEffect, useState, useCallback } from 'react'
import {
  Search, Filter, Download, RefreshCw, ChevronLeft, ChevronRight,
  ChevronUp, ChevronDown, Users
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'
import Layout from '../components/Layout'
import PlanBadge from '../components/PlanBadge'
import UserDetailDrawer from '../components/UserDetailDrawer'
import clsx from 'clsx'

// ── Status badge ─────────────────────────────────────────────────────────────

const STATUS_STYLES = {
  active:   'bg-green-100 text-green-700',
  trialing: 'bg-brand-100 text-brand-700',
  free:     'bg-slate-100 text-slate-600',
  past_due: 'bg-orange-100 text-orange-700',
  canceled: 'bg-red-100 text-red-600',
  unpaid:   'bg-red-100 text-red-600',
}
const STATUS_LABELS = {
  active:   'Ativo',
  trialing: 'Trial',
  free:     'Free',
  past_due: 'Pendente',
  canceled: 'Cancelado',
  unpaid:   'Não pago',
}

function StatusBadge({ status }) {
  return (
    <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full', STATUS_STYLES[status] || STATUS_STYLES.free)}>
      {STATUS_LABELS[status] || status}
    </span>
  )
}

// ── Risk badge ────────────────────────────────────────────────────────────────

const RISK_STYLES = {
  low:    'bg-green-100 text-green-700',
  medium: 'bg-yellow-100 text-yellow-700',
  high:   'bg-red-100 text-red-600',
}
const RISK_LABELS = { low: 'Baixo', medium: 'Médio', high: 'Alto' }

function RiskBadge({ risk }) {
  return (
    <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full', RISK_STYLES[risk] || RISK_STYLES.low)}>
      {RISK_LABELS[risk] || risk}
    </span>
  )
}

// ── Health bar ────────────────────────────────────────────────────────────────

function HealthBar({ score }) {
  const color = score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-yellow-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={clsx('h-full rounded-full', color)} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs text-slate-500 w-6 text-right">{score}</span>
    </div>
  )
}

// ── Sort header ───────────────────────────────────────────────────────────────

function SortTh({ label, field, sortBy, sortDir, onSort }) {
  const active = sortBy === field
  return (
    <th
      className="pb-2 pr-4 text-left text-xs text-slate-500 font-medium cursor-pointer select-none hover:text-slate-700"
      onClick={() => onSort(field)}
    >
      <span className="flex items-center gap-1">
        {label}
        {active
          ? sortDir === 'desc'
            ? <ChevronDown className="w-3 h-3" />
            : <ChevronUp className="w-3 h-3" />
          : null}
      </span>
    </th>
  )
}

// ── Export helper ─────────────────────────────────────────────────────────────

async function downloadCsv(segment) {
  try {
    const res = await api.get(`/admin/users/export/${segment}`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `hostflow_users_${segment}.csv`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    toast.error('Erro ao exportar CSV')
  }
}

// ── Page ──────────────────────────────────────────────────────────────────────

const EXPORT_OPTIONS = [
  { label: 'Todos', segment: 'all' },
  { label: 'Em trial', segment: 'trial' },
  { label: 'Pagantes', segment: 'paying' },
  { label: 'Cancelados', segment: 'canceled' },
  { label: 'Pag. pendente', segment: 'past_due' },
  { label: 'Alto risco', segment: 'high_risk' },
]

export default function AdminUsers() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [planFilter, setPlanFilter] = useState('')
  const [riskFilter, setRiskFilter] = useState('')
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState('created_at')
  const [sortDir, setSortDir] = useState('desc')
  const [selectedUser, setSelectedUser] = useState(null)
  const [showExportMenu, setShowExportMenu] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page,
        page_size: 25,
        sort_by: sortBy,
        sort_dir: sortDir,
      })
      if (search) params.set('search', search)
      if (statusFilter) params.set('status', statusFilter)
      if (planFilter) params.set('plan', planFilter)
      if (riskFilter) params.set('churn_risk', riskFilter)

      const { data: res } = await api.get(`/admin/users?${params}`)
      setData(res)
    } catch (err) {
      if (err.response?.status === 403) {
        toast.error('Acesso restrito a administradores')
      } else {
        toast.error('Erro ao carregar usuários')
      }
    } finally {
      setLoading(false)
    }
  }, [page, sortBy, sortDir, search, statusFilter, planFilter, riskFilter])

  useEffect(() => { load() }, [load])

  const handleSearch = (e) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  const handleSort = (field) => {
    if (sortBy === field) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortBy(field); setSortDir('desc') }
    setPage(1)
  }

  const fmt = (dt) => dt ? new Date(dt).toLocaleDateString('pt-BR') : '—'

  return (
    <Layout>
      <div className="max-w-full">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">CRM de Usuários</h1>
            <p className="text-slate-500 text-sm mt-1">
              {data ? `${data.total} usuários encontrados` : 'Carregando...'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={load} className="text-slate-400 hover:text-slate-600 p-2">
              <RefreshCw className="w-4 h-4" />
            </button>
            <div className="relative">
              <button
                onClick={() => setShowExportMenu(m => !m)}
                className="btn-secondary text-sm flex items-center gap-2"
              >
                <Download className="w-4 h-4" /> Exportar CSV
              </button>
              {showExportMenu && (
                <div className="absolute right-0 top-10 z-50 bg-white border border-slate-200 rounded-lg shadow-lg py-1 min-w-40">
                  {EXPORT_OPTIONS.map(({ label, segment }) => (
                    <button
                      key={segment}
                      onClick={() => { downloadCsv(segment); setShowExportMenu(false) }}
                      className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="card p-4 mb-5">
          <div className="flex flex-wrap gap-3 items-end">
            {/* Search */}
            <form onSubmit={handleSearch} className="flex gap-2 flex-1 min-w-48">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  className="input pl-9 text-sm"
                  placeholder="Buscar por nome ou e-mail..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                />
              </div>
              <button type="submit" className="btn-primary text-sm py-2">Buscar</button>
            </form>

            {/* Status filter */}
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
              className="input text-sm w-40"
            >
              <option value="">Todos os status</option>
              <option value="active">Ativo</option>
              <option value="trialing">Trial</option>
              <option value="free">Free</option>
              <option value="past_due">Pag. pendente</option>
              <option value="canceled">Cancelado</option>
            </select>

            {/* Plan filter */}
            <select
              value={planFilter}
              onChange={(e) => { setPlanFilter(e.target.value); setPage(1) }}
              className="input text-sm w-36"
            >
              <option value="">Todos os planos</option>
              <option value="free">Free</option>
              <option value="pro">Pro</option>
              <option value="business">Business</option>
            </select>

            {/* Risk filter */}
            <select
              value={riskFilter}
              onChange={(e) => { setRiskFilter(e.target.value); setPage(1) }}
              className="input text-sm w-36"
            >
              <option value="">Todo risco</option>
              <option value="high">Alto risco</option>
              <option value="medium">Risco médio</option>
              <option value="low">Baixo risco</option>
            </select>

            {(search || statusFilter || planFilter || riskFilter) && (
              <button
                onClick={() => {
                  setSearch(''); setSearchInput(''); setStatusFilter('')
                  setPlanFilter(''); setRiskFilter(''); setPage(1)
                }}
                className="text-sm text-slate-500 hover:text-slate-700"
              >
                Limpar filtros
              </button>
            )}
          </div>
        </div>

        {/* Table */}
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-100">
                <tr>
                  <SortTh label="Usuário" field="name" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                  <SortTh label="Plano" field="plan" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                  <SortTh label="Status" field="subscription_status" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                  <th className="pb-2 pr-4 text-left text-xs text-slate-500 font-medium">Saúde</th>
                  <th className="pb-2 pr-4 text-left text-xs text-slate-500 font-medium">Risco</th>
                  <th className="pb-2 pr-4 text-left text-xs text-slate-500 font-medium">IA/mês</th>
                  <th className="pb-2 pr-4 text-left text-xs text-slate-500 font-medium">Imóveis</th>
                  <SortTh label="Cadastro" field="created_at" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                  <SortTh label="Último login" field="last_login_at" sortBy={sortBy} sortDir={sortDir} onSort={handleSort} />
                  <th className="pb-2 text-left text-xs text-slate-500 font-medium">Ação</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr><td colSpan={10} className="py-12 text-center text-slate-400 text-sm">Carregando...</td></tr>
                ) : !data?.items.length ? (
                  <tr><td colSpan={10} className="py-12 text-center text-slate-400 text-sm">Nenhum usuário encontrado</td></tr>
                ) : (
                  data.items.map(user => (
                    <tr
                      key={user.id}
                      className="border-b border-slate-50 hover:bg-slate-50 cursor-pointer"
                      onClick={() => setSelectedUser(user)}
                    >
                      <td className="py-3 pr-4">
                        <div>
                          <p className="font-medium text-slate-800 truncate max-w-40">{user.name}</p>
                          <p className="text-xs text-slate-400 truncate max-w-40">{user.email}</p>
                        </div>
                      </td>
                      <td className="py-3 pr-4"><PlanBadge plan={user.effective_plan} /></td>
                      <td className="py-3 pr-4"><StatusBadge status={user.subscription_status} /></td>
                      <td className="py-3 pr-4"><HealthBar score={user.health_score} /></td>
                      <td className="py-3 pr-4"><RiskBadge risk={user.churn_risk} /></td>
                      <td className="py-3 pr-4 text-slate-600">{user.ai_responses_month}</td>
                      <td className="py-3 pr-4 text-slate-600">{user.properties_count}</td>
                      <td className="py-3 pr-4 text-slate-500 text-xs">{fmt(user.created_at)}</td>
                      <td className="py-3 pr-4 text-slate-500 text-xs">{fmt(user.last_login_at)}</td>
                      <td className="py-3 max-w-44">
                        <p className="text-xs text-slate-500 line-clamp-2">{user.recommended_action}</p>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
              <p className="text-xs text-slate-400">
                Página {data.page} de {data.pages} · {data.total} usuários
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="p-1.5 rounded text-slate-500 hover:bg-slate-100 disabled:opacity-40"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPage(p => Math.min(data.pages, p + 1))}
                  disabled={page >= data.pages}
                  className="p-1.5 rounded text-slate-500 hover:bg-slate-100 disabled:opacity-40"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Detail drawer */}
      {selectedUser && (
        <UserDetailDrawer
          userId={selectedUser.id}
          onClose={() => setSelectedUser(null)}
        />
      )}
    </Layout>
  )
}
