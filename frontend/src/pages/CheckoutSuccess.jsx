import { useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle2, ArrowRight, Inbox, Plug, Zap } from 'lucide-react'
import { trackEvent } from '../lib/tracking'
import { CONVERSION_EVENTS, PLAN_META } from '../lib/plans'

const NEXT_STEPS = [
  {
    icon: Plug,
    title: 'Conectar Gmail ou WhatsApp',
    description: 'Receba e responda mensagens de hóspedes direto no HostFlow.',
    href: '/integrations',
    cta: 'Conectar integrações',
  },
  {
    icon: Inbox,
    title: 'Ver sua caixa de entrada',
    description: 'Todas as conversas organizadas em um só lugar.',
    href: '/inbox',
    cta: 'Abrir caixa de entrada',
  },
  {
    icon: Zap,
    title: 'Configurar auto-envio',
    description: 'Deixe a IA responder automaticamente com suas regras.',
    href: '/auto-send',
    cta: 'Configurar auto-envio',
  },
]

export default function CheckoutSuccess() {
  const [searchParams] = useSearchParams()
  const planName = searchParams.get('plan') || 'pro'
  const meta = PLAN_META[planName] || PLAN_META.pro

  useEffect(() => {
    trackEvent(CONVERSION_EVENTS.VIEWED_SUCCESS_PAGE, { plan: planName })
    trackEvent(CONVERSION_EVENTS.CHECKOUT_COMPLETED, { plan: planName })
  }, [planName])

  return (
    <div className="min-h-screen bg-gradient-to-b from-brand-50 to-white flex flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-lg text-center">

        {/* Success icon */}
        <div className="flex justify-center mb-6">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
            <CheckCircle2 className="w-10 h-10 text-green-500" />
          </div>
        </div>

        {/* Headline */}
        <h1 className="text-3xl font-extrabold text-slate-900 mb-2">
          Bem-vindo ao plano {meta.displayName}!
        </h1>
        <p className="text-slate-500 text-base mb-8 leading-relaxed">
          Sua assinatura foi ativada com sucesso. Agora você tem acesso a todos os recursos{' '}
          <span className="font-semibold text-slate-700">{meta.displayName}</span>.
        </p>

        {/* Next steps */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 mb-6 text-left">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">
            Próximos passos recomendados
          </p>
          <div className="space-y-4">
            {NEXT_STEPS.map(({ icon: Icon, title, description, href, cta }) => (
              <div key={href} className="flex items-start gap-4">
                <div className="w-9 h-9 bg-brand-50 rounded-xl flex items-center justify-center shrink-0 mt-0.5">
                  <Icon className="w-4 h-4 text-brand-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-slate-800 text-sm">{title}</p>
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{description}</p>
                </div>
                <Link
                  to={href}
                  className="text-xs text-brand-600 font-semibold hover:underline shrink-0 mt-0.5"
                >
                  {cta}
                </Link>
              </div>
            ))}
          </div>
        </div>

        {/* Primary CTA */}
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 bg-brand-600 text-white font-bold py-3 px-8 rounded-xl hover:bg-brand-700 transition-colors text-sm"
        >
          Ir para o dashboard
          <ArrowRight className="w-4 h-4" />
        </Link>

        <p className="text-xs text-slate-400 mt-4">
          Dúvidas?{' '}
          <Link to="/contact" className="underline hover:text-slate-600">
            Fale com a gente
          </Link>
        </p>
      </div>
    </div>
  )
}
