from sqlalchemy import Column, Integer, Float, Date, DateTime, String
from sqlalchemy.sql import func
from database import Base
from datetime import date

class Portfolio(Base):
    __tablename__ = "portfolio"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Current state
    current_balance = Column(Float, nullable=False)
    initial_balance = Column(Float, nullable=False)
    
    # Open positions
    open_positions = Column(Integer, default=0)
    total_exposure = Column(Float, default=0.0)  # Total value in positions
    
    # Performance metrics
    total_pnl = Column(Float, default=0.0)
    total_pnl_percentage = Column(Float, default=0.0)
    
    # Risk metrics
    max_drawdown = Column(Float, default=0.0)
    current_drawdown = Column(Float, default=0.0)
    
    # Trade statistics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    # Average metrics
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def calculate_metrics(self):
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
        
        self.total_pnl = self.current_balance - self.initial_balance
        self.total_pnl_percentage = (self.total_pnl / self.initial_balance) * 100
        
        # Calculate drawdown
        if self.current_balance < self.initial_balance:
            self.current_drawdown = ((self.initial_balance - self.current_balance) / self.initial_balance) * 100
    
    def to_dict(self):
        return {
            "current_balance": self.current_balance,
            "initial_balance": self.initial_balance,
            "total_pnl": self.total_pnl,
            "total_pnl_percentage": self.total_pnl_percentage,
            "open_positions": self.open_positions,
            "total_exposure": self.total_exposure,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "max_drawdown": self.max_drawdown,
            "current_drawdown": self.current_drawdown
        }

class DailyPerformance(Base):
    __tablename__ = "daily_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    
    # Daily metrics
    starting_balance = Column(Float, nullable=False)
    ending_balance = Column(Float, nullable=False)
    daily_pnl = Column(Float, default=0.0)
    daily_pnl_percentage = Column(Float, default=0.0)
    
    # Trade statistics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    
    # Risk metrics
    max_position_size = Column(Float, default=0.0)
    total_commission = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def calculate_daily_metrics(self):
        self.daily_pnl = self.ending_balance - self.starting_balance
        self.daily_pnl_percentage = (self.daily_pnl / self.starting_balance) * 100
    
    def to_dict(self):
        return {
            "date": self.date.isoformat() if self.date else None,
            "starting_balance": self.starting_balance,
            "ending_balance": self.ending_balance,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_percentage": self.daily_pnl_percentage,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades
        }