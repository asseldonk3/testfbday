# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an MVP News-Based Trading System that uses AI agents to monitor news, generate trading signals, and execute trades with risk management. The system is designed for automated day trading across three strategies: News-Based Trading, Gap and Go, and Momentum Scalping.

## System Architecture

The project follows a multi-agent architecture:
- **Weekly Heartbeat Agent**: Selects 10-25 companies to monitor weekly
- **Scout Agent**: Monitors news every 30 minutes using Gemini Pro 2.5 + GPT-4
- **Analyst Agent**: Converts information into trade signals
- **Risk Manager**: Applies hard rules and risk assessment
- **Executor Agent**: Places and manages trades via broker API

## Development Commands

### Setup & Installation
```bash
# Backend setup
cd mvp-news-trading
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup (separate dashboard)
cd frontend-dashboard
npm install  # or: python -m venv venv && pip install -r requirements.txt

# Database initialization
cd mvp-news-trading/utilities
python setup_database.py
```

### Running the System
```bash
# Start all services (run in separate terminals)
redis-server                                    # Redis
cd mvp-news-trading && uvicorn main:app --reload --port 8000  # Backend API
cd frontend-dashboard && npm run dev            # Frontend dashboard (port 3000)
cd mvp-news-trading && celery -A main.celery worker --loglevel=info  # Celery worker
cd mvp-news-trading && celery -A main.celery beat --loglevel=info    # Celery scheduler
```

### Testing
```bash
# Run tests (when implemented)
cd mvp-news-trading && pytest
cd frontend-dashboard && npm test  # or pytest if using Python
```

## Key Implementation Details

### Trading Strategies
1. **News-Based Trading**: Primary strategy using LLM text analysis with <30 second latency target
2. **Gap and Go**: Secondary strategy for overnight gaps with catalyst validation
3. **Momentum Scalping**: Tertiary strategy for social media-driven moves

### Risk Management Rules
- Max 3 trades per day
- Max 2% portfolio risk per trade  
- Max 5% daily portfolio loss
- No trades after 3 consecutive losses
- Position sizing using Kelly Criterion
- No trades during first/last 15 minutes of market

### Technology Stack
- **Backend**: FastAPI with Python 3.11
- **Frontend**: Flask + Bootstrap
- **Database**: PostgreSQL 15+ for trade history, Redis for caching
- **Queue**: Celery + RabbitMQ for scheduled tasks
- **LLMs**: GPT-4, Gemini Pro 2.5, Claude (for redundancy)
- **Trading API**: Alpaca Markets
- **Market Data**: Polygon.io, NewsAPI, Reddit API

### Agent Prompts & Scoring
News scoring uses a weighted formula:
- Catalyst proximity: 30%
- Volume trend: 20%  
- Gap history: 20%
- Options activity: 15%
- Liquidity score: 15%

## Current Project Status

**Implementation Progress: 95% Complete** - See [mvp-news-trading/IMPLEMENTATION_STATUS.md](mvp-news-trading/IMPLEMENTATION_STATUS.md) for detailed progress tracking.

### System Architecture
- `mvp-news-trading/backend/` - Backend trading system with AI agents and Alpaca integration
- `mvp-news-trading/frontend/` - Flask dashboard with real-time pipeline visualization
- `mvp-news-trading/utilities/` - Database setup and utility scripts
- `artifacts/` - Product discovery documentation
- `brainstorm/` - Strategy analysis and planning documents

### What's Working
- ✅ Complete trading pipeline from news monitoring to trade execution
- ✅ Interactive frontend dashboard with WebSocket updates
- ✅ Weekly watchlist admin interface (Step 0)
- ✅ Risk management with position sizing
- ✅ Alpaca paper trading integration
- ✅ Webhook integration for external predictions

Note: System is 95% operational and ready for testing with live market data.

## Environment Configuration

Required API keys in `.env`:
- `GEMINI_API_KEY`
- `OPENAI_API_KEY`
- `ALPACA_API_KEY` & `ALPACA_SECRET_KEY`
- `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`
- `DATABASE_URL` (PostgreSQL connection)
- `REDIS_URL`
- `WEBHOOK_SECRET` (for prediction tool integration)
- `WEBHOOK_ENDPOINT` (typically `/webhook/prediction`)

## Success Metrics
- Win rate target: >60%
- News-to-signal latency: <30 seconds
- System uptime: >99% during market hours
- False positive rate: <20%
- Daily success rate: >60%