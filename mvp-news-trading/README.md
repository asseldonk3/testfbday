# MVP News Trading System

AI-powered news-based trading system for EU markets using Gemini's Google Search grounding for real-time news monitoring.

## 🎯 Mission
Each week, pick the most tradeable EU companies to watch, focused on names with highest probability of meaningful intraday action.

## 🚀 Quick Start with Docker

### Prerequisites
- Docker and Docker Compose
- API Keys (Gemini, Alpaca)

### Setup

1. **Configure environment**
```bash
cd mvp-news-trading
# Add your API keys to .env file
```

2. **Start with Docker**
```bash
docker-compose up -d
```

3. **Access the system**
- API: http://localhost:8009
- API Docs: http://localhost:8009/docs

### Without Docker

```bash
# Setup backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run backend
uvicorn main:app --reload --port 8000
```

## 📊 System Architecture

```
Gemini 2.5 Pro (with Google Search Grounding)
    ↓
Scout Agent (Every 30 min)
    ↓
Analyst Agent (Signal Generation)
    ↓
Risk Manager (Position Sizing)
    ↓
Executor (Alpaca Paper Trading)
    ↓
Portfolio Tracking & Telegram Alerts
```

## 🎯 Key Features

- **Real-time News**: Gemini 2.5 Pro with native Google Search grounding
- **EU Market Focus**: Top 10 liquid EU stocks (ASML, Shell, SAP, etc.)
- **Risk Management**: Max 3 trades/day, 2% risk per trade
- **Paper Trading**: Safe testing with Alpaca
- **Simple Architecture**: Single FastAPI service, PostgreSQL in Docker

## 🔧 API Endpoints

### Signals
- `POST /api/signals/scan/{ticker}` - Manual news scan for a stock
- `POST /api/signals/scan-all` - Scan all watchlist stocks
- `GET /api/signals/active` - Get active signals

### Trading & Portfolio
- `GET /api/trades/today` - Today's trades
- `GET /api/portfolio/status` - Portfolio overview
- `GET /api/portfolio/metrics` - Performance metrics

## 📈 Monitored EU Stocks

| Ticker | Company | Exchange | Sector |
|--------|---------|----------|--------|
| ASML.AS | ASML | Amsterdam | Technology |
| SHEL.AS | Shell | Amsterdam | Energy |
| SAP.DE | SAP | Frankfurt | Technology |
| MC.PA | LVMH | Paris | Luxury |
| TTE.PA | TotalEnergies | Paris | Energy |

## ⚠️ Risk Warning

**Educational purposes only. Paper trading mode by default. Never risk money you can't afford to lose.**

## 📝 Documentation

See `/docs/implementation-plan.md` for detailed guide.