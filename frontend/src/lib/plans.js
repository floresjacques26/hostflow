/**
 * Plan presentation config — single source of truth for all billing UI.
 *
 * Limits (max_properties, max_ai_responses_per_month, etc.) come from the
 * backend /billing/plans endpoint and are passed in as `apiPlan`.
 *
 * Everything here is presentation-only: bullet copy, comparison rows,
 * display prices, FAQ content, marketing labels.
 */

// ── Display metadata ──────────────────────────────────────────────────────────

export const PLAN_META = {
  free: {
    displayName: 'Free',
    price: 'R$ 0',
    priceNote: '/mês, para sempre',
    description: 'Para quem quer experimentar',
    badge: null,
    highlight: false,
    cta: {
      public: 'Começar grátis',
      inApp: null, // user is already on free if this is shown
    },
    color: 'slate',
  },
  pro: {
    displayName: 'Pro',
    price: 'R$ 49',
    priceNote: '/mês',
    description: 'Para hosts ativos',
    badge: '14 dias grátis',
    highlight: true, // "most popular" ring
    cta: {
      public: 'Testar 14 dias grátis',
      inApp: 'Fazer upgrade para Pro',
    },
    color: 'brand',
  },
  business: {
    displayName: 'Business',
    price: 'R$ 129',
    priceNote: '/mês',
    description: 'Para gestoras e multi-hosts',
    badge: null,
    highlight: false,
    cta: {
      public: 'Começar agora',
      inApp: 'Fazer upgrade para Business',
    },
    color: 'purple',
  },
}

// ── Feature bullets (what's shown in pricing cards) ───────────────────────────

export const PLAN_BULLETS = {
  free: [
    '1 imóvel cadastrado',
    '20 respostas com IA por mês',
    '3 templates personalizados',
    'Calculadora de check-in/out',
    'Acesso básico à caixa de entrada',
  ],
  pro: [
    'Até 5 imóveis cadastrados',
    '500 respostas com IA por mês',
    'Templates ilimitados',
    'Histórico completo de conversas',
    'Caixa de entrada unificada',
    'Gmail nativo + WhatsApp Business',
    'Auto-envio com IA',
    'Trial gratuito de 14 dias',
  ],
  business: [
    'Imóveis ilimitados',
    'Respostas com IA ilimitadas',
    'Tudo do plano Pro',
    'Analytics avançado',
    'Relatórios de performance',
    'Preparado para equipes',
    'Suporte prioritário',
  ],
}

// ── Comparison table ──────────────────────────────────────────────────────────
// Each row: { label, free, pro, business }
// Values: string | true | false
// true → green checkmark, false → dash (not available)

export const COMPARISON_ROWS = [
  {
    section: 'Limites',
    rows: [
      { label: 'Imóveis cadastrados',         free: '1',        pro: 'Até 5',     business: 'Ilimitados' },
      { label: 'Respostas com IA / mês',       free: '20',       pro: '500',       business: 'Ilimitadas' },
      { label: 'Templates personalizados',     free: 'Até 3',    pro: 'Ilimitados', business: 'Ilimitados' },
    ],
  },
  {
    section: 'Caixa de entrada',
    rows: [
      { label: 'Caixa de entrada unificada',  free: true,       pro: true,        business: true },
      { label: 'Gmail nativo',                free: false,      pro: true,        business: true },
      { label: 'WhatsApp Business',           free: false,      pro: true,        business: true },
      { label: 'Auto-envio com IA',           free: false,      pro: true,        business: true },
    ],
  },
  {
    section: 'Ferramentas',
    rows: [
      { label: 'Calculadora de check-in/out', free: true,       pro: true,        business: true },
      { label: 'Histórico de conversas',      free: 'Limitado', pro: 'Completo',  business: 'Completo' },
      { label: 'Templates inteligentes',      free: true,       pro: true,        business: true },
    ],
  },
  {
    section: 'Analytics e gestão',
    rows: [
      { label: 'Dashboard de uso',            free: true,       pro: true,        business: true },
      { label: 'Analytics avançado',          free: false,      pro: false,       business: true },
      { label: 'Relatórios de performance',   free: false,      pro: false,       business: true },
      { label: 'Preparado para equipes',      free: false,      pro: false,       business: true },
    ],
  },
  {
    section: 'Suporte',
    rows: [
      { label: 'Suporte por email',           free: true,       pro: true,        business: true },
      { label: 'Suporte prioritário',         free: false,      pro: false,       business: true },
    ],
  },
]

// ── FAQ ───────────────────────────────────────────────────────────────────────

export const PRICING_FAQ = [
  {
    q: 'Preciso de cartão de crédito para o trial?',
    a: 'Não. O trial gratuito de 14 dias do plano Pro não exige cartão de crédito. Você só informa os dados de pagamento se decidir assinar ao final do período.',
  },
  {
    q: 'O que acontece quando o trial termina?',
    a: 'Ao final dos 14 dias, sua conta volta automaticamente para o plano Free. Você não perde nenhum dado — apenas os limites do Free voltam a ser aplicados. Para continuar com todos os recursos Pro, basta assinar antes do prazo.',
  },
  {
    q: 'Posso cancelar quando quiser?',
    a: 'Sim. Você pode cancelar a qualquer momento pelo portal de gerenciamento de assinatura, sem taxa de cancelamento. Seu acesso continua até o fim do período pago.',
  },
  {
    q: 'Como funciona a mudança de plano?',
    a: 'Você pode fazer upgrade imediatamente — a cobrança é proporcional ao período restante. Para downgrade, a mudança entra em vigor no próximo ciclo de cobrança.',
  },
  {
    q: 'O WhatsApp Business está incluso no Pro?',
    a: 'Sim. A integração com WhatsApp Business Cloud API está disponível no plano Pro e Business. Você conecta a sua própria conta Meta Business pelo painel de Integrações.',
  },
  {
    q: 'Quantos imóveis posso ter no plano Business?',
    a: 'Imóveis ilimitados. O plano Business é ideal para gestoras, imobiliárias ou anfitriões com grande volume de propriedades.',
  },
  {
    q: 'Os dados do meu imóvel ficam seguros?',
    a: 'Sim. Todos os dados são armazenados de forma segura, com criptografia em trânsito e em repouso. Nunca compartilhamos suas informações com terceiros.',
  },
  {
    q: 'Vocês aceitam pagamento por boleto ou Pix?',
    a: 'No momento, trabalhamos com cartão de crédito via Stripe. Pagamento por boleto está no roadmap e deve ser disponibilizado em breve.',
  },
]

// ── Conversion event names ────────────────────────────────────────────────────
// Used by trackEvent() helper on the frontend and stored in the event log.

export const CONVERSION_EVENTS = {
  VIEWED_PRICING_PAGE:   'viewed_pricing_page',
  CLICKED_PLAN_CTA:      'clicked_plan_cta',
  STARTED_CHECKOUT:      'started_checkout',
  CHECKOUT_COMPLETED:    'checkout_completed',
  CHECKOUT_CANCELED:     'checkout_canceled',
  VIEWED_SUCCESS_PAGE:   'viewed_success_page',
  UPGRADED_IN_APP:       'upgraded_in_app',
  STARTED_TRIAL:         'started_trial',
  CLICKED_COMPARISON:    'clicked_comparison',
}
