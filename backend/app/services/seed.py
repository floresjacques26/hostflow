"""Seeds default templates on first startup."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.template import Template

DEFAULT_TEMPLATES = [
    {
        "title": "Boas-vindas",
        "category": "welcome",
        "context_key": "checkin",
        "auto_apply": False,
        "priority": 0,
        "content": (
            "Olá, {nome_hospede}! Seja muito bem-vindo(a)! 🏠\n\n"
            "Estamos felizes em recebê-lo(a). Seguem as informações importantes:\n"
            "• Check-in: a partir das 14h\n"
            "• Check-out: até as 11h\n"
            "• Wi-Fi: {wifi_nome} | Senha: {wifi_senha}\n\n"
            "Qualquer dúvida, estou à disposição. Boa estadia!"
        ),
    },
    {
        "title": "Regras da Casa",
        "category": "rules",
        "context_key": "house_rules",
        "auto_apply": True,
        "priority": 0,
        "content": (
            "Olá! Segue um resumo das regras da casa:\n\n"
            "• Não é permitido fumar nas dependências\n"
            "• Animais de estimação: consultar previamente\n"
            "• Festas e eventos: não permitidos\n"
            "• Silêncio após as 22h\n"
            "• Check-out: até as 11h (sem exceções sem aviso prévio)\n"
            "• Danos ao imóvel serão cobrados separadamente\n\n"
            "Contamos com a sua compreensão. Qualquer dúvida, estou aqui!"
        ),
    },
    {
        "title": "Recusa Educada",
        "category": "refusal",
        "context_key": None,
        "auto_apply": False,
        "priority": -5,  # lower priority — only use when explicitly selected
        "content": (
            "Olá! Obrigado pela mensagem.\n\n"
            "Infelizmente não conseguimos atender a essa solicitação desta vez, "
            "pois estamos comprometidos com as políticas da propriedade para garantir "
            "uma boa experiência para todos os hóspedes.\n\n"
            "Caso tenha outras dúvidas ou precise de ajuda, estou à disposição!"
        ),
    },
    {
        "title": "Early Check-in — Cobrança",
        "category": "charge",
        "context_key": "early_checkin",
        "auto_apply": True,
        "priority": 10,
        "content": (
            "Olá! Verificamos a disponibilidade para early check-in.\n\n"
            "Conseguimos liberar o apartamento antes das 14h mediante pagamento de "
            "meia diária, caso haja disponibilidade no dia anterior. "
            "Posso confirmar o valor e a disponibilidade assim que verificar a agenda.\n\n"
            "Confirma o interesse?"
        ),
    },
    {
        "title": "Late Check-out — Cobrança",
        "category": "charge",
        "context_key": "late_checkout",
        "auto_apply": True,
        "priority": 10,
        "content": (
            "Olá! Sobre o late check-out:\n\n"
            "• Até as 15h: meia diária\n"
            "• Até as 18h: diária completa\n\n"
            "Sujeito à disponibilidade do dia. Confirma interesse? "
            "Assim que verificar a agenda te retorno com a confirmação."
        ),
    },
    {
        "title": "Política de Animais",
        "category": "rules",
        "context_key": "pets",
        "auto_apply": True,
        "priority": 5,
        "content": (
            "Olá! Sobre animais de estimação:\n\n"
            "Nossa política para pets é consultada caso a caso. "
            "Por favor, informe o tipo e porte do animal para que eu possa verificar a disponibilidade.\n\n"
            "Geralmente solicitamos um depósito de segurança adicional para estadias com pets.\n\n"
            "Aguardo mais detalhes!"
        ),
    },
    {
        "title": "Informações de Estacionamento",
        "category": "other",
        "context_key": "parking",
        "auto_apply": True,
        "priority": 5,
        "content": (
            "Olá! Sobre estacionamento:\n\n"
            "O imóvel conta com [informar disponibilidade]. "
            "Para mais detalhes sobre acesso e eventuais custos, "
            "entre em contato que confirmo as informações!\n\n"
            "Há algo mais em que posso ajudar?"
        ),
    },
    {
        "title": "Informações de Endereço e Acesso",
        "category": "other",
        "context_key": "address",
        "auto_apply": True,
        "priority": 5,
        "content": (
            "Olá! Seguem as informações de acesso:\n\n"
            "• Endereço: [endereço completo]\n"
            "• Referência: [ponto de referência]\n"
            "• Acesso: [instruções de entrada]\n\n"
            "Caso precise de ajuda para chegar, é só me chamar! "
            "Estarei disponível para orientar no dia do check-in."
        ),
    },
    {
        "title": "Problema com Descarga / Vaso Sanitário",
        "category": "issue",
        "context_key": "complaint",
        "auto_apply": False,
        "priority": 0,
        "content": (
            "Olá! Lamentamos pelo inconveniente.\n\n"
            "Para agilizar o atendimento, você consegue me enviar um vídeo rápido "
            "mostrando o problema com a descarga? Assim consigo acionar a manutenção "
            "com mais precisão.\n\n"
            "Estou resolvendo isso o mais rápido possível para não comprometer sua estadia!"
        ),
    },
    {
        "title": "Problema com Cozinha / Equipamentos",
        "category": "issue",
        "context_key": "amenities",
        "auto_apply": False,
        "priority": 0,
        "content": (
            "Olá! Sentimos muito pelo transtorno.\n\n"
            "Pode me descrever melhor o que está acontecendo? Se possível, envie uma foto "
            "ou vídeo para eu acionar a equipe de manutenção com mais agilidade.\n\n"
            "Vou priorizar isso para garantir sua comodidade. Obrigado pela compreensão!"
        ),
    },
    {
        "title": "Disponibilidade e Preços",
        "category": "other",
        "context_key": "availability",
        "auto_apply": False,
        "priority": 0,
        "content": (
            "Olá! Obrigado pelo seu interesse.\n\n"
            "Para verificar a disponibilidade nas datas que você precisa, "
            "poderia confirmar o período de entrada e saída?\n\n"
            "Assim que confirmar, envio os valores e condições disponíveis."
        ),
    },
    {
        "title": "Cancelamento — Política",
        "category": "rules",
        "context_key": "cancellation",
        "auto_apply": True,
        "priority": 8,
        "content": (
            "Olá! Sobre cancelamentos:\n\n"
            "Nossa política de cancelamento segue as regras da plataforma onde a reserva foi feita. "
            "Cancelamentos com mais de 48h de antecedência geralmente têm reembolso parcial ou total, "
            "dependendo das condições da reserva.\n\n"
            "Posso verificar os detalhes específicos da sua reserva se precisar. "
            "Há algo mais em que posso ajudar?"
        ),
    },
]


async def seed_default_templates(db: AsyncSession):
    result = await db.execute(select(Template).where(Template.is_default == True))  # noqa: E712
    existing = result.scalars().all()
    if existing:
        return  # already seeded

    for t in DEFAULT_TEMPLATES:
        db.add(Template(
            **t,
            is_default=True,
            user_id=None,
            active=True,
        ))

    await db.commit()
