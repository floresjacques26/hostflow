import { Link } from 'react-router-dom'
import { MessageSquare } from 'lucide-react'

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
      <main className="max-w-3xl mx-auto px-6 py-12">{children}</main>
      <footer className="border-t border-slate-100 py-6 text-center text-sm text-slate-400">
        <div className="flex justify-center gap-6">
          <Link to="/" className="hover:text-slate-600">Início</Link>
          <Link to="/pricing" className="hover:text-slate-600">Preços</Link>
          <Link to="/terms" className="hover:text-slate-600">Termos de uso</Link>
          <Link to="/contact" className="hover:text-slate-600">Contato</Link>
        </div>
      </footer>
    </div>
  )
}

export default function PrivacyPolicy() {
  return (
    <PublicLayout>
      <div className="prose prose-slate max-w-none">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Política de Privacidade</h1>
        <p className="text-slate-500 text-sm mb-8">Última atualização: abril de 2026</p>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">1. Quem somos</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            O HostFlow é um serviço SaaS operado por [Empresa Operadora], com sede no Brasil. Nosso
            produto ajuda anfitriões do Airbnb e plataformas similares a gerenciar a comunicação com
            hóspedes com o auxílio de inteligência artificial.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">2. Dados que coletamos</h2>
          <ul className="text-slate-600 text-sm leading-relaxed space-y-2 list-disc pl-5">
            <li><strong>Dados de conta:</strong> nome, e-mail e senha (armazenada com hash seguro).</li>
            <li><strong>Dados de imóveis:</strong> informações cadastradas pelo usuário sobre seus imóveis (regras, horários, preços).</li>
            <li><strong>Mensagens de hóspedes:</strong> conteúdo processado para geração de respostas com IA. Não armazenamos mensagens além do necessário para o serviço.</li>
            <li><strong>Dados de integração:</strong> tokens OAuth do Gmail e credenciais do WhatsApp Business, armazenados com criptografia Fernet.</li>
            <li><strong>Dados de pagamento:</strong> gerenciados exclusivamente pelo Stripe. Não armazenamos dados de cartão de crédito.</li>
            <li><strong>Dados de uso:</strong> contadores de uso mensal para controle de limites de plano.</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">3. Como usamos seus dados</h2>
          <ul className="text-slate-600 text-sm leading-relaxed space-y-2 list-disc pl-5">
            <li>Prestar o serviço contratado (geração de respostas, sincronização de mensagens).</li>
            <li>Enviar comunicações transacionais (confirmação de cadastro, notificações de trial, lembretes de cobrança).</li>
            <li>Melhorar o produto com dados agregados e anonimizados.</li>
            <li>Cumprir obrigações legais e prevenir fraudes.</li>
          </ul>
          <p className="text-slate-600 text-sm leading-relaxed mt-3">
            Nunca vendemos ou compartilhamos seus dados pessoais com terceiros para fins de marketing.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">4. Terceiros e subprocessadores</h2>
          <p className="text-slate-600 text-sm leading-relaxed mb-3">
            Utilizamos os seguintes serviços de terceiros, cada um com sua própria política de privacidade:
          </p>
          <ul className="text-slate-600 text-sm leading-relaxed space-y-2 list-disc pl-5">
            <li><strong>OpenAI:</strong> geração de respostas com IA. As mensagens são enviadas para a API da OpenAI para processamento.</li>
            <li><strong>Stripe:</strong> processamento de pagamentos.</li>
            <li><strong>Resend:</strong> envio de e-mails transacionais.</li>
            <li><strong>Google:</strong> integração Gmail OAuth.</li>
            <li><strong>Meta:</strong> integração WhatsApp Business Cloud API.</li>
            <li><strong>Railway / Cloudflare:</strong> hospedagem e armazenamento de arquivos.</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">5. Segurança</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            Todos os dados são transmitidos com criptografia TLS. Dados sensíveis (tokens OAuth) são
            armazenados com criptografia Fernet em repouso. Senhas são armazenadas com bcrypt.
            Realizamos verificações de segurança periódicas e seguimos boas práticas de desenvolvimento seguro.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">6. Seus direitos (LGPD)</h2>
          <p className="text-slate-600 text-sm leading-relaxed mb-3">
            Em conformidade com a Lei Geral de Proteção de Dados (Lei 13.709/2018), você tem direito a:
          </p>
          <ul className="text-slate-600 text-sm leading-relaxed space-y-2 list-disc pl-5">
            <li>Confirmar a existência de tratamento dos seus dados.</li>
            <li>Acessar, corrigir ou atualizar seus dados.</li>
            <li>Solicitar a exclusão dos seus dados pessoais.</li>
            <li>Revogar o consentimento a qualquer momento.</li>
            <li>Solicitar a portabilidade dos seus dados.</li>
          </ul>
          <p className="text-slate-600 text-sm leading-relaxed mt-3">
            Para exercer seus direitos, entre em contato: <Link to="/contact" className="text-brand-600 hover:underline">contato</Link>.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">7. Retenção de dados</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            Mantemos seus dados enquanto sua conta estiver ativa. Após o cancelamento, os dados são
            retidos por até 90 dias para fins de backup e suporte, após os quais são excluídos.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-800 mb-3">8. Contato</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            Para dúvidas sobre esta política ou sobre o tratamento dos seus dados, entre em contato
            pelo nosso{' '}
            <Link to="/contact" className="text-brand-600 hover:underline">
              formulário de contato
            </Link>{' '}
            ou pelo e-mail <strong>privacidade@hostflow.com.br</strong>.
          </p>
        </section>
      </div>
    </PublicLayout>
  )
}
