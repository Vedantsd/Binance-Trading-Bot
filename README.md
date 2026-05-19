# Binance Testnet Trading Bot

A Python CLI application for placing orders on the **Binance USDT-M Futures Testnet**.

---

## Features

| Feature | Detail |
|---|---|
| Order types | MARKET, LIMIT, **STOP_LIMIT** (bonus) |
| Sides | BUY / SELL |
| CLI | `argparse`-based with sub-commands |
| Validation | Full input validation with clear error messages |
| Logging | Rotating log file (`logs/trading_bot.log`) + console output |
| Error handling | Typed exceptions for API errors, network failures, auth issues |
| Structure | Separate client / orders / validators / CLI layers |

---

## Project Structure

```
Binance-Trading-Bot/
├── bot/
│   ├── client.py          # Binance REST client (signing, HTTP, exceptions)
│   ├── orders.py          # Order placement logic + OrderResult dataclass
│   ├── validators.py      # Input validation (raises ValueError on bad input)
│   └── logging_config.py  # Rotating file + console logging setup
├── cli.py                 # CLI entry point 
├── logs/
│   └── trading_bot.log    # Auto-generated (sample logs included)
├── .env                   
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Setup

### 1. Get Testnet Credentials

1. Visit [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in (GitHub OAuth is the easiest option)
3. Go to **API Key** → **Generate Key** → copy your API key and secret

### 2. Clone & Install

```bash
git clone https://github.com/Vedantsd/Binance-Trading-Bot.git
cd Binance-Trading-Bot

python -m venv .venv
source .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure Credentials

```bash
cp .env.example .env
# Edit .env and set your API key and secret:
#   BINANCE_API_KEY=""
#   BINANCE_API_SECRET=""
```

---

## How to Run

### Place a MARKET order 

```bash
# BUY 0.001 BTC at market price
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

# SELL 0.1 ETH at market price
python cli.py place --symbol ETHUSDT --side SELL --type MARKET --qty 0.1
```

### Place a LIMIT order

```bash
# SELL 0.001 BTC at $110,000 (GTC)
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 110000

# BUY 0.01 ETH at $3,000 (GTC)
python cli.py place --symbol ETHUSDT --side BUY --type LIMIT --qty 0.01 --price 3000
```

### Place a STOP_LIMIT order (bonus)

```bash
# Triggers at $94,500, places a limit BUY at $95,000
python cli.py place --symbol BTCUSDT --side BUY --type STOP_LIMIT \
    --qty 0.001 --price 95000 --stop-price 94500
```

### List open orders

```bash
python cli.py open-orders --symbol BTCUSDT   # filtered
python cli.py open-orders                    # all symbols
```

### Show account balance

```bash
python cli.py account
```

### Verbose / debug output

```bash
python cli.py --log-level DEBUG place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

---

## Example CLI Output

```
────────────────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────────
  Symbol         : BTCUSDT
  Side           : BUY
  Type           : MARKET
  Quantity       : 0.001
────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────
  ORDER RESPONSE
────────────────────────────────────────────────────────────
  Order ID       : 4512097348
  Symbol         : BTCUSDT
  Side           : BUY
  Type           : MARKET
  Status         : FILLED
  Orig Qty       : 0.001
  Executed Qty   : 0.001
  Avg Price      : 105432.10
────────────────────────────────────────────────────────────

  Order placed successfully!
```

---

## Validation Rules

| Field | Rule |
|---|---|
| symbol | Non-empty, alphanumeric |
| side | Must be `BUY` or `SELL` |
| type | Must be `MARKET`, `LIMIT`, or `STOP_LIMIT` |
| qty | Positive number, ≤ 1,000,000 |
| price | Required for LIMIT/STOP_LIMIT; must not be provided for MARKET |
| stop-price | Required only for STOP_LIMIT |

---

## Assumptions

- **USDT-M Futures only** — the testnet endpoint only supports USDT-margined perpetuals.
- **Position mode** — the bot uses the default **one-way** (BOTH) position side. Hedge mode is not supported.
- **Time-in-force** — LIMIT and STOP_LIMIT orders use `GTC` (Good Till Cancelled) by default.
- **Quantity precision** — Binance enforces per-symbol precision rules (e.g. BTC = 3 decimals). Use values that match the testnet's `LOT_SIZE` filter. Invalid precision returns an API error with a clear message.
- **Testnet only** — `BINANCE_BASE_URL` defaults to `https://testnet.binancefuture.com`. To use mainnet, override the env variable (and accept the associated financial risk!).

---

## Requirements

```
requests
python-dotenv
```

Python 3.9+ required.