import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { MessageSquare, ChevronDown, ArrowRight, Shield, CreditCard, RefreshCw } from 'lucide-react'
import PricingCard from '../components/PricingCard'
import PlanComparisonTable from '../components/PlanComparisonTable'
import { PRICING_FAQ } from '../lib/plans'
import { trackEvent, CONVERSION_EVENTS } from '../lib/tracking'

// ── Public nav ─────────────────────────────────────────────────────────────────

function PublicNav() {
  return (
    <header className="border-b border-slate-100 sticky top-0 bg-white/95 backdrop-blur z-50">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
            <MessageSquare className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-slate-800 text-lg">HostFlow</span>
        </Link>
        <nav className="hidden sm:flex items-center gap-6 text-sm text-slate-600">
          <Link to="/" className="hover:text-slate-800 transition-colors">Início</Link>
          <Link to="/pricing" className="text-brand-600 font-medium">Preços</Link>
        </nav>
        <div className="flex items-center gap-3">
          <Link to="/login" className="text-sm text-slate-600 hover:text-slate-800 transition-colors">
            Entrar
          </Link>
          <Link to="/register" className="btn-primary text-sm py-2 px-4">
            Começar grátis
          </Link>
        </div>
      </div>
    </header>
  )
}

// ── FAQ Accordion ──────────────────────────────────────────────────────────────

function FAQItem({ q, a }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border-b border-slate-100 last:border-0">
      <button
        className="w-full text-left py-5 flex items-start justify-between gap-4"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="font-medium text-slate-800 text-sm leading-snug">{q}</span>
        <ChevronDown
          className={`w-4 h-4 text-slate-400 shrink-0 mt-0.5 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <p className="pb-5 text-sm text-slate-500 leading-relaxed -mt-1">{a}</p>
      )}
    </div>
  )
}

// ── Trust signals ──────────────────────────────────────────────────────────────

const TRUST_ITEMS = [
  { icon: Shield,      text: 'Dados criptografados e seguros' },
  { icon: CreditCard,  text: 'Pagamento 100% seguro via Stripe' },
  { icon: RefreshCw,   text: 'Cancele quando quiser, sem multa' },
]

// ── Main page ──────────────────────────────────────────────────────────────────

// Static plan data for public page (no auth needed)
const PUBLIC_PLANS = [
  { planName: 'free',     priceId: null, trialDays: 0  },
  { planName: 'pro',      priceId: null, trialDays: 14 },
  { planName: 'business', priceId: null, trialDays: 0  },
]

export default function PricingPage() {
  const [showTable, setShowTable] = useState(false)

  useEffect(() => {
    trackEvent(CONVERSION_EVENTS.VIEWED_PRICING_PAGE)
  }, [])

  const handlePlanCTA = (planName) => {
    trackEvent(CONVERSION_EVENTS.CLICKED_PLAN_CTA, { plan: planName, source: 'pricing_page' })
  }

  return (
    <div className="min-h-screen bg-white text-slate-800">
      <PublicNav />

      {/* Hero */}
      <section className="pt-16 pb-4 px-6 text-center bg-gradient-to-b from-brand-50 to-white">
        <div className="max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-brand-100 text-brand-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-5">
            14 dias grátis no plano Pro · sem cartão de crédito
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 leading-tight mb-4">
            Planos simples,<br />
            <span className="text-brand-600">sem surpresas</span>
          </h1>
          <p className="text-lg text-slate-500 mb-2 max-w-lg mx-auto">
            Comece grátis. Faça upgrade quando precisar. Cancele quando quiser.
          </p>
        </div>
      </section>

      {/* Plan cards */}
      <section className="py-12 px-6">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 items-start">
            {PUBLIC_PLANS.map(({ planName, priceId, trialDays }) => (
              <div key={planName} onClick={() => handlePlanCTA(planName)}>
                <PricingCard
                  planName={planName}
                  priceId={priceId}
                  mode="public"
                  trialDays={trialDays}
                />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust signals */}
      <section className="py-6 px-6 border-y border-slate-100">
        <div className="max-w-3xl mx-auto flex flex-col sm:flex-row items-center justify-center gap-6">
          {TRUST_ITEMS.map(({ icon: Icon, text }) => (
            <div key={text} className="flex items-center gap-2 text-sm text-slate-500">
              <Icon className="w-4 h-4 text-slate-400 shrink-0" />
              {text}
            </div>
          ))}
        </div>
      </section>

      {/* Comparison table */}
      <section className="py-16 px-6 bg-slate-50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-slate-900 mb-2">
              Compare os planos em detalhe
            </h2>
            <p className="text-slate-500 text-sm">Todos os recursos, lado a lado.</p>
          </div>

          {/* Mobile: toggle */}
          <div className="sm:hidden mb-4 text-center">
            <button
              onClick={() => {
                setShowTable((v) => !v)
                if (!showTable) trackEvent(CONVERSION_EVENTS.CLICKED_COMPARISON)
              }}
              className="text-sm text-brand-600 font-medium underline underline-offset-2"
            >
              {showTable ? 'Ocultar comparativo' : 'Ver comparativo completo'}
            </button>
          </div>

          <div className={`${showTable ? 'block' : 'hidden sm:block'}`}>
            <PlanComparisonTable />
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 px-6 bg-white">
        <div className="max-w-2xl mx-auto">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-slate-900 mb-2">Perguntas frequentes</h2>
            <p className="text-slate-500 text-sm">Tudo que você precisa saber antes de começar.</p>
          </div>
          <div className="bg-white rounded-2xl border border-slate-100 px-6">
            {PRICING_FAQ.map((item) => (
              <FAQItem key={item.q} {...item} />
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="py-16 px-6 bg-brand-600 text-white text-center">
        <div className="max-w-xl mx-auto">
          <h2 className="text-3xl font-bold mb-3">Comece agora, é grátis</h2>
          <p className="text-brand-100 mb-8 text-base">
            Setup em 2 minutos. Trial de 14 dias no plano Pro sem cartão.
          </p>
          <Link
            to="/register"
            onClick={() => handlePlanCTA('pro')}
            className="inline-flex items-center gap-2 bg-white text-brand-700 font-bold py-3 px-8 rounded-xl hover:bg-brand-50 transition-colors text-base"
          >
            Criar conta grátis
            <ArrowRight className="w-4 h-4" />
          </Link>
          <p className="text-brand-200 text-xs mt-4">Sem cartão de crédito · Cancele quando quiser</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-slate-100 bg-white">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-slate-400">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-brand-600 rounded flex items-center justify-center">
              <MessageSquare className="w-3 h-3 text-white" />
            </div>
            <span className="font-semibold text-slate-600">HostFlow</span>
          </div>
          <p>© {new Date().getFullYear()} HostFlow. Feito para hosts brasileiros.</p>
          <div className="flex gap-4">
            <Link to="/privacy" className="hover:text-slate-600 transition-colors">Privacidade</Link>
            <Link to="/terms" className="hover:text-slate-600 transition-colors">Termos</Link>
            <Link to="/contact" className="hover:text-slate-600 transition-colors">Contato</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
