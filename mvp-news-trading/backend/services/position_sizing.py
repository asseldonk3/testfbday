"""
Position Sizing Service
Manages position sizes with simulated $2000 capital limit
"""
from typing import Dict, Optional
from loguru import logger
from config import settings
from datetime import datetime
from sqlalchemy.orm import Session

class PositionSizer:
    """
    Calculate position sizes based on risk management rules
    Uses simulated $2000 capital instead of full paper account balance
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.simulated_capital = settings.starting_capital  # $2000
        self.max_risk_per_trade = settings.max_risk_per_trade  # 2%
        
    def get_available_capital(self) -> float:
        """
        Get available capital for trading
        Returns simulated capital minus current positions
        """
        from models import Trade
        from models.trade import TradeStatus
        
        # Get all open trades
        open_trades = self.db.query(Trade).filter(
            Trade.status == TradeStatus.OPEN
        ).all()
        
        # Calculate capital in use
        capital_in_use = sum(trade.entry_price * trade.quantity for trade in open_trades)
        
        # Available capital
        available = self.simulated_capital - capital_in_use
        
        logger.info(f"Available capital: ${available:.2f} of ${self.simulated_capital:.2f}")
        return max(0, available)
    
    def calculate_position_size(
        self, 
        entry_price: float, 
        stop_loss: float,
        confidence: int = 70
    ) -> Dict:
        """
        Calculate position size using Kelly Criterion with risk limits
        
        Args:
            entry_price: Expected entry price
            stop_loss: Stop loss price
            confidence: Signal confidence (0-100)
            
        Returns:
            Dictionary with position details
        """
        available_capital = self.get_available_capital()
        
        # Check if we have capital
        if available_capital < 100:  # Minimum $100 per trade
            return {
                "shares": 0,
                "position_value": 0,
                "risk_amount": 0,
                "message": "Insufficient capital (min $100 per trade)"
            }
        
        # Calculate risk per share
        risk_per_share = abs(entry_price - stop_loss)
        
        if risk_per_share == 0:
            return {
                "shares": 0,
                "position_value": 0,
                "risk_amount": 0,
                "message": "Invalid stop loss (same as entry)"
            }
        
        # Maximum risk amount (2% of simulated capital)
        max_risk = self.simulated_capital * self.max_risk_per_trade
        
        # Adjust risk based on confidence (Kelly Criterion simplified)
        # Higher confidence = larger position (within limits)
        confidence_factor = min(1.0, confidence / 100.0)
        adjusted_risk = max_risk * confidence_factor
        
        # Calculate shares based on risk
        shares = int(adjusted_risk / risk_per_share)
        
        # Check position value doesn't exceed available capital
        position_value = shares * entry_price
        if position_value > available_capital:
            # Adjust shares to fit available capital
            shares = int(available_capital / entry_price)
            position_value = shares * entry_price
        
        # Ensure minimum position size
        if shares < 1:
            return {
                "shares": 0,
                "position_value": 0,
                "risk_amount": 0,
                "message": "Position too small (less than 1 share)"
            }
        
        # Calculate actual risk
        actual_risk = shares * risk_per_share
        
        return {
            "shares": shares,
            "position_value": position_value,
            "risk_amount": actual_risk,
            "risk_percentage": (actual_risk / self.simulated_capital) * 100,
            "stop_loss": stop_loss,
            "entry_price": entry_price,
            "message": f"Position sized for ${self.simulated_capital:.0f} capital"
        }
    
    def check_daily_loss_limit(self) -> bool:
        """
        Check if daily loss limit has been reached
        Returns True if trading should continue, False if limit reached
        """
        from models import Trade
        from models.trade import TradeStatus
        from sqlalchemy import func
        
        # Get today's closed trades
        today = datetime.now().date()
        today_trades = self.db.query(Trade).filter(
            func.date(Trade.closed_at) == today,
            Trade.status == TradeStatus.CLOSED
        ).all()
        
        # Calculate today's P&L
        daily_pnl = sum(trade.profit_loss for trade in today_trades if trade.profit_loss)
        
        # Check against limit (5% of simulated capital)
        max_daily_loss = self.simulated_capital * settings.max_daily_loss
        
        if daily_pnl < -max_daily_loss:
            logger.warning(f"Daily loss limit reached: ${daily_pnl:.2f} exceeds ${-max_daily_loss:.2f}")
            return False
        
        return True
    
    def check_trade_count_limit(self) -> bool:
        """
        Check if daily trade count limit has been reached
        Returns True if can trade, False if limit reached
        """
        from models import Trade
        from sqlalchemy import func
        
        # Count today's trades
        today = datetime.now().date()
        today_count = self.db.query(Trade).filter(
            func.date(Trade.created_at) == today
        ).count()
        
        if today_count >= settings.max_trades_per_day:
            logger.warning(f"Daily trade limit reached: {today_count} trades")
            return False
            
        return True
    
    def can_trade(self) -> Dict:
        """
        Check all risk limits to determine if trading is allowed
        
        Returns:
            Dictionary with status and reasons
        """
        reasons = []
        can_trade = True
        
        # Check daily loss limit
        if not self.check_daily_loss_limit():
            can_trade = False
            reasons.append("Daily loss limit reached")
        
        # Check trade count
        if not self.check_trade_count_limit():
            can_trade = False
            reasons.append("Daily trade count limit reached")
        
        # Check available capital
        available = self.get_available_capital()
        if available < 100:
            can_trade = False
            reasons.append(f"Insufficient capital (${available:.2f} < $100)")
        
        return {
            "can_trade": can_trade,
            "available_capital": available,
            "simulated_capital": self.simulated_capital,
            "reasons": reasons if not can_trade else ["All checks passed"]
        }