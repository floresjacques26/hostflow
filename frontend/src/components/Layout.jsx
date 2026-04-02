import { useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { MessageSquare, Calculator, FileText, LogOut, Home, Building2, CreditCard, Zap, ShieldAlert, Users, Inbox, Plug, SendHorizonal, Clock, AlertCircle } from 'lucide-react'
import useAuth from '../hooks/useAuth'
import useBilling from '../hooks/useBilling'
import PlanBadge from './PlanBadge'
import OnboardingChecklist from './OnboardingChecklist'
import clsx from 'clsx'

/**
 * Calculates how many days remain until a given ISO date string.
 * Returns 0 if the date is in the past.
 */
function daysUntil(isoDate) {
  if (!isoDate) return null
  const ms = new Date(isoDate) - Date.now()
  return Math.max(0, Math.ceil(ms / (1000 * 60 * 60 * 24)))
}

/**
 * Smart sidebar upsell banner — shows the most relevant nudge for the user's
 * current state. Only one banner visible at a time, priority order:
 *   1. Trial ending (≤ 3 days left)  → urgent CTA
 *   2. AI usage ≥ 80%                → usage warning
 *   3. Trial active (> 3 days left)  → soft reminder
 *   4. Free plan                     → value nudge (shown periodically)
 */
function SidebarBanner({ subscription, usage }) {
  if (!subscription) return null

  const { is_trial_active, trial_ends_at, subscription_status, effective_plan } = subscription
  const daysLeft = daysUntil(trial_ends_at)
  const aiPct = usage && usage.ai_responses_limit
    ? Math.round((usage.ai_responses / usage.ai_responses_limit) * 100)
    : 0

  // 1. Trial expiring soon
  if (is_trial_active && daysLeft !== null && daysLeft <= 3) {
    return (
      <div className="mx-3 mb-2">
        <Link
          to="/billing"
          className="block p-3 bg-orange-50 border border-orange-200 rounded-lg text-xs text-orange-800 hover:bg-orange-100 transition-colors"
        >
          <div className="flex items-center gap-1.5 font-bold mb-0.5">
            <Clock className="w-3 h-3" />
            {daysLeft === 0 ? 'Trial expira hoje!' : `Trial expira em ${daysLeft} dia${daysLeft > 1 ? 's' : ''}!`}
          </div>
          <p className="text-orange-700">Assine agora para manter o acesso Pro.</p>
        </Link>
      </div>
    )
  }

  // 2. AI limit ≥ 80%
  if (aiPct >= 80 && effective_plan === 'free') {
    return (
      <div className="mx-3 mb-2">
        <Link
          to="/billing"
          className="block p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 hover:bg-amber-100 transition-colors"
        >
          <div className="flex items-center gap-1.5 font-bold mb-0.5">
            <AlertCircle className="w-3 h-3" />
            {aiPct >= 100 ? 'Limite de IA atingido' : `${aiPct}% do limite de IA usado`}
          </div>
          <p className="text-amber-700">
            {aiPct >= 100 ? 'Faça upgrade para continuar.' : 'Quase no limite. Considere o upgrade Pro.'}
          </p>
        </Link>
      </div>
    )
  }

  // 3. Trial active (> 3 days left)
  if (is_trial_active) {
    return (
      <div className="mx-3 mb-2">
        <Link
          to="/billing"
          className="block p-3 bg-brand-50 border border-brand-200 rounded-lg text-xs text-brand-700 hover:bg-brand-100 transition-colors"
        >
          <div className="flex items-center gap-1.5 font-semibold mb-0.5">
            <Zap className="w-3 h-3" /> Trial Pro ativo
          </div>
          {daysLeft !== null && (
            <p className="text-brand-600">{daysLeft} dias restantes · assine para continuar</p>
          )}
        </Link>
      </div>
    )
  }

  // 4. Free plan — quiet nudge
  if (subscription_status === 'free' && effective_plan === 'free') {
    return (
      <div className="mx-3 mb-2">
        <Link
          to="/billing"
          className="block p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600 hover:bg-slate-100 transition-colors"
        >
          <div className="flex items-center gap-1.5 font-semibold mb-0.5">
            <Zap className="w-3 h-3" /> Upgrade para Pro
          </div>
          <p>Gmail, WhatsApp e respostas ilimitadas.</p>
        </Link>
      </div>
    )
  }

  return null
}

const navItems = [
  { to: '/dashboard', icon: Home, label: 'Dashboard' },
  { to: '/inbox', icon: Inbox, label: 'Caixa de entrada' },
  { to: '/properties', icon: Building2, label: 'Imóveis' },
  { to: '/calculator', icon: Calculator, label: 'Calculadora' },
  { to: '/templates', icon: FileText, label: 'Templates' },
  { to: '/integrations', icon: Plug, label: 'Integrações' },
  { to: '/auto-send', icon: SendHorizonal, label: 'Auto-envio' },
  { to: '/billing', icon: CreditCard, label: 'Assinatura' },
]

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const { subscription, usage, loaded, fetchAll } = useBilling()
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(() => {
    if (!loaded) fetchAll().catch(() => {})
  }, [loaded, fetchAll])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const isTrialActive = subscription?.is_trial_active

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-slate-200 flex flex-col fixed h-full">
        <div className="p-5 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-slate-800 text-lg">HostFlow</span>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <Link
              key={to}
              to={to}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                location.pathname === to
                  ? 'bg-brand-50 text-brand-700'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-800'
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          ))}
        </nav>

        {/* Sidebar upsell banners */}
        {location.pathname !== '/billing' && (
          <SidebarBanner subscription={subscription} usage={usage} />
        )}

        {/* Admin section — only visible to admins */}
        {user?.is_admin && (
          <div className="px-3 pb-2">
            <p className="px-3 pt-1 pb-1.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Admin
            </p>
            {[
              { to: '/admin', icon: ShieldAlert, label: 'Dashboard' },
              { to: '/admin/users', icon: Users, label: 'CRM Usuários' },
            ].map(({ to, icon: Icon, label }) => (
              <Link
                key={to}
                to={to}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                  location.pathname === to
                    ? 'bg-purple-50 text-purple-700'
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                )}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            ))}
          </div>
        )}

        <div className="p-3 border-t border-slate-100">
          <div className="px-3 py-2 mb-1">
            <p className="text-xs font-medium text-slate-800 truncate">{user?.name}</p>
            <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            <div className="mt-1">
              <PlanBadge plan={subscription?.effective_plan || user?.plan || 'free'} />
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-600 hover:bg-slate-50 hover:text-red-600 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sair
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 ml-56 p-8 min-h-screen">
        {children}
      </main>

      <OnboardingChecklist />
    </div>
  )
}
