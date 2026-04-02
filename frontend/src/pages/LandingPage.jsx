import { Link } from 'react-router-dom'
import { MessageSquare, Clock, Zap, CheckCircle2, Star, ArrowRight, Building2, FileText, Calculator } from 'lucide-react'

const PLANS = [
  {
    name: 'Free',
    price: 'R$ 0',
    period: '/mês',
    description: 'Para quem está começando',
    features: [
      '20 respostas de IA/mês',
      '1 imóvel',
      '3 templates',
      'Calculadora de check-in',
    ],
    cta: 'Começar grátis',
    href: '/register',
    highlight: false,
  },
  {
    name: 'Pro',
    price: 'R$ 49',
    period: '/mês',
    description: 'Para hosts ativos',
    badge: '14 dias grátis',
    features: [
      '500 respostas de IA/mês',
      'Até 5 imóveis',
      'Templates ilimitados',
      'Histórico completo',
      'Suporte prioritário',
    ],
    cta: 'Testar 14 dias grátis',
    href: '/register',
    highlight: true,
  },
  {
    name: 'Business',
    price: 'R$ 129',
    period: '/mês',
    description: 'Para gestoras e multi-hosts',
    features: [
      'Respostas ilimitadas',
      'Imóveis ilimitados',
      'Templates ilimitados',
      'Analytics avançado',
      'Suporte prioritário',
    ],
    cta: 'Falar com vendas',
    href: '/register',
    highlight: false,
  },
]

const HOW_IT_WORKS = [
  {
    step: '1',
    icon: MessageSquare,
    title: 'Cole a mensagem do hóspede',
    description: 'Copie qualquer mensagem recebida no Airbnb e cole no HostFlow.',
  },
  {
    step: '2',
    icon: Zap,
    title: 'IA gera a resposta',
    description: 'Em segundos, nossa IA cria uma resposta profissional com as regras do seu imóvel.',
  },
  {
    step: '3',
    icon: CheckCircle2,
    title: 'Copie e envie',
    description: 'Revise, copie e envie de volta ao hóspede. Simples assim.',
  },
]

const BEFORE_AFTER = [
  {
    before: 'Passa 15 minutos pensando como responder cada mensagem',
    after: 'Resposta profissional em menos de 30 segundos',
  },
  {
    before: 'Esquece de mencionar políticas importantes (pets, check-in, etc)',
    after: 'IA sempre inclui as regras corretas do imóvel automaticamente',
  },
  {
    before: 'Tom inconsistente dependendo do humor do dia',
    after: 'Comunicação sempre profissional e amigável',
  },
  {
    before: 'Sem histórico — precisa recontar o mesmo contexto',
    after: 'Histórico completo de todas as conversas por imóvel',
  },
]

const TESTIMONIALS = [
  {
    name: 'Ana L.',
    role: 'Host com 3 imóveis em SP',
    text: 'Economizo pelo menos 1 hora por dia com o HostFlow. As respostas ficam muito mais profissionais do que as que eu escrevia.',
    stars: 5,
  },
  {
    name: 'Carlos M.',
    role: 'Gestora de 8 propriedades no RJ',
    text: 'Finalmente consigo manter a qualidade das respostas mesmo com volume alto de mensagens. Indispensável.',
    stars: 5,
  },
  {
    name: 'Fernanda R.',
    role: 'Superhost em Florianópolis',
    text: 'A calculadora de check-in antecipado/tardio me poupou várias discussões de preço com hóspedes.',
    stars: 5,
  },
]

function Stars({ count }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: count }).map((_, i) => (
        <Star key={i} className="w-3.5 h-3.5 text-yellow-400 fill-yellow-400" />
      ))}
    </div>
  )
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-slate-800">
      {/* Nav */}
      <header className="border-b border-slate-100 sticky top-0 bg-white/95 backdrop-blur z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
              <MessageSquare className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-slate-800 text-lg">HostFlow</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/pricing" className="hidden sm:inline text-sm text-slate-600 hover:text-slate-800 transition-colors">
              Preços
            </Link>
            <Link to="/login" className="text-sm text-slate-600 hover:text-slate-800 transition-colors">
              Entrar
            </Link>
            <Link
              to="/register"
              className="btn-primary text-sm py-2 px-4"
            >
              Começar grátis
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="py-20 px-6 text-center bg-gradient-to-b from-brand-50 to-white">
        <div className="max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-brand-100 text-brand-700 text-xs font-semibold px-3 py-1.5 rounded-full mb-6">
            <Zap className="w-3 h-3" />
            Teste grátis por 14 dias no plano Pro
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 leading-tight mb-5">
            Responda hóspedes do Airbnb{' '}
            <span className="text-brand-600">10x mais rápido</span>{' '}
            com IA
          </h1>
          <p className="text-lg text-slate-500 mb-8 max-w-xl mx-auto">
            Pare de perder tempo escrevendo as mesmas respostas. HostFlow usa IA para gerar mensagens profissionais em segundos, com as regras do seu imóvel.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/register"
              className="btn-primary text-base py-3 px-8 flex items-center gap-2"
            >
              Começar grátis
              <ArrowRight className="w-4 h-4" />
            </Link>
            <p className="text-sm text-slate-400">Sem cartão de crédito</p>
          </div>
          <div className="flex items-center justify-center gap-6 mt-10 text-sm text-slate-500">
            <div className="flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-green-500" />
              <span>2 min economizados por resposta</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Building2 className="w-4 h-4 text-brand-500" />
              <span>Multi-imóvel</span>
            </div>
            <div className="flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-purple-500" />
              <span>Templates personalizados</span>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">Como funciona</h2>
            <p className="text-slate-500">Três passos simples, zero complicação.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
            {HOW_IT_WORKS.map(({ step, icon: Icon, title, description }) => (
              <div key={step} className="text-center">
                <div className="w-12 h-12 bg-brand-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Icon className="w-6 h-6 text-brand-600" />
                </div>
                <div className="text-xs font-bold text-brand-400 mb-1">PASSO {step}</div>
                <h3 className="font-semibold text-slate-800 mb-2">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Before / After */}
      <section className="py-20 px-6 bg-slate-50">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">Antes vs. depois</h2>
            <p className="text-slate-500">Veja o que muda no dia a dia de um host.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-2xl bg-red-50 border border-red-100 p-6">
              <p className="text-xs font-bold text-red-400 mb-4 uppercase tracking-wide">Sem HostFlow</p>
              <div className="space-y-3">
                {BEFORE_AFTER.map(({ before }, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <span className="text-red-400 text-lg leading-none mt-0.5">✕</span>
                    <p className="text-sm text-red-700">{before}</p>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-2xl bg-green-50 border border-green-100 p-6">
              <p className="text-xs font-bold text-green-500 mb-4 uppercase tracking-wide">Com HostFlow</p>
              <div className="space-y-3">
                {BEFORE_AFTER.map(({ after }, i) => (
                  <div key={i} className="flex items-start gap-3">
                    <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0 mt-0.5" />
                    <p className="text-sm text-green-800">{after}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features grid */}
      <section className="py-20 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">Tudo que um host precisa</h2>
            <p className="text-slate-500">Ferramentas práticas para o dia a dia de anfitriões.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {[
              {
                icon: MessageSquare,
                color: 'brand',
                title: 'Respostas com IA',
                description: 'Geração automática de mensagens profissionais com contexto do imóvel: check-in, reclamações, dúvidas, cobranças e mais.',
              },
              {
                icon: Building2,
                color: 'purple',
                title: 'Multi-imóvel',
                description: 'Gerencie vários imóveis com regras próprias (horários, preços, pets, estacionamento). A IA sempre usa as regras certas.',
              },
              {
                icon: Calculator,
                color: 'green',
                title: 'Calculadora de check-in',
                description: 'Calcule automaticamente o valor cobrado por check-in antecipado ou check-out tardio com base na sua diária.',
              },
              {
                icon: FileText,
                color: 'orange',
                title: 'Templates',
                description: 'Crie e reutilize templates de mensagens para situações recorrentes. Economize ainda mais tempo.',
              },
              {
                icon: Clock,
                color: 'blue',
                title: 'Histórico completo',
                description: 'Acesse todas as conversas geradas, filtradas por imóvel. Nunca perca o contexto de uma conversa.',
              },
              {
                icon: Zap,
                color: 'brand',
                title: 'Rápido como deve ser',
                description: 'Interface limpa, sem distrações. Cole a mensagem, gere a resposta, copie e envie em menos de 30 segundos.',
              },
            ].map(({ icon: Icon, color, title, description }) => {
              const colorClass = {
                brand: 'bg-brand-50 text-brand-600',
                purple: 'bg-purple-50 text-purple-600',
                green: 'bg-green-50 text-green-600',
                orange: 'bg-orange-50 text-orange-600',
                blue: 'bg-blue-50 text-blue-600',
              }[color]
              return (
                <div key={title} className="p-5 rounded-2xl border border-slate-100 hover:border-brand-100 hover:shadow-sm transition-all">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center mb-4 ${colorClass}`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="font-semibold text-slate-800 mb-2">{title}</h3>
                  <p className="text-sm text-slate-500 leading-relaxed">{description}</p>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Social proof */}
      <section className="py-20 px-6 bg-slate-50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">O que dizem os hosts</h2>
            <p className="text-slate-500">Depoimentos de anfitriões que usam HostFlow no dia a dia.</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {TESTIMONIALS.map(({ name, role, text, stars }) => (
              <div key={name} className="bg-white rounded-2xl border border-slate-100 p-6">
                <Stars count={stars} />
                <p className="text-sm text-slate-600 leading-relaxed mt-3 mb-4">"{text}"</p>
                <div>
                  <p className="text-sm font-semibold text-slate-800">{name}</p>
                  <p className="text-xs text-slate-400">{role}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 px-6 bg-white" id="pricing">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 mb-3">Planos simples, sem surpresa</h2>
            <p className="text-slate-500 mb-3">Comece grátis. Faça upgrade quando precisar.</p>
            <Link to="/pricing" className="text-sm text-brand-600 font-medium hover:underline">
              Ver comparativo completo de planos →
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 items-start">
            {PLANS.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-2xl border p-6 ${
                  plan.highlight
                    ? 'border-brand-400 shadow-lg shadow-brand-100 relative'
                    : 'border-slate-200'
                }`}
              >
                {plan.highlight && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-brand-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                      MAIS POPULAR
                    </span>
                  </div>
                )}
                {plan.badge && (
                  <div className="bg-green-100 text-green-700 text-xs font-semibold px-2 py-0.5 rounded-full inline-block mb-3">
                    {plan.badge}
                  </div>
                )}
                <h3 className="font-bold text-xl text-slate-900 mb-1">{plan.name}</h3>
                <p className="text-xs text-slate-500 mb-4">{plan.description}</p>
                <div className="flex items-end gap-1 mb-5">
                  <span className="text-3xl font-extrabold text-slate-900">{plan.price}</span>
                  <span className="text-sm text-slate-400 mb-1">{plan.period}</span>
                </div>
                <ul className="space-y-2.5 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2.5 text-sm text-slate-600">
                      <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to={plan.href}
                  className={`block text-center text-sm font-semibold py-2.5 rounded-lg transition-colors ${
                    plan.highlight
                      ? 'bg-brand-600 text-white hover:bg-brand-700'
                      : 'border border-slate-200 text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="py-20 px-6 bg-brand-600 text-white text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl font-bold mb-4">
            Pronto para responder mais rápido?
          </h2>
          <p className="text-brand-100 mb-8 text-lg">
            Crie sua conta grátis agora. Sem cartão de crédito. Setup em 2 minutos.
          </p>
          <Link
            to="/register"
            className="inline-flex items-center gap-2 bg-white text-brand-700 font-bold py-3 px-8 rounded-xl hover:bg-brand-50 transition-colors text-base"
          >
            Começar grátis
            <ArrowRight className="w-4 h-4" />
          </Link>
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
          <div className="flex gap-4 flex-wrap justify-center">
            <Link to="/pricing" className="hover:text-slate-600 transition-colors">Preços</Link>
            <Link to="/login" className="hover:text-slate-600 transition-colors">Entrar</Link>
            <Link to="/register" className="hover:text-slate-600 transition-colors">Cadastrar</Link>
            <Link to="/privacy" className="hover:text-slate-600 transition-colors">Privacidade</Link>
            <Link to="/terms" className="hover:text-slate-600 transition-colors">Termos</Link>
            <Link to="/contact" className="hover:text-slate-600 transition-colors">Contato</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}
