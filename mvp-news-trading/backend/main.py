from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime
import schedule
import time
from threading import Thread
from loguru import logger
import hashlib
import hmac
import json

from database import engine, Base, get_db
from config import settings
from sqlalchemy.orm import Session

# Import models to register them with SQLAlchemy
from models import Signal, Trade, Portfolio

# Import agents
from agents.scout import ScoutAgent
from agents.analyst import AnalystAgent
from agents.risk_manager import RiskManagerAgent
from agents.executor import ExecutorAgent

# Import API routers
from api.watchlist import router as watchlist_router
from routers.news import router as news_router

# Initialize agents
scout_agent = ScoutAgent()
analyst_agent = AnalystAgent()
risk_manager = RiskManagerAgent()
executor_agent = ExecutorAgent()

# Create database tables
Base.metadata.create_all(bind=engine)

# Background scheduler
scheduler_running = False

def run_scheduler():
    """Run the scheduler in a separate thread"""
    global scheduler_running
    scheduler_running = True
    logger.info("Scheduler started")
    
    while scheduler_running:
        schedule.run_pending()
        time.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting MVP News Trading System")
    
    # Start scheduler in background thread
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Schedule scout agent to run every 30 minutes
    schedule.every(settings.scout_interval_minutes).minutes.do(scout_news)
    
    # Schedule daily summary at 18:00 CET
    schedule.every().day.at("18:00").do(send_daily_summary)
    
    yield
    
    # Shutdown
    global scheduler_running
    scheduler_running = False
    logger.info("Shutting down MVP News Trading System")

# Create FastAPI app
app = FastAPI(
    title="MVP News Trading System",
    description="AI-powered news-based trading system for EU markets",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import API routers
from api import webhook

# Include routers
app.include_router(webhook.router)
app.include_router(watchlist_router)
app.include_router(news_router)

# Scheduled tasks
async def scout_news():
    """Run scout agent to check for news"""
    logger.info("Running scout agent for news monitoring")
    try:
        # Run news scan
        news_results = await scout_agent.run_scheduled_scan()
        
        # Process pending signals
        signals = await analyst_agent.analyze_pending_signals()
        
        # Validate and execute approved signals
        for signal in signals:
            approved, reason, trade_params = await risk_manager.validate_signal(signal)
            if approved:
                await executor_agent.execute_trade(trade_params)
                
    except Exception as e:
        logger.error(f"Error in scout news task: {str(e)}")

async def send_daily_summary():
    """Send daily trading summary via Telegram"""
    logger.info("Sending daily summary")
    try:
        # Get today's performance
        summary = await executor_agent.get_positions_summary()
        
        # Update portfolio metrics
        await risk_manager.update_portfolio_metrics()
        
        # TODO: Send via Telegram
        logger.info(f"Daily summary: {summary}")
        
    except Exception as e:
        logger.error(f"Error sending daily summary: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "MVP News Trading System",
        "status": "running",
        "environment": settings.environment,
        "market_hours": f"{settings.market_open_hour}:00-{settings.market_close_hour}:{settings.market_close_minute}",
        "watchlist_count": len(settings.watchlist)
    }

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected",
        "scheduler": scheduler_running
    }

# System status
@app.get("/api/status")
async def get_status(db: Session = Depends(get_db)):
    from models import Portfolio, Signal, Trade
    from sqlalchemy import func
    
    # Get portfolio status
    portfolio = db.query(Portfolio).first()
    
    # Get today's trades
    today = datetime.now().date()
    today_trades = db.query(Trade).filter(
        func.date(Trade.created_at) == today
    ).count()
    
    # Get active signals
    active_signals = db.query(Signal).filter(
        Signal.status == "pending"
    ).count()
    
    return {
        "portfolio": portfolio.to_dict() if portfolio else None,
        "today_trades": today_trades,
        "active_signals": active_signals,
        "max_trades_remaining": settings.max_trades_per_day - today_trades,
        "market_status": "open" if is_market_open() else "closed"
    }

def is_market_open():
    """Check if EU markets are open"""
    now = datetime.now()
    if now.weekday() >= 5:  # Weekend
        return False
    
    current_time = now.time()
    market_open = datetime.now().replace(
        hour=settings.market_open_hour, 
        minute=0, 
        second=0
    ).time()
    market_close = datetime.now().replace(
        hour=settings.market_close_hour,
        minute=settings.market_close_minute,
        second=0
    ).time()
    
    return market_open <= current_time <= market_close

# Test Alpaca connection endpoint
@app.get("/api/alpaca/test")
async def test_alpaca_connection():
    """Test Alpaca API connection"""
    try:
        from services.alpaca_service import AlpacaService
        alpaca = AlpacaService()
        account = alpaca.get_account_info()
        
        if account:
            return {
                "status": "connected",
                "account": {
                    "buying_power": account["buying_power"],
                    "portfolio_value": account["portfolio_value"],
                    "cash": account["cash"],
                    "currency": account["currency"]
                }
            }
        else:
            return {"status": "error", "message": "Could not retrieve account info"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Test Gemini news scanning
@app.get("/api/gemini/test/{ticker}")
async def test_gemini_news(ticker: str):
    """Test Gemini news analysis for a specific ticker"""
    try:
        from services.gemini_service import GeminiService
        gemini = GeminiService()
        
        # Get news analysis
        news_result = await gemini.analyze_news_for_ticker(ticker)
        
        return {
            "status": "success",
            "ticker": ticker,
            "analysis": news_result
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Check position sizing and risk limits
@app.get("/api/risk/check")
async def check_risk_limits(db: Session = Depends(get_db)):
    """Check if trading is allowed based on risk limits"""
    from services.position_sizing import PositionSizer
    
    sizer = PositionSizer(db)
    return sizer.can_trade()

# Calculate position size for a trade
@app.post("/api/risk/position-size")
async def calculate_position(
    entry_price: float,
    stop_loss: float,
    confidence: int = 70,
    db: Session = Depends(get_db)
):
    """Calculate position size based on risk management rules"""
    from services.position_sizing import PositionSizer
    
    sizer = PositionSizer(db)
    return sizer.calculate_position_size(entry_price, stop_loss, confidence)

# API routes
try:
    from api import signals, trades, portfolio, watchlist
    app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
    app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
    app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
    app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
    logger.info("API routes loaded successfully")
except ImportError as e:
    logger.warning(f"Some API routes not available: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.environment == "development" else False
    )