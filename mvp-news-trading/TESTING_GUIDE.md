# MVP News Trading System - Testing Guide

## 🚀 Current Status: OPERATIONAL

The MVP News Trading System backend is now fully operational with all core components implemented and running.

## ✅ Completed Components

### 1. **Infrastructure**
- ✅ PostgreSQL database running in Docker (port 5433)
- ✅ Database tables initialized (signals, trades, portfolio)
- ✅ FastAPI backend server running (port 8000)

### 2. **AI Agents**
- ✅ **Scout Agent**: Monitors news for 10 EU stocks every 30 minutes
- ✅ **Analyst Agent**: Converts news/predictions into trading signals
- ✅ **Risk Manager Agent**: Validates trades against risk rules
- ✅ **Executor Agent**: Places and manages trades via Alpaca

### 3. **Integrations**
- ✅ **Alpaca API**: Connected to paper trading account ($100k portfolio)
- ✅ **Gemini AI**: Working for news analysis and signal generation
- ✅ **Webhook Handler**: Ready to receive external predictions

### 4. **Risk Management**
- Max 3 trades per day
- Max 2% portfolio risk per trade
- Max 5% daily loss limit
- No trades after 3 consecutive losses
- Position sizing based on risk parameters

## 🧪 How to Test

### 1. Start the System
```bash
# Ensure PostgreSQL is running
docker-compose up -d postgres

# Start the backend (already running)
cd backend
source venv/bin/activate
python -m uvicorn main:app --reload --port 8000
```

### 2. Test Endpoints

#### Health Check
```bash
curl http://localhost:8000/
# Returns: {"message":"MVP News Trading System","status":"running",...}
```

#### Account Info
```bash
curl http://localhost:8000/api/alpaca/test
# Returns: Alpaca account details
```

#### Webhook Test
```bash
curl -X POST http://localhost:8000/webhook/test
# Returns: {"status":"success","message":"Webhook endpoint is working",...}
```

### 3. Send a Trading Prediction via Webhook
```bash
curl -X POST http://localhost:8000/webhook/prediction \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "prediction": {
      "direction": "BUY",
      "confidence": 85
    },
    "source": "external_tool",
    "reasoning": "Strong technical breakout pattern"
  }'
```

### 4. View Webhook Logs
```bash
curl http://localhost:8000/webhook/logs
# Returns: List of recent webhook events
```

### 5. Check System Status
```bash
curl http://localhost:8000/api/status
# Returns: Portfolio status, today's trades, active signals
```

## 📊 API Documentation

Access the interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔄 Webhook Integration

The prediction tool webhook accepts POST requests at `/webhook/prediction` with this format:

```json
{
  "ticker": "STOCK_SYMBOL",
  "prediction": {
    "direction": "BUY|SELL",
    "confidence": 0-100
  },
  "source": "tool_name",
  "reasoning": "explanation",
  "metadata": {}  // optional
}
```

### Webhook Flow:
1. Receives prediction → 2. Generates signal → 3. Validates with Risk Manager → 4. Executes if approved

## 📈 Trading Workflow

1. **Scheduled News Monitoring** (every 30 minutes)
   - Scout Agent scans news for watchlist stocks
   - Creates pending signals for material news

2. **Signal Analysis**
   - Analyst Agent evaluates pending signals
   - Calculates confidence and price targets

3. **Risk Validation**
   - Risk Manager checks all rules
   - Calculates position size

4. **Trade Execution**
   - Executor Agent places orders
   - Manages stops and targets

## 🛠️ Monitoring & Logs

### View Logs
```bash
# Backend logs (already visible in terminal)
# Webhook logs
cat logs/webhook_logs.json | python3 -m json.tool
```

### Database Queries
```bash
# Connect to PostgreSQL
docker exec -it trading_postgres psql -U trader -d trading_db

# View signals
SELECT * FROM signals ORDER BY created_at DESC LIMIT 10;

# View trades
SELECT * FROM trades ORDER BY opened_at DESC LIMIT 10;
```

## ⚠️ Current Limitations

1. **EU Stock Support**: Alpaca may not support all EU stocks (configured for EU but may need US stocks for full testing)
2. **Google Search**: Gemini's Google Search grounding is simplified (uses AI-generated responses instead of real search)
3. **Paper Trading Only**: Currently configured for Alpaca paper trading
4. **No Frontend Yet**: Use API endpoints directly or build frontend separately

## 🔧 Configuration

Edit `.env` file for configuration:
```bash
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
GEMINI_API_KEY=your_key
DATABASE_URL=postgresql://trader:tradingpass123@localhost:5433/trading_db
WEBHOOK_SECRET=optional_secret
```

## 📝 Next Steps

1. **Frontend Dashboard**: Build web interface for monitoring
2. **Telegram Notifications**: Add real-time alerts
3. **Enhanced Logging**: Implement comprehensive error tracking
4. **Backtesting**: Add historical performance analysis
5. **Production Deployment**: Move to cloud infrastructure

## 🚨 Testing Risk-Free

All trading is done in Alpaca's paper trading environment with virtual money. No real funds are at risk during testing.

## 📞 Support

For issues or questions:
1. Check the logs for error messages
2. Verify all services are running (PostgreSQL, FastAPI)
3. Ensure API keys are valid
4. Test individual components separately

---

**System Status**: ✅ READY FOR TESTING

Last Updated: January 16, 2025