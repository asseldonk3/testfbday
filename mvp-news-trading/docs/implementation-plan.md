# MVP News-Based Trading System
## Implementation Plan

### Mission Statement
**Each week, pick the most tradeable companies to watch, not to trade—focused solely on names with the highest probability of meaningful intraday action.**

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   WEEKLY HEARTBEAT AGENT                 │
│         (Selects 10-25 companies to monitor)            │
└─────────────────────┬───────────────────────────────────┘
                      │ Weekly Watchlist
                      ▼
┌─────────────────────────────────────────────────────────┐
│                      SCOUT AGENT                         │
│    (Gemini Pro 2.5 + GPT-4 with Web Search)            │
│            Monitors watchlist every 30 min              │
└─────────────────────┬───────────────────────────────────┘
                      │ Raw Information
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    ANALYST AGENT                         │
│        (Determines what's important & actionable)        │
│              Generates trade signals                     │
└─────────────────────┬───────────────────────────────────┘
                      │ Trade Signals
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  RISK MANAGER AGENT                      │
│         (Hard rules + Risk assessment framework)         │
│      Max trades/day, max loss, position sizing          │
└─────────────────────┬───────────────────────────────────┘
                      │ Approved Trades
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   EXECUTOR AGENT                         │
│            (Places trades via broker API)                │
│                  Manages positions                       │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                          ▼
┌──────────────────┐      ┌──────────────────┐
│   WEB DASHBOARD  │      │     TELEGRAM     │
│   (Bootstrap)    │      │  (Notifications) │
└──────────────────┘      └──────────────────┘
```

---

## 📁 Project Structure

```
mvp-news-trading/
├── backend/
│   ├── main.py                    # FastAPI main application
│   ├── config.py                  # Configuration and API keys
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── weekly_heartbeat.py    # Weekly stock selector
│   │   ├── scout.py               # Information gatherer
│   │   ├── analyst.py             # Signal generator
│   │   ├── risk_manager.py        # Risk assessment
│   │   └── executor.py            # Trade execution
│   ├── models/
│   │   ├── __init__.py
│   │   ├── company.py             # Company/ticker models
│   │   ├── signal.py              # Trade signal models
│   │   ├── trade.py               # Trade execution models
│   │   └── portfolio.py           # Portfolio tracking
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_service.py         # Gemini & OpenAI integration
│   │   ├── broker_service.py      # Alpaca/broker integration
│   │   ├── telegram_service.py    # Telegram notifications
│   │   └── database_service.py    # PostgreSQL operations
│   ├── api/
│   │   ├── __init__.py
│   │   ├── trades.py              # Trade endpoints
│   │   ├── watchlist.py           # Watchlist endpoints
│   │   ├── portfolio.py           # Portfolio endpoints
│   │   └── settings.py            # Settings endpoints
│   └── requirements.txt
│
├── frontend/
│   ├── app.py                     # Flask application
│   ├── templates/
│   │   ├── base.html              # Base template with Bootstrap
│   │   ├── dashboard.html         # Main dashboard
│   │   ├── trades.html            # Trade history
│   │   ├── watchlist.html         # Current watchlist
│   │   └── settings.html          # Configuration
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css          # Custom styles
│   │   └── js/
│   │       └── dashboard.js       # Dashboard interactions
│   └── requirements.txt
│
├── utilities/
│   ├── setup_database.py          # Initialize database
│   ├── backtest.py               # Backtest strategies
│   ├── data_collector.py          # Historical data collection
│   ├── performance_analyzer.py    # Analyze trading performance
│   └── watchlist_generator.py     # Manual watchlist generation
│
├── docs/
│   ├── implementation-plan.md     # This document
│   ├── api-documentation.md       # API endpoints
│   └── agent-prompts.md           # LLM prompts
│
├── docker-compose.yml             # Docker configuration
├── .env.example                   # Environment variables template
└── README.md                      # Project overview
```

---

## 🤖 Agent Specifications

### 1. Weekly Heartbeat Agent
**Mission:** Select 10-25 most tradeable companies for the week

**Core Functions:**
- Apply liquidity gates (min $10M daily volume, <$0.05 spread)
- Build catalyst map (earnings, FDA, M&A, macro events)
- Score & rank tickers using transparent formula
- Produce Tier A (must-watch) and Tier B (opportunistic) lists
- Auto-refresh daily with new information

**Scoring Formula:**
```python
score = (
    catalyst_proximity_weight * 0.3 +
    volume_trend_weight * 0.2 +
    gap_history_weight * 0.2 +
    options_activity_weight * 0.15 +
    liquidity_score * 0.15
)
```

### 2. Scout Agent (Every 30 minutes)
**Technology:** Gemini Pro 2.5 + GPT-4 with web search

**Preferred Sources (in prompt):**
- Bloomberg.com
- Reuters.com
- SeekingAlpha.com
- SEC.gov (8-K filings)
- Benzinga.com
- MarketWatch.com
- Reddit.com/r/wallstreetbets (sentiment only)
- Twitter/X financial accounts
- CNBC.com
- Yahoo Finance

**Prompt Template:**
```
You are a financial news scout monitoring [TICKER].
Search for breaking news, focusing on these preferred sources:
[LIST OF SOURCES]

Find information about:
1. Company announcements
2. Analyst upgrades/downgrades
3. Unusual volume or price movement
4. Social media momentum
5. Sector/industry news affecting the company

Return structured data with:
- Source URL
- Headline
- Key points
- Sentiment (bullish/bearish/neutral)
- Materiality score (1-10)
- Time discovered
```

### 3. Analyst Agent
**Purpose:** Convert raw information into actionable trade signals

**Signal Generation Criteria:**
- News materiality score > 7
- Sentiment alignment across sources
- Price action confirmation
- Volume surge detected
- No conflicting information

**Output Format:**
```json
{
  "ticker": "AAPL",
  "signal_type": "BUY",
  "confidence": 85,
  "entry_price": 150.50,
  "stop_loss": 149.00,
  "target_price": 153.00,
  "reasoning": "Major product announcement...",
  "time_horizon": "intraday"
}
```

### 4. Risk Manager Agent
**Hard Rules:**
- Max 3 trades per day
- Max 2% portfolio risk per trade
- Max 5% daily portfolio loss
- No trades if 3 consecutive losses
- Position size = (Portfolio * 0.02) / (Entry - StopLoss)
- No trades during first/last 15 minutes
- No trades if spread > 0.5%

**Risk Assessment Framework:**
```python
def assess_trade(signal, portfolio):
    checks = {
        'daily_trade_count': current_trades < 3,
        'portfolio_risk': calculate_risk(signal) < 0.02,
        'daily_loss': daily_pnl > -0.05 * portfolio_value,
        'consecutive_losses': consecutive_losses < 3,
        'spread_check': spread < 0.005,
        'time_check': not in_restricted_hours(),
        'correlation_check': correlation_with_existing < 0.6
    }
    
    if all(checks.values()):
        return "APPROVED"
    else:
        return f"REJECTED: {failed_checks}"
```

### 5. Executor Agent
**Functions:**
- Place market/limit orders via Alpaca API
- Manage stop-loss and take-profit orders
- Track fill prices and slippage
- Update portfolio database
- Send execution confirmations

---

## 💻 Technology Stack

### Backend (FastAPI)
```python
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
google-generativeai==0.3.0  # Gemini
openai==1.6.0
alpaca-py==0.13.0
python-telegram-bot==20.6
sqlalchemy==2.0.23
postgresql==15.0
redis==5.0.1  # For caching
celery==5.3.4  # For scheduled tasks
pydantic==2.5.0
pandas==2.1.3
numpy==1.24.3
python-dotenv==1.0.0
httpx==0.25.2  # For async HTTP
websocket-client==1.6.4
```

### Frontend (Flask + Bootstrap)
```python
# requirements.txt
flask==3.0.0
flask-socketio==5.3.5  # For real-time updates
bootstrap-flask==2.3.2
plotly==5.18.0  # For charts
pandas==2.1.3
requests==2.31.0
python-dotenv==1.0.0
```

### Database Schema
```sql
-- Companies table
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255),
    sector VARCHAR(100),
    tier CHAR(1),  -- 'A' or 'B'
    added_date TIMESTAMP DEFAULT NOW(),
    catalyst_date TIMESTAMP,
    catalyst_type VARCHAR(100),
    score DECIMAL(5,2)
);

-- Signals table
CREATE TABLE signals (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(10),
    signal_type VARCHAR(10),  -- 'BUY', 'SELL'
    confidence INTEGER,
    entry_price DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    target_price DECIMAL(10,2),
    reasoning TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20)  -- 'pending', 'approved', 'rejected', 'executed'
);

-- Trades table
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    signal_id INTEGER REFERENCES signals(id),
    ticker VARCHAR(10),
    side VARCHAR(10),
    quantity INTEGER,
    entry_price DECIMAL(10,2),
    exit_price DECIMAL(10,2),
    pnl DECIMAL(10,2),
    status VARCHAR(20),  -- 'open', 'closed', 'cancelled'
    opened_at TIMESTAMP,
    closed_at TIMESTAMP
);

-- Portfolio table
CREATE TABLE portfolio (
    id SERIAL PRIMARY KEY,
    date DATE UNIQUE,
    starting_balance DECIMAL(12,2),
    ending_balance DECIMAL(12,2),
    daily_pnl DECIMAL(10,2),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER
);
```

---

## 📊 Frontend Dashboard Features

### Main Dashboard (dashboard.html)
- **Portfolio Overview**
  - Current balance
  - Daily P&L (with color coding)
  - Weekly/Monthly performance
  - Win rate percentage

- **Active Positions**
  - Real-time price updates
  - Unrealized P&L
  - Time in position
  - Stop/Target levels

- **Today's Trades**
  - Entry/Exit prices
  - P&L per trade
  - Status indicators

- **Watchlist Widget**
  - Tier A companies with catalysts
  - Next catalyst countdown
  - Current price/volume

### Trade History (trades.html)
- Sortable/filterable table
- Performance metrics per ticker
- Export to CSV functionality
- Trade replay/analysis

### Settings (settings.html)
- Risk parameters configuration
- API keys management
- Notification preferences
- Trading hours setup

---

## 📱 Telegram Integration

### Daily Summary (9:00 AM & 4:30 PM)
```
📊 Daily Trading Summary - [DATE]
━━━━━━━━━━━━━━━━━━━━━
💰 Starting Balance: €5,000
💵 Current Balance: €5,150
📈 Daily P&L: +€150 (+3.0%)
━━━━━━━━━━━━━━━━━━━━━
✅ Winning Trades: 2
❌ Losing Trades: 1
📊 Win Rate: 66.7%
━━━━━━━━━━━━━━━━━━━━━
Best Trade: AAPL +€80
Worst Trade: TSLA -€30
```

### Trade Notifications
```
🔔 NEW TRADE SIGNAL
Ticker: AAPL
Signal: BUY
Confidence: 85%
Entry: $150.50
Stop: $149.00
Target: $153.00
Risk: €100 (2% of portfolio)
━━━━━━━━━━━━━━━━━━━━━
Reason: Major product announcement detected
```

### Execution Confirmations
```
✅ TRADE EXECUTED
AAPL: Bought 10 shares @ $150.55
Stop Loss set @ $149.00
Take Profit set @ $153.00
```

---

## 🚀 Implementation Timeline

### Week 1: Foundation
**Goal:** Basic infrastructure and database setup

Day 1-2: Project Setup
- [ ] Initialize Git repository
- [ ] Set up Python virtual environments
- [ ] Create folder structure
- [ ] Configure PostgreSQL database
- [ ] Set up Redis for caching

Day 3-4: API Integrations
- [ ] Gemini Pro 2.5 integration
- [ ] OpenAI GPT-4 integration
- [ ] Alpaca API setup
- [ ] Telegram bot creation

Day 5-7: Database & Models
- [ ] Create database schema
- [ ] Implement SQLAlchemy models
- [ ] Basic CRUD operations
- [ ] Test database connections

### Week 2: Weekly Heartbeat Agent
**Goal:** Automated weekly watchlist generation

Day 8-10: Core Logic
- [ ] Implement liquidity filters
- [ ] Catalyst detection system
- [ ] Scoring algorithm
- [ ] Tier classification

Day 11-14: Testing & Refinement
- [ ] Backtest on historical data
- [ ] Tune scoring weights
- [ ] Add logging system
- [ ] Create manual override capability

### Week 3: Scout & Analyst Agents
**Goal:** Information gathering and signal generation

Day 15-17: Scout Agent
- [ ] Multi-LLM query system
- [ ] Web search integration
- [ ] Source prioritization
- [ ] 30-minute scheduler

Day 18-21: Analyst Agent
- [ ] Signal generation logic
- [ ] Confidence scoring
- [ ] Price target calculation
- [ ] Integration with Scout output

### Week 4: Risk Manager & Executor
**Goal:** Risk control and trade execution

Day 22-24: Risk Manager
- [ ] Hard rules implementation
- [ ] Position sizing calculator
- [ ] Correlation checker
- [ ] Daily limits tracker

Day 25-28: Executor Agent
- [ ] Alpaca order placement
- [ ] Stop/target management
- [ ] Fill tracking
- [ ] Slippage monitoring

### Week 5: Frontend Development
**Goal:** Web dashboard with Bootstrap

Day 29-31: Flask Setup
- [ ] Basic Flask application
- [ ] Bootstrap integration
- [ ] WebSocket for real-time updates
- [ ] API endpoints

Day 32-35: Dashboard Pages
- [ ] Main dashboard layout
- [ ] Trade history page
- [ ] Watchlist display
- [ ] Settings interface

### Week 6: Integration & Testing
**Goal:** Full system integration and testing

Day 36-38: Telegram Integration
- [ ] Bot setup and commands
- [ ] Notification system
- [ ] Daily summaries
- [ ] Error alerts

Day 39-42: End-to-End Testing
- [ ] Paper trading mode
- [ ] Performance monitoring
- [ ] Bug fixes
- [ ] Documentation

---

## 🔧 Configuration (.env file)

```bash
# API Keys
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id

# Database
DATABASE_URL=postgresql://user:password@localhost/trading_db
REDIS_URL=redis://localhost:6379

# Trading Configuration
MAX_TRADES_PER_DAY=3
MAX_RISK_PER_TRADE=0.02
MAX_DAILY_LOSS=0.05
STARTING_CAPITAL=5000

# Agent Settings
SCOUT_INTERVAL_MINUTES=30
CONFIDENCE_THRESHOLD=70
MIN_LIQUIDITY=10000000

# Flask Settings
FLASK_SECRET_KEY=your_secret_key
FLASK_ENV=development
FLASK_PORT=5000

# FastAPI Settings
FASTAPI_PORT=8000
WORKERS=4
```

---

## 🏃 Running the System

### Local Development Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd mvp-news-trading

# 2. Create virtual environments
python -m venv backend/venv
python -m venv frontend/venv

# 3. Install dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt

cd ../frontend
source venv/bin/activate
pip install -r requirements.txt

# 4. Set up database
cd ../utilities
python setup_database.py

# 5. Start Redis
redis-server

# 6. Start Backend (FastAPI)
cd ../backend
uvicorn main:app --reload --port 8000

# 7. Start Frontend (Flask)
cd ../frontend
python app.py

# 8. Start Celery worker (for scheduled tasks)
cd ../backend
celery -A main.celery worker --loglevel=info

# 9. Start Celery beat (for periodic tasks)
celery -A main.celery beat --loglevel=info
```

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: trading_db
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://trader:${DB_PASSWORD}@postgres/trading_db
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app

  frontend:
    build: ./frontend
    ports:
      - "5000:5000"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app

  celery_worker:
    build: ./backend
    command: celery -A main.celery worker --loglevel=info
    depends_on:
      - redis
      - postgres
    environment:
      - DATABASE_URL=postgresql://trader:${DB_PASSWORD}@postgres/trading_db
      - REDIS_URL=redis://redis:6379

  celery_beat:
    build: ./backend
    command: celery -A main.celery beat --loglevel=info
    depends_on:
      - redis
      - postgres
    environment:
      - DATABASE_URL=postgresql://trader:${DB_PASSWORD}@postgres/trading_db
      - REDIS_URL=redis://redis:6379

volumes:
  postgres_data:
```

---

## 📈 Success Metrics

### Technical KPIs
- System uptime > 99%
- Scout agent response time < 2 seconds
- Signal generation latency < 5 seconds
- Order execution time < 100ms
- Database query time < 50ms

### Trading KPIs
- Win rate > 55%
- Average profit/loss ratio > 1.5
- Maximum drawdown < 10%
- Sharpe ratio > 1.5
- Daily success rate > 60%

### Business KPIs
- Monthly return > 5%
- Cost coverage (profit > €500/month)
- Signal accuracy > 65%
- False positive rate < 20%

---

## 🔒 Security Considerations

1. **API Key Management**
   - Store in environment variables
   - Never commit to Git
   - Rotate regularly
   - Use separate keys for dev/prod

2. **Database Security**
   - Use connection pooling
   - Parameterized queries only
   - Regular backups
   - Encryption at rest

3. **Network Security**
   - HTTPS only for web interface
   - VPN for remote access
   - IP whitelist for APIs
   - Rate limiting

4. **Trading Security**
   - Position limits enforced
   - Daily loss limits
   - Automatic shutdown on anomalies
   - Audit trail for all trades

---

## 📝 Next Steps After MVP

1. **Machine Learning Enhancement**
   - Train models on historical signals
   - Pattern recognition for better entries
   - Sentiment analysis fine-tuning

2. **Additional Data Sources**
   - Options flow data
   - Dark pool prints
   - Insider trading filings
   - Alternative data (satellite, credit card)

3. **Strategy Expansion**
   - Add gap-and-go strategy
   - Social momentum detection
   - Pairs trading capability

4. **Infrastructure Scaling**
   - Move to cloud (AWS/GCP)
   - Kubernetes deployment
   - Advanced monitoring (Grafana)
   - Disaster recovery plan

5. **Compliance & Risk**
   - Regulatory compliance checks
   - Advanced risk metrics (VaR)
   - Backtesting framework
   - Performance attribution

---

## 🚨 Risk Warnings

**IMPORTANT DISCLAIMERS:**
- This system is for educational purposes
- Past performance doesn't guarantee future results
- You can lose all your invested capital
- Start with paper trading for minimum 3 months
- Only trade with money you can afford to lose
- Markets can remain irrational longer than you can remain solvent

---

## 📞 Support & Monitoring

### Monitoring Dashboard
- Grafana for metrics visualization
- Prometheus for metrics collection
- Sentry for error tracking
- CloudWatch for AWS resources

### Alerts Setup
- Telegram alerts for critical errors
- Email alerts for daily summaries
- SMS alerts for system downtime
- Slack integration for team updates

### Backup & Recovery
- Daily database backups to S3
- Configuration backups
- Trade log archives
- 30-day retention policy

---

*Last Updated: January 2025*
*Version: 1.0.0-MVP*