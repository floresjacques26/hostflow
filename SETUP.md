# HostFlow — Setup Local

## Pré-requisitos
- Python 3.12+
- Node.js 20+
- PostgreSQL 15+ (ou Docker)

---

## 1. Banco de dados (via Docker — mais fácil)

```bash
docker run -d \
  --name hostflow-db \
  -e POSTGRES_DB=hostflow \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:16-alpine
```

---

## 2. Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv .venv
source .venv/bin/activate       # Linux/Mac
.venv\Scripts\activate          # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Edite .env e coloque sua OPENAI_API_KEY

# Rodar servidor
uvicorn app.main:app --reload --port 8000
```

Acesse a documentação da API: http://localhost:8000/docs

---

## 3. Frontend

```bash
cd frontend

npm install
npm run dev
```

Acesse: http://localhost:5173

---

## 4. Subir tudo com Docker Compose

```bash
# Na raiz do projeto
cp backend/.env.example backend/.env
# Edite backend/.env com sua OPENAI_API_KEY

docker-compose up --build
```

---

## Deploy

### Backend → Railway
1. Crie projeto no [Railway](https://railway.app)
2. Adicione PostgreSQL plugin
3. Conecte o repositório → selecione `/backend`
4. Configure variáveis: `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY`, `FRONTEND_URL`

### Frontend → Vercel
1. Importe o repositório no [Vercel](https://vercel.com)
2. Root directory: `frontend`
3. Framework: Vite
4. Adicione variável `VITE_API_URL` (URL do backend Railway)
5. Atualize `vite.config.js` para usar a variável em produção

---

## Estrutura do projeto

```
HostFlow/
├── backend/
│   └── app/
│       ├── core/         # config, database, security
│       ├── models/       # SQLAlchemy models
│       ├── schemas/      # Pydantic schemas
│       ├── routes/       # FastAPI routers
│       └── services/     # AI service, seed
├── frontend/
│   └── src/
│       ├── components/   # Layout, ProtectedRoute
│       ├── hooks/        # useAuth (Zustand)
│       ├── lib/          # axios instance
│       └── pages/        # Dashboard, Calculator, Templates
└── docker-compose.yml
```

---

## Migração: billing (banco existente)

```bash
psql -U postgres -d hostflow -f backend/migrations/002_add_billing.sql

# Ou via Docker:
docker exec -i hostflow-db psql -U postgres -d hostflow \
  < backend/migrations/002_add_billing.sql
```

## Stripe: configuração local

1. Crie uma conta em [dashboard.stripe.com](https://dashboard.stripe.com)
2. Acesse **Products → Add product**, crie "HostFlow Pro" e "HostFlow Business"
3. Copie os **Price IDs** (ex: `price_1Oabc...`) para o `.env`
4. Para testar webhooks localmente, instale o [Stripe CLI](https://stripe.com/docs/stripe-cli):
   ```bash
   stripe login
   stripe listen --forward-to localhost:8000/webhooks/stripe
   # O CLI imprime o STRIPE_WEBHOOK_SECRET — coloque no .env
   ```
5. Para simular checkout: `stripe trigger checkout.session.completed`

## Migração: multi-imóvel (banco existente)

Se você já tem o banco rodando do MVP anterior, execute a migration antes de subir o novo código:

```bash
# Conecte ao banco e execute:
psql -U postgres -d hostflow -f backend/migrations/001_add_properties.sql

# Ou via Docker:
docker exec -i hostflow-db psql -U postgres -d hostflow \
  < backend/migrations/001_add_properties.sql
```

A migration é segura e idempotente — pode rodar múltiplas vezes sem erro.

> Se está subindo do zero (banco vazio), não precisa rodar a migration manualmente. O `create_tables()` no lifespan do FastAPI cria tudo automaticamente.

## Próximos passos

- [ ] Integração com Stripe (assinaturas free/pro)
- [ ] Webhook Airbnb / integração nativa
- [ ] App mobile (React Native)
- [ ] Analytics de atendimento (tempo médio, contextos mais comuns)
