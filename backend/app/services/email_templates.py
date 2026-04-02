"""
Lifecycle email templates — all in pt-BR.

Each public function returns (subject: str, html: str, text: str).
Edit templates here; the layout wrapper (_layout) controls branding globally.

Brand color: #4F46E5 (indigo-600 equivalent)
"""

# ── Layout ────────────────────────────────────────────────────────────────────

_BRAND_COLOR = "#4F46E5"
_BRAND_LIGHT = "#EEF2FF"


def _btn(label: str, url: str) -> str:
    return (
        f'<table cellpadding="0" cellspacing="0" style="margin:24px 0;">'
        f'<tr><td style="background:{_BRAND_COLOR};border-radius:8px;">'
        f'<a href="{url}" style="display:inline-block;padding:12px 28px;color:#ffffff;'
        f'font-size:15px;font-weight:600;text-decoration:none;border-radius:8px;">'
        f'{label}</a></td></tr></table>'
    )


def _layout(body_html: str, app_url: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>HostFlow</title>
</head>
<body style="margin:0;padding:0;background-color:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="580" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:12px;overflow:hidden;
                      max-width:580px;width:100%;box-shadow:0 1px 3px rgba(0,0,0,.06);">

          <!-- Header -->
          <tr>
            <td style="background:{_BRAND_COLOR};padding:22px 32px;">
              <a href="{app_url}" style="text-decoration:none;">
                <span style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.3px;">
                  &#9889; HostFlow
                </span>
              </a>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:36px 32px 28px;color:#1e293b;font-size:15px;line-height:1.7;">
              {body_html}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:20px 32px 28px;background:#f8fafc;
                       border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8;">
              <p style="margin:0 0 6px;">
                Você recebeu este e-mail porque tem uma conta no HostFlow.<br>
                Se não foi você, ignore este e-mail.
              </p>
              <p style="margin:0;">
                <a href="{app_url}" style="color:{_BRAND_COLOR};text-decoration:none;">
                  Acessar HostFlow
                </a>
                &nbsp;·&nbsp;
                <a href="{app_url}/billing" style="color:{_BRAND_COLOR};text-decoration:none;">
                  Gerenciar assinatura
                </a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _highlight_box(content: str, color: str = _BRAND_LIGHT) -> str:
    return (
        f'<div style="background:{color};border-radius:8px;padding:16px 20px;'
        f'margin:20px 0;font-size:14px;">{content}</div>'
    )


# ── Templates ─────────────────────────────────────────────────────────────────

def welcome(name: str, app_url: str) -> tuple[str, str, str]:
    subject = "Bem-vindo ao HostFlow! Veja como começar"
    first_name = name.split()[0]
    body = f"""
<p style="font-size:22px;font-weight:700;margin:0 0 16px;color:#0f172a;">
  Olá, {first_name}! 👋
</p>
<p style="margin:0 0 16px;">
  Sua conta no <strong>HostFlow</strong> foi criada com sucesso.
  Agora você tem tudo o que precisa para responder hóspedes do Airbnb de forma
  profissional — em segundos, com IA.
</p>

{_highlight_box("""
<p style="margin:0 0 10px;font-weight:600;color:#1e293b;">Seus próximos passos:</p>
<p style="margin:0 0 6px;">&#9312; Cadastre seu primeiro imóvel com as regras específicas</p>
<p style="margin:0 0 6px;">&#9313; Cole uma mensagem de hóspede e veja a IA em ação</p>
<p style="margin:0;">&#9314; Experimente a calculadora de check-in antecipado / check-out tardio</p>
""")}

{_btn("Acessar minha conta", app_url + "/dashboard")}

<p style="margin:0;color:#64748b;font-size:14px;">
  Qualquer dúvida, é só responder este e-mail.<br>
  Boas boas-vindas ao HostFlow! 🏠
</p>
"""
    text = (
        f"Olá, {first_name}!\n\n"
        "Sua conta no HostFlow foi criada com sucesso.\n\n"
        "Próximos passos:\n"
        "1. Cadastre seu primeiro imóvel\n"
        "2. Gere sua primeira resposta com IA\n"
        "3. Use a calculadora de check-in/check-out\n\n"
        f"Acesse: {app_url}/dashboard\n\n"
        "Qualquer dúvida, responda este e-mail."
    )
    return subject, _layout(body, app_url), text


def trial_started(name: str, days: int, app_url: str) -> tuple[str, str, str]:
    subject = f"Seu trial Pro de {days} dias começou! 🚀"
    first_name = name.split()[0]
    body = f"""
<p style="font-size:22px;font-weight:700;margin:0 0 16px;color:#0f172a;">
  Seu trial Pro está ativo, {first_name}!
</p>
<p style="margin:0 0 16px;">
  Você agora tem acesso completo ao plano <strong>Pro</strong> por
  <strong>{days} dias</strong> — sem precisar de cartão de crédito.
</p>

{_highlight_box(f"""
<p style="margin:0 0 10px;font-weight:600;">O que você tem no plano Pro:</p>
<p style="margin:0 0 4px;">✅ Até 5 imóveis com regras personalizadas</p>
<p style="margin:0 0 4px;">✅ 500 respostas de IA por mês</p>
<p style="margin:0 0 4px;">✅ Templates ilimitados</p>
<p style="margin:0;">✅ Histórico completo de conversas</p>
""")}

{_btn("Explorar o plano Pro", app_url + "/dashboard")}

<p style="margin:0;color:#64748b;font-size:14px;">
  Aproveite ao máximo esses {days} dias. Se gostar, assinar é rápido e simples.
</p>
"""
    text = (
        f"Olá, {first_name}!\n\n"
        f"Seu trial Pro de {days} dias está ativo.\n\n"
        "O que você tem:\n"
        "- Até 5 imóveis\n"
        "- 500 respostas de IA/mês\n"
        "- Templates ilimitados\n"
        "- Histórico completo\n\n"
        f"Acesse: {app_url}/dashboard\n\n"
        f"Aproveite os {days} dias!"
    )
    return subject, _layout(body, app_url), text


def trial_ending_soon(name: str, days_left: int, app_url: str) -> tuple[str, str, str]:
    first_name = name.split()[0]
    if days_left <= 1:
        subject = "Seu trial Pro termina hoje — assine agora ⚡"
        urgency = "termina <strong>hoje</strong>"
        urgency_color = "#FEF2F2"
    else:
        subject = f"Seu trial Pro termina em {days_left} dias"
        urgency = f"termina em <strong>{days_left} dias</strong>"
        urgency_color = "#FFF7ED"

    body = f"""
<p style="font-size:22px;font-weight:700;margin:0 0 16px;color:#0f172a;">
  Seu trial Pro {urgency}
</p>
<p style="margin:0 0 16px;">
  Olá, {first_name}! Não perca o acesso às ferramentas que você já está usando.
  Assinar o plano Pro leva menos de 2 minutos.
</p>

{_highlight_box("""
<p style="margin:0 0 8px;font-weight:600;">Por apenas <span style="color:#4F46E5;">R$ 49/mês</span> você mantém:</p>
<p style="margin:0 0 4px;">✅ 500 respostas de IA por mês</p>
<p style="margin:0 0 4px;">✅ Até 5 imóveis</p>
<p style="margin:0;">✅ Templates e histórico ilimitados</p>
""", urgency_color)}

{_btn("Assinar o plano Pro agora", app_url + "/billing")}

<p style="margin:0;color:#64748b;font-size:14px;">
  Se não assinar, sua conta volta ao plano Free automaticamente
  (1 imóvel, 20 respostas/mês).
</p>
"""
    text = (
        f"Olá, {first_name}!\n\n"
        f"Seu trial Pro {urgency.replace('<strong>', '').replace('</strong>', '')}.\n\n"
        "Para manter o acesso Pro:\n"
        f"Assine em: {app_url}/billing\n\n"
        "Plano Pro: R$ 49/mês — 500 respostas, 5 imóveis, templates ilimitados."
    )
    return subject, _layout(body, app_url), text


def trial_expired(name: str, app_url: str) -> tuple[str, str, str]:
    subject = "Seu trial Pro expirou — volte quando quiser"
    first_name = name.split()[0]
    body = f"""
<p style="font-size:22px;font-weight:700;margin:0 0 16px;color:#0f172a;">
  Seu trial Pro expirou, {first_name}
</p>
<p style="margin:0 0 16px;">
  Sua conta voltou para o plano Free. Você ainda pode usar o HostFlow,
  mas com os limites do plano gratuito (1 imóvel, 20 respostas/mês).
</p>
<p style="margin:0 0 16px;">
  Se quiser continuar aproveitando todos os recursos, assinar é rápido:
</p>

{_btn("Assinar o plano Pro", app_url + "/billing")}

{_highlight_box("""
<p style="margin:0 0 6px;font-weight:600;color:#4F46E5;">Por que assinar?</p>
<p style="margin:0 0 4px;font-size:14px;">Cada resposta gerada com IA economiza em média 2 minutos.</p>
<p style="margin:0;font-size:14px;">Com 500 respostas/mês, isso são mais de 16 horas poupadas.</p>
""")}

<p style="margin:0;color:#64748b;font-size:14px;">
  Sem pressão — sua conta está preservada e você pode assinar quando quiser.
</p>
"""
    text = (
        f"Olá, {first_name}!\n\n"
        "Seu trial Pro expirou. Sua conta voltou ao plano Free.\n\n"
        "Para continuar com o plano Pro:\n"
        f"{app_url}/billing\n\n"
        "Plano Pro: R$ 49/mês."
    )
    return subject, _layout(body, app_url), text


def upgrade_confirmation(name: str, plan: str, app_url: str) -> tuple[str, str, str]:
    plan_display = "Pro" if plan == "pro" else "Business"
    subject = f"Bem-vindo ao plano {plan_display}! 🎉"
    first_name = name.split()[0]
    body = f"""
<p style="font-size:22px;font-weight:700;margin:0 0 16px;color:#0f172a;">
  Assinatura confirmada, {first_name}! 🎉
</p>
<p style="margin:0 0 16px;">
  Você agora é um assinante do plano <strong>{plan_display}</strong>.
  Obrigado por apoiar o HostFlow!
</p>

{_highlight_box(f"""
<p style="margin:0 0 8px;font-weight:600;">O que mudou na sua conta:</p>
{'<p style="margin:0 0 4px;">✅ 500 respostas de IA por mês</p><p style="margin:0 0 4px;">✅ Até 5 imóveis</p><p style="margin:0;">✅ Templates e histórico ilimitados</p>' if plan == 'pro' else '<p style="margin:0 0 4px;">✅ Respostas ilimitadas</p><p style="margin:0 0 4px;">✅ Imóveis ilimitados</p><p style="margin:0;">✅ Analytics avançado</p>'}
""")}

{_btn("Acessar minha conta", app_url + "/dashboard")}

<p style="margin:0;color:#64748b;font-size:14px;">
  Você pode gerenciar sua assinatura a qualquer momento em
  <a href="{app_url}/billing" style="color:{_BRAND_COLOR};">Assinatura</a>.
</p>
"""
    text = (
        f"Olá, {first_name}!\n\n"
        f"Sua assinatura do plano {plan_display} foi confirmada. Obrigado!\n\n"
        f"Acesse: {app_url}/dashboard\n\n"
        f"Gerencie sua assinatura em: {app_url}/billing"
    )
    return subject, _layout(body, app_url), text


def payment_failed(name: str, app_url: str) -> tuple[str, str, str]:
    subject = "Problema no pagamento — ação necessária"
    first_name = name.split()[0]
    body = f"""
<p style="font-size:22px;font-weight:700;margin:0 0 16px;color:#0f172a;">
  Não conseguimos processar seu pagamento
</p>
<p style="margin:0 0 16px;">
  Olá, {first_name}. Houve um problema ao cobrar o método de pagamento
  associado à sua assinatura HostFlow.
</p>
<p style="margin:0 0 16px;">
  Para não perder o acesso ao plano Pro, atualize seus dados de pagamento:
</p>

{_btn("Atualizar método de pagamento", app_url + "/billing")}

{_highlight_box("""
<p style="margin:0 0 6px;font-weight:600;color:#DC2626;">Importante:</p>
<p style="margin:0;font-size:14px;">
  Se o pagamento não for resolvido em breve, sua conta será revertida
  automaticamente para o plano Free.
</p>
""", "#FEF2F2")}

<p style="margin:0;color:#64748b;font-size:14px;">
  Se precisar de ajuda, responda este e-mail e resolveremos juntos.
</p>
"""
    text = (
        f"Olá, {first_name}!\n\n"
        "Não conseguimos processar o pagamento da sua assinatura HostFlow.\n\n"
        "Para manter o acesso, atualize seus dados:\n"
        f"{app_url}/billing\n\n"
        "Se precisar de ajuda, responda este e-mail."
    )
    return subject, _layout(body, app_url), text


def subscription_canceled(name: str, app_url: str) -> tuple[str, str, str]:
    subject = "Sua assinatura foi cancelada"
    first_name = name.split()[0]
    body = f"""
<p style="font-size:22px;font-weight:700;margin:0 0 16px;color:#0f172a;">
  Assinatura cancelada, {first_name}
</p>
<p style="margin:0 0 16px;">
  Sua assinatura Pro do HostFlow foi cancelada. Sua conta voltou ao plano
  Free e seus dados foram preservados.
</p>

{_highlight_box("""
<p style="margin:0 0 8px;font-weight:600;">O que você ainda tem:</p>
<p style="margin:0 0 4px;">✅ 1 imóvel</p>
<p style="margin:0 0 4px;">✅ 20 respostas de IA por mês</p>
<p style="margin:0;">✅ Histórico das suas conversas</p>
""")}

<p style="margin:0 0 16px;">
  Se mudou de ideia, você pode reativar sua assinatura a qualquer momento:
</p>

{_btn("Reativar assinatura", app_url + "/billing")}

<p style="margin:0;color:#64748b;font-size:14px;">
  Se houve algum problema que motivou o cancelamento, adoraríamos ouvir.
  Basta responder este e-mail.
</p>
"""
    text = (
        f"Olá, {first_name}!\n\n"
        "Sua assinatura Pro do HostFlow foi cancelada.\n"
        "Sua conta voltou ao plano Free e seus dados foram preservados.\n\n"
        "Para reativar:\n"
        f"{app_url}/billing\n\n"
        "Qualquer dúvida, responda este e-mail."
    )
    return subject, _layout(body, app_url), text


def activation_reminder(name: str, onboarding_step: int, app_url: str) -> tuple[str, str, str]:
    subject = "Você ainda não experimentou tudo do HostFlow"
    first_name = name.split()[0]

    if onboarding_step == 0:
        next_step = "Cadastrar seu primeiro imóvel"
        next_path = "/properties"
        hint = "Com um imóvel cadastrado, a IA usa suas regras específicas nas respostas."
    elif onboarding_step == 1:
        next_step = "Gerar sua primeira resposta com IA"
        next_path = "/dashboard"
        hint = "Cole qualquer mensagem de hóspede e veja a resposta em segundos."
    else:
        next_step = "Usar a calculadora de check-in"
        next_path = "/calculator"
        hint = "Calcule automaticamente o valor para check-in antecipado ou check-out tardio."

    body = f"""
<p style="font-size:22px;font-weight:700;margin:0 0 16px;color:#0f172a;">
  Você tem recursos não explorados, {first_name}
</p>
<p style="margin:0 0 16px;">
  Você criou sua conta mas ainda não configurou tudo. Isso leva menos de
  2 minutos e faz uma diferença enorme no dia a dia.
</p>

{_highlight_box(f"""
<p style="margin:0 0 8px;font-weight:600;">Próximo passo:</p>
<p style="margin:0 0 6px;font-size:15px;">👉 <strong>{next_step}</strong></p>
<p style="margin:0;font-size:13px;color:#64748b;">{hint}</p>
""")}

{_btn(f"Continuar configuração", app_url + next_path)}

<p style="margin:0;color:#64748b;font-size:14px;">
  Hosts que completam o setup respondem hóspedes até 10x mais rápido.
</p>
"""
    text = (
        f"Olá, {first_name}!\n\n"
        "Você ainda não explorou tudo do HostFlow.\n\n"
        f"Próximo passo: {next_step}\n"
        f"{hint}\n\n"
        f"Continue aqui: {app_url}{next_path}"
    )
    return subject, _layout(body, app_url), text


def reactivation(name: str, app_url: str) -> tuple[str, str, str]:
    subject = "Sentimos sua falta — volte ao HostFlow"
    first_name = name.split()[0]
    body = f"""
<p style="font-size:22px;font-weight:700;margin:0 0 16px;color:#0f172a;">
  Sentimos sua falta, {first_name} 👋
</p>
<p style="margin:0 0 16px;">
  Faz um tempo que você não usa o HostFlow. Seu trial expirou, mas você
  pode retomar com um plano Pro quando quiser.
</p>

{_highlight_box("""
<p style="margin:0 0 8px;font-weight:600;">O que você deixou para trás:</p>
<p style="margin:0 0 4px;">⚡ Respostas profissionais para hóspedes em segundos</p>
<p style="margin:0 0 4px;">🏠 Regras por imóvel (check-in, pets, preços)</p>
<p style="margin:0;">⏱️ ~2 minutos economizados por resposta</p>
""")}

{_btn("Voltar ao HostFlow", app_url + "/billing")}

<p style="margin:0;color:#64748b;font-size:14px;">
  Plano Pro: R$ 49/mês. Cancele quando quiser, sem multa.
</p>
"""
    text = (
        f"Olá, {first_name}!\n\n"
        "Sentimos sua falta no HostFlow.\n\n"
        "Seu trial expirou, mas você pode retomar com o plano Pro:\n"
        f"{app_url}/billing\n\n"
        "R$ 49/mês. Cancele quando quiser."
    )
    return subject, _layout(body, app_url), text
