from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum

class TradeStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    PENDING = "pending"

class TradeSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"))
    
    # Trade details
    ticker = Column(String(10), nullable=False, index=True)
    side = Column(Enum(TradeSide), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    # Prices
    entry_price = Column(Float)
    exit_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    
    # Performance
    pnl = Column(Float, default=0.0)
    pnl_percentage = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    
    # Status
    status = Column(Enum(TradeStatus), default=TradeStatus.PENDING)
    is_paper = Column(Boolean, default=True)  # Paper trading flag
    
    # Alpaca order IDs
    entry_order_id = Column(String(100))
    exit_order_id = Column(String(100))
    
    # Risk metrics
    risk_amount = Column(Float)  # Amount at risk
    position_size = Column(Float)  # Total position value
    
    # Timestamps
    opened_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def calculate_pnl(self):
        if self.exit_price and self.entry_price and self.quantity:
            if self.side == TradeSide.BUY:
                self.pnl = (self.exit_price - self.entry_price) * self.quantity - self.commission
            else:
                self.pnl = (self.entry_price - self.exit_price) * self.quantity - self.commission
            
            self.pnl_percentage = (self.pnl / (self.entry_price * self.quantity)) * 100
    
    def to_dict(self):
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "ticker": self.ticker,
            "side": self.side.value if self.side else None,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "pnl": self.pnl,
            "pnl_percentage": self.pnl_percentage,
            "status": self.status.value if self.status else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None
        }