from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import func

from models.signal import Signal, SignalStatus
from models.trade import Trade, TradeStatus
from models.portfolio import Portfolio
from database import SessionLocal
from config import settings
from services.position_sizing import PositionSizer
from services.alpaca_service import AlpacaService

class RiskManagerAgent:
    """
    Risk Manager Agent - Enforces hard risk rules and validates trades
    Implements position sizing, daily limits, and risk assessment
    """
    
    def __init__(self):
        self.alpaca = AlpacaService()
        
        # Risk parameters from settings
        self.max_trades_per_day = settings.max_trades_per_day
        self.max_risk_per_trade = settings.max_risk_per_trade
        self.max_daily_loss = settings.max_daily_loss
        self.max_consecutive_losses = 3
        
        logger.info(f"Risk Manager initialized - Max trades/day: {self.max_trades_per_day}, "
                   f"Max risk/trade: {self.max_risk_per_trade*100}%")
    
    async def validate_signal(self, signal: Signal) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate a signal against all risk rules
        
        Args:
            signal: Signal to validate
            
        Returns:
            Tuple of (approved, rejection_reason, trade_params if approved)
        """
        db = SessionLocal()
        try:
            logger.info(f"Validating signal for {signal.ticker}")
            
            # Get current portfolio state
            portfolio_value = await self._get_portfolio_value()
            daily_stats = await self._get_daily_trading_stats(db)
            
            # Run all risk checks
            checks = {
                'daily_trade_limit': self._check_daily_trade_limit(daily_stats),
                'daily_loss_limit': self._check_daily_loss_limit(daily_stats, portfolio_value),
                'consecutive_losses': self._check_consecutive_losses(db),
                'market_hours': self._check_market_hours(),
                'position_correlation': await self._check_position_correlation(signal.ticker),
                'spread_check': await self._check_spread(signal.ticker, signal.entry_price),
            }
            
            # Log all check results
            for check_name, (passed, reason) in checks.items():
                if not passed:
                    logger.warning(f"Risk check failed - {check_name}: {reason}")
                    signal.status = SignalStatus.REJECTED
                    signal.reasoning = f"Risk check failed: {reason}"
                    db.commit()
                    return False, reason, None
            
            # All checks passed - calculate position size
            position_sizer = PositionSizer(db)
            position_size_data = position_sizer.calculate_position_size(
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                confidence=signal.confidence
            )
            position_size = position_size_data['shares']
            
            # Alternative simple calculation
            if position_size < 1:
                position_size = self._calculate_simple_position_size(
                portfolio_value=portfolio_value,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                max_risk_percentage=self.max_risk_per_trade
            )
            
            if position_size < 1:
                reason = "Position size too small (< 1 share)"
                signal.status = SignalStatus.REJECTED
                signal.reasoning = reason
                db.commit()
                return False, reason, None
            
            # Calculate risk metrics
            risk_amount = position_size * abs(signal.entry_price - signal.stop_loss)
            risk_percentage = (risk_amount / portfolio_value) * 100
            potential_profit = position_size * abs(signal.target_price - signal.entry_price)
            risk_reward_ratio = potential_profit / risk_amount if risk_amount > 0 else 0
            
            # Prepare trade parameters
            trade_params = {
                'ticker': signal.ticker,
                'signal_id': signal.id,
                'position_size': position_size,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'target_price': signal.target_price,
                'risk_amount': risk_amount,
                'risk_percentage': risk_percentage,
                'potential_profit': potential_profit,
                'risk_reward_ratio': risk_reward_ratio,
                'signal_type': signal.signal_type
            }
            
            # Update signal status
            signal.status = SignalStatus.APPROVED
            signal.reasoning += f" | Risk approved: {risk_percentage:.2f}% risk, R:R {risk_reward_ratio:.2f}"
            db.commit()
            
            logger.info(f"Signal approved for {signal.ticker}: {position_size} shares, "
                       f"Risk: ${risk_amount:.2f} ({risk_percentage:.2f}%), R:R: {risk_reward_ratio:.2f}")
            
            return True, "", trade_params
            
        except Exception as e:
            logger.error(f"Error validating signal: {str(e)}")
            return False, f"Validation error: {str(e)}", None
        finally:
            db.close()
    
    def _check_daily_trade_limit(self, daily_stats: Dict) -> Tuple[bool, str]:
        """Check if daily trade limit has been reached"""
        trades_today = daily_stats.get('trades_today', 0)
        if trades_today >= self.max_trades_per_day:
            return False, f"Daily trade limit reached ({trades_today}/{self.max_trades_per_day})"
        return True, ""
    
    def _check_daily_loss_limit(self, daily_stats: Dict, portfolio_value: float) -> Tuple[bool, str]:
        """Check if daily loss limit has been reached"""
        daily_pnl = daily_stats.get('daily_pnl', 0)
        max_loss = -self.max_daily_loss * portfolio_value
        
        if daily_pnl <= max_loss:
            return False, f"Daily loss limit reached (${daily_pnl:.2f} / ${max_loss:.2f})"
        return True, ""
    
    def _check_consecutive_losses(self, db) -> Tuple[bool, str]:
        """Check for consecutive losses"""
        # Get last N trades
        recent_trades = db.query(Trade).filter(
            Trade.status == TradeStatus.CLOSED
        ).order_by(Trade.closed_at.desc()).limit(self.max_consecutive_losses).all()
        
        if len(recent_trades) >= self.max_consecutive_losses:
            consecutive_losses = all(trade.pnl < 0 for trade in recent_trades)
            if consecutive_losses:
                return False, f"Max consecutive losses reached ({self.max_consecutive_losses})"
        
        return True, ""
    
    def _check_market_hours(self) -> Tuple[bool, str]:
        """Check if within trading hours"""
        now = datetime.now()
        current_time = now.time()
        
        # Define restricted times (first and last 15 minutes)
        market_open = datetime.strptime(f"{settings.market_open_hour}:00", "%H:%M").time()
        market_close = datetime.strptime(f"{settings.market_close_hour}:{settings.market_close_minute}", "%H:%M").time()
        
        restricted_open_end = datetime.strptime(f"{settings.market_open_hour}:15", "%H:%M").time()
        restricted_close_start = datetime.strptime(f"{settings.market_close_hour}:{settings.market_close_minute-15}", "%H:%M").time()
        
        # Check if in restricted period
        if current_time < market_open or current_time > market_close:
            return False, "Outside market hours"
        
        if current_time <= restricted_open_end:
            return False, "Within first 15 minutes of market open"
        
        if current_time >= restricted_close_start:
            return False, "Within last 15 minutes of market close"
        
        return True, ""
    
    async def _check_position_correlation(self, ticker: str) -> Tuple[bool, str]:
        """Check correlation with existing positions"""
        try:
            # For now, simple check - don't allow same ticker twice
            db = SessionLocal()
            try:
                existing_position = db.query(Trade).filter(
                    Trade.ticker == ticker,
                    Trade.status == TradeStatus.OPEN
                ).first()
                
                if existing_position:
                    return False, f"Already have open position in {ticker}"
                
                # Could add sector correlation checks here
                return True, ""
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error checking position correlation: {str(e)}")
            return False, "Could not verify position correlation"
    
    async def _check_spread(self, ticker: str, entry_price: float) -> Tuple[bool, str]:
        """Check bid-ask spread"""
        try:
            # For EU stocks, we might not have real-time spread data
            # Use a conservative default
            max_spread_percentage = 0.005  # 0.5%
            
            # In production, would get real quote data
            # quote = await self.alpaca.get_latest_quote(ticker)
            # if quote:
            #     spread = (quote.ask_price - quote.bid_price) / quote.ask_price
            #     if spread > max_spread_percentage:
            #         return False, f"Spread too wide: {spread*100:.2f}%"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error checking spread: {str(e)}")
            return True, ""  # Don't block on spread check failures
    
    def _calculate_simple_position_size(self, portfolio_value: float, entry_price: float, 
                                       stop_loss: float, max_risk_percentage: float) -> int:
        """Simple position size calculation"""
        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return 0
        
        max_risk_amount = portfolio_value * max_risk_percentage
        position_size = int(max_risk_amount / risk_per_share)
        
        return max(1, min(position_size, 100))  # Min 1, max 100 shares
    
    async def _get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        try:
            account = self.alpaca.client.get_account()
            return float(account.portfolio_value)
        except:
            # Fallback to configured starting capital
            return settings.starting_capital
    
    async def _get_daily_trading_stats(self, db) -> Dict:
        """Get today's trading statistics"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Count today's trades
        trades_today = db.query(func.count(Trade.id)).filter(
            Trade.opened_at >= today_start
        ).scalar() or 0
        
        # Calculate today's P&L
        daily_pnl = db.query(func.sum(Trade.pnl)).filter(
            Trade.closed_at >= today_start,
            Trade.status == TradeStatus.CLOSED
        ).scalar() or 0.0
        
        return {
            'trades_today': trades_today,
            'daily_pnl': daily_pnl
        }
    
    async def update_portfolio_metrics(self):
        """Update portfolio metrics at end of day"""
        db = SessionLocal()
        try:
            today = datetime.now().date()
            
            # Get or create today's portfolio record
            portfolio = db.query(Portfolio).filter(
                Portfolio.date == today
            ).first()
            
            if not portfolio:
                portfolio = Portfolio(
                    date=today,
                    starting_balance=settings.starting_capital
                )
                db.add(portfolio)
            
            # Calculate metrics
            daily_stats = await self._get_daily_trading_stats(db)
            
            # Get all closed trades today
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = db.query(Trade).filter(
                Trade.closed_at >= today_start,
                Trade.status == TradeStatus.CLOSED
            ).all()
            
            winning_trades = sum(1 for t in today_trades if t.pnl > 0)
            losing_trades = sum(1 for t in today_trades if t.pnl < 0)
            
            # Update portfolio record
            portfolio.ending_balance = portfolio.starting_balance + daily_stats['daily_pnl']
            portfolio.daily_pnl = daily_stats['daily_pnl']
            portfolio.total_trades = len(today_trades)
            portfolio.winning_trades = winning_trades
            portfolio.losing_trades = losing_trades
            
            db.commit()
            
            logger.info(f"Portfolio updated: P&L: ${daily_stats['daily_pnl']:.2f}, "
                       f"Trades: {len(today_trades)} (W:{winning_trades}/L:{losing_trades})")
            
        except Exception as e:
            logger.error(f"Error updating portfolio metrics: {str(e)}")
            db.rollback()
        finally:
            db.close()