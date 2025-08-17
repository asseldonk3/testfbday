from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Enum
from sqlalchemy.sql import func
from database import Base
import enum

class SignalType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class SignalStatus(enum.Enum):
    PENDING = "pending"
    ANALYZED = "analyzed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"

class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), nullable=False, index=True)
    exchange = Column(String(20))  # 'AMS', 'XETRA', 'EPA'
    signal_type = Column(Enum(SignalType), nullable=False)
    confidence = Column(Integer, nullable=False)  # 0-100
    
    # Price levels
    entry_price = Column(Float)
    stop_loss = Column(Float)
    target_price = Column(Float)
    
    # News and reasoning
    news_source = Column(Text)  # Gemini search results
    reasoning = Column(Text)
    materiality_score = Column(Integer)  # 1-10
    
    # Status tracking
    status = Column(Enum(SignalStatus), default=SignalStatus.PENDING)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True))
    
    def to_dict(self):
        return {
            "id": self.id,
            "ticker": self.ticker,
            "exchange": self.exchange,
            "signal_type": self.signal_type.value if self.signal_type else None,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "target_price": self.target_price,
            "reasoning": self.reasoning,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }