# investment_agent

Agent autônomo de **trade spot** para Binance usando `binance-connector` (SDK oficial). Foco em **alocação de carteira (BTC/ETH/SOL/BNB)**, **DCA mensal** e **rebalanceamento semanal**, com guard-rails de risco.

> **Modo padrão:** TESTNET (sem risco real). Para produção, veja abaixo.

---

## Arquitetura

- Python 3.11
- [binance-connector](https://github.com/binance/binance-connector-python) (SDK oficial Spot)
- Execução em container Docker (cron interno)
- Logs em SQLite + CSV, alertas opcionais por Telegram
- Estratégia:
  - **Targets**: BTC 60%, ETH 25%, SOL 10%, BNB 5% (TRUMP sem aportes)
  - **DCA mensal** (R$ 300/mês ≈ €50 — ajuste no `.env`)
  - **Rebalance semanal** (±5 p.p. de tolerância)
  - **Satélite opcional** com filtro SMA200 (desligado por padrão)

---

## Quick start (local)

1) Clone o repositório e crie o arquivo `.env`:
```bash
cp .env.example .env
# edite com suas chaves de TESTNET (ou deixe em branco para rodar só leitura)
```

2) Build e start:
```bash
docker compose up --build -d
# logs
docker compose logs -f agent
```

3) Banco de dados/arquivos (volume): `./data/`

---

## Variáveis de ambiente (`.env`)

```ini
# Modo de operação
TESTNET=true
LIVE=false

# Credenciais (Spot). Para Testnet, gere no site de testnet Spot da Binance
BINANCE_API_KEY=
BINANCE_API_SECRET=

# Alvos da carteira
TARGET_BTC=0.60
TARGET_ETH=0.25
TARGET_SOL=0.10
TARGET_BNB=0.05

# DCA mensal (moeda da conta base — ex: USDT ou EUR)
DCA_ENABLED=true
DCA_DAY=5                 # dia do mês (1-28 recomendado)
DCA_AMOUNT_BASE=50.0      # valor total do DCA por mês (ex: €50)
DCA_BASE_ASSET=EUR        # EUR ou USDT (de acordo com sua conta)
DCA_SYMBOLS=BTC,ETH,SOL,BNB

# Rebalanceamento semanal
REBALANCE_ENABLED=true
REBALANCE_WEEKDAY=2       # 0=Seg ... 6=Dom; ex: 2=Quarta
REBALANCE_TOLERANCE=0.05  # 5 p.p.

# Risco e guard-rails
DAILY_LOSS_CAP_PCT=0.015  # pausa se PnL diário < -1.5%
MAX_ORDERS_PER_DAY=20
RISK_PER_TRADE=0.01       # 1% do capital por trade (satélite, se ativar)

# Notificações (opcional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Timezone (para agendamentos)
TZ=America/Sao_Paulo

# Pausa de segurança via arquivo
KILL_SWITCH_FILE=/app/data/.kill
```

---

## Produção (VPS)

1) **Crie uma API Key Spot** com *Enable Spot Trading*, **sem Withdrawals**, e **whitelist do IP** da VPS.
2) Edite `.env`: `TESTNET=false` e `LIVE=true` + chaves de produção.
3) Suba o container na VPS:
```bash
docker compose up --build -d
```

---

## Deploy no GitHub

No seu computador:
```bash
git init
git remote add origin https://github.com/ViniciusMRod/investment_agent.git
git add .
git commit -m "feat: initial agent skeleton (binance-connector + dca + rebalance)"
git push -u origin main
```

---

## Aviso

Este projeto é fornecido "como está". Use por sua conta e risco. Sem alavancagem. Sem derivativos. Sempre teste em **TESTNET** antes de produção.
