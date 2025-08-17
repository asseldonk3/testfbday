"""
Database models for MVP News Trading System
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, JSON, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()


class SignalSource(enum.Enum):
    """Sources of trading signals"""
    GEMINI = "gemini"
    MARKETAUX = "marketaux" 
    FINNHUB = "finnhub"
    AGGREGATED = "aggregated"
    WEBHOOK = "webhook"
    MANUAL = "manual"


class SignalStatus(enum.Enum):
    """Status of a trading signal"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


class TradeStatus(enum.Enum):
    """Status of a trade"""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class Signal(Base):
    """Trading signals generated from news"""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    
    # Signal details
    direction = Column(String(10), nullable=False)  # BUY or SELL
    confidence = Column(Integer, nullable=False)  # 0-100
    materiality = Column(Integer, nullable=False)  # 1-10
    
    # Source tracking - NEW FIELD
    source = Column(Enum(SignalSource), nullable=False, default=SignalSource.AGGREGATED)
    source_details = Column(JSON)  # Additional source info (which APIs contributed)
    
    # News that triggered the signal
    news_headline = Column(Text)
    news_summary = Column(Text)
    news_url = Column(String(500))
    news_published_at = Column(DateTime)
    
    # Pricing
    suggested_entry = Column(Float)
    suggested_stop_loss = Column(Float)
    suggested_take_profit = Column(Float)
    
    # Risk metrics
    risk_score = Column(Integer)  # 1-10
    position_size = Column(Float)
    
    # Status and timing
    status = Column(Enum(SignalStatus), default=SignalStatus.PENDING)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)
    
    # AI reasoning
    ai_reasoning = Column(Text)
    ai_model = Column(String(50))  # Which AI model generated this


class Trade(Base):
    """Executed trades"""
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer)  # Reference to signal
    ticker = Column(String(20), nullable=False)
    
    # Trade details
    direction = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    # Entry
    entry_price = Column(Float)
    entry_time = Column(DateTime)
    entry_order_id = Column(String(100))
    
    # Exit
    exit_price = Column(Float)
    exit_time = Column(DateTime)
    exit_order_id = Column(String(100))
    exit_reason = Column(String(50))  # stop_loss, take_profit, manual, eod
    
    # Risk management
    stop_loss = Column(Float)
    take_profit = Column(Float)
    trailing_stop = Column(Boolean, default=False)
    
    # P&L
    realized_pnl = Column(Float)
    realized_pnl_percent = Column(Float)
    commission = Column(Float)
    
    # Status
    status = Column(Enum(TradeStatus), default=TradeStatus.OPEN)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Position(Base):
    """Current open positions"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True)
    trade_id = Column(Integer)
    ticker = Column(String(20), nullable=False)
    
    # Position details
    quantity = Column(Integer, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float)
    
    # P&L
    unrealized_pnl = Column(Float)
    unrealized_pnl_percent = Column(Float)
    
    # Risk
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_amount = Column(Float)
    
    # Timing
    opened_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class WebhookLog(Base):
    """Log of all webhook events"""
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True)
    
    # Request details
    endpoint = Column(String(100))
    method = Column(String(10))
    headers = Column(JSON)
    payload = Column(JSON)
    
    # Response
    status_code = Column(Integer)
    response = Column(JSON)
    
    # Processing
    processed = Column(Boolean, default=False)
    signal_generated = Column(Boolean, default=False)
    error_message = Column(Text)
    
    # Timing
    received_at = Column(DateTime, default=func.now())
    processed_at = Column(DateTime)


class Performance(Base):
    """Daily performance metrics"""
    __tablename__ = "performance"
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, unique=True)
    
    # Trading stats
    trades_count = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    # P&L
    gross_pnl = Column(Float, default=0)
    commission = Column(Float, default=0)
    net_pnl = Column(Float, default=0)
    
    # Risk metrics
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    win_rate = Column(Float)
    
    # Capital
    starting_capital = Column(Float)
    ending_capital = Column(Float)
    
    created_at = Column(DateTime, default=func.now())


class Watchlist(Base):
    """Weekly watchlist of stocks to monitor"""
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    company_name = Column(String(100))
    exchange = Column(String(20))
    
    # Selection criteria
    selection_date = Column(DateTime, default=func.now())
    selection_reason = Column(Text)
    
    # Metrics at selection
    market_cap = Column(Float)
    avg_volume = Column(Float)
    volatility = Column(Float)
    
    # Monitoring
    is_active = Column(Boolean, default=True)
    news_count_today = Column(Integer, default=0)
    signals_generated = Column(Integer, default=0)
    
    # Performance
    trades_executed = Column(Integer, default=0)
    total_pnl = Column(Float, default=0)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class NewsCache(Base):
    """Cache for news articles to avoid duplicates"""
    __tablename__ = "news_cache"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20), nullable=False)
    
    # News details
    headline = Column(Text, nullable=False)
    url = Column(String(500))
    source = Column(String(50))
    api_source = Column(String(20))  # gemini, marketaux, finnhub
    
    # Content
    summary = Column(Text)
    sentiment = Column(String(20))
    materiality = Column(Integer)
    
    # Timing
    published_at = Column(DateTime)
    cached_at = Column(DateTime, default=func.now())
    
    # Processing
    processed = Column(Boolean, default=False)
    signal_generated = Column(Boolean, default=False)