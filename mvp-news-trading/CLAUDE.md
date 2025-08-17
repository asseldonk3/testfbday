# CLAUDE.md - MVP News Trading Backend

This file provides guidance to Claude Code when working with the MVP News Trading backend system.

## Project Focus

This directory contains the backend implementation for the automated news-based trading system. It handles:
- Real-time news monitoring and analysis
- Trading signal generation via AI agents
- Risk management and position sizing
- Trade execution through broker APIs
- Webhook integration for predictions

## Core Components

### Agent System
- **Scout Agent**: Monitors news sources every 30 minutes
- **Analyst Agent**: Converts news into actionable trading signals
- **Risk Manager Agent**: Enforces position limits and risk parameters
- **Executor Agent**: Handles order placement and management

### Webhook Integration
The prediction tool webhook is a critical component that:
- Receives external trading signals
- Validates incoming predictions
- Routes signals to appropriate agents
- Logs all webhook events for audit

## Development Commands

```bash
# Setup backend environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run the backend server
uvicorn main:app --reload --port 8000

# Start Celery worker for async tasks
celery -A main.celery worker --loglevel=info

# Start Celery beat for scheduled tasks
celery -A main.celery beat --loglevel=info

# Run tests
pytest tests/

# Database migrations
alembic upgrade head
```

## API Endpoints

Key endpoints to implement:
- `POST /webhook/prediction` - Receive prediction signals
- `GET /api/signals` - List active trading signals
- `POST /api/trades/execute` - Execute a trade
- `GET /api/positions` - Current positions
- `GET /api/performance` - Performance metrics

## Risk Management Rules

Hard-coded limits:
- Max 3 trades per day
- Max 2% portfolio risk per trade
- Max 5% daily loss
- No trades after 3 consecutive losses
- Position size = (Portfolio * 0.02) / (Entry - StopLoss)

## Webhook Handler Structure

```python
@app.post("/webhook/prediction")
async def handle_prediction_webhook(request: Request):
    """
    Process incoming prediction signals
    - Validate webhook signature
    - Parse prediction data
    - Apply risk filters
    - Generate trade signal if approved
    - Log to webhook_handler.json
    """
    pass
```

## Database Schema

Core tables:
- `signals` - All generated trading signals
- `trades` - Executed trades with entry/exit
- `positions` - Current open positions
- `webhook_logs` - All webhook events
- `performance` - Daily P&L tracking

## Environment Variables

Required in `.env`:
```
# LLM APIs
OPENAI_API_KEY=
GEMINI_API_KEY=

# Trading
ALPACA_API_KEY=
ALPACA_SECRET_KEY=

# Database
DATABASE_URL=postgresql://user:pass@localhost/trading_db
REDIS_URL=redis://localhost:6379

# Webhook
WEBHOOK_SECRET=
WEBHOOK_ENDPOINT=/webhook/prediction

# Risk Parameters
MAX_TRADES_PER_DAY=3
MAX_RISK_PER_TRADE=0.02
MAX_DAILY_LOSS=0.05
```

## Testing Strategy

Focus areas:
1. Webhook validation and security
2. Risk management rule enforcement
3. Signal generation accuracy
4. Order execution reliability
5. Error handling and recovery

## Performance Targets

- Webhook processing: <500ms
- Signal generation: <30 seconds
- Order execution: <2 seconds
- System uptime: >99% during market hours