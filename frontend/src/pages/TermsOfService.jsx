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
          <Link to="/privacy" className="hover:text-slate-600">Privacidade</Link>
          <Link to="/contact" className="hover:text-slate-600">Contato</Link>
        </div>
      </footer>
    </div>
  )
}

export default function TermsOfService() {
  return (
    <PublicLayout>
      <div className="prose prose-slate max-w-none">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Termos de Uso</h1>
        <p className="text-slate-500 text-sm mb-8">Última atualização: abril de 2026</p>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">1. Aceitação dos termos</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            Ao criar uma conta ou usar o HostFlow, você concorda com estes Termos de Uso. Se não
            concordar, não use o serviço. O uso continuado após alterações nestes termos constitui
            aceitação das alterações.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">2. Descrição do serviço</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            O HostFlow é uma plataforma SaaS que auxilia anfitriões de temporada na comunicação com
            hóspedes por meio de inteligência artificial. O serviço inclui geração de mensagens,
            caixa de entrada unificada, integração com Gmail e WhatsApp Business, templates
            personalizados e outras funcionalidades descritas em nossa página de preços.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">3. Conta e responsabilidades</h2>
          <ul className="text-slate-600 text-sm leading-relaxed space-y-2 list-disc pl-5">
            <li>Você é responsável por manter a confidencialidade das suas credenciais de acesso.</li>
            <li>Você deve fornecer informações verdadeiras e atualizadas no cadastro.</li>
            <li>Você é responsável por todas as atividades realizadas com sua conta.</li>
            <li>É vedado compartilhar o acesso à conta com terceiros não autorizados.</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">4. Planos e cobrança</h2>
          <ul className="text-slate-600 text-sm leading-relaxed space-y-2 list-disc pl-5">
            <li>Os planos e preços são descritos na <Link to="/pricing" className="text-brand-600 hover:underline">página de preços</Link>.</li>
            <li>O trial gratuito de 14 dias está disponível para novas contas no plano Pro, sem necessidade de cartão de crédito.</li>
            <li>Cobranças são realizadas mensalmente via Stripe. O acesso continua até o fim do período pago após cancelamento.</li>
            <li>Não realizamos reembolsos por períodos parciais, salvo determinação legal.</li>
            <li>Reservamos o direito de alterar preços com aviso prévio de 30 dias.</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">5. Uso aceitável</h2>
          <p className="text-slate-600 text-sm leading-relaxed mb-3">É proibido usar o HostFlow para:</p>
          <ul className="text-slate-600 text-sm leading-relaxed space-y-2 list-disc pl-5">
            <li>Enviar spam ou comunicações não solicitadas em massa.</li>
            <li>Gerar conteúdo enganoso, fraudulento ou que viole direitos de terceiros.</li>
            <li>Violar leis aplicáveis, incluindo normas de proteção de dados.</li>
            <li>Tentar contornar os limites de uso dos planos ou acessar dados de outros usuários.</li>
            <li>Fazer engenharia reversa ou explorar vulnerabilidades do serviço.</li>
          </ul>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">6. Propriedade intelectual</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            O HostFlow e todo o seu conteúdo são de propriedade da empresa operadora. O uso do
            serviço não transfere qualquer direito de propriedade intelectual. Você mantém a
            propriedade dos dados e conteúdos que você insere na plataforma.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">7. Limitação de responsabilidade</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            O HostFlow é fornecido "como está". Não garantimos disponibilidade ininterrupta ou
            ausência de erros. As respostas geradas por IA são sugestões — a responsabilidade pela
            comunicação final com hóspedes é sempre do usuário. Nossa responsabilidade está limitada
            ao valor pago nos últimos 3 meses de serviço.
          </p>
        </section>

        <section className="mb-8">
          <h2 className="text-xl font-bold text-slate-800 mb-3">8. Suspensão e cancelamento</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            Podemos suspender ou encerrar contas que violem estes termos. Você pode cancelar sua
            conta a qualquer momento pelo painel de assinatura. Após o cancelamento, seus dados
            são retidos por até 90 dias antes da exclusão definitiva.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-800 mb-3">9. Lei aplicável e foro</h2>
          <p className="text-slate-600 text-sm leading-relaxed">
            Estes termos são regidos pelas leis brasileiras. Fica eleito o foro da comarca de
            [Cidade da empresa], Brasil, para resolução de eventuais disputas.
          </p>
          <p className="text-slate-600 text-sm leading-relaxed mt-3">
            Para dúvidas, entre em <Link to="/contact" className="text-brand-600 hover:underline">contato</Link>.
          </p>
        </section>
      </div>
    </PublicLayout>
  )
}
