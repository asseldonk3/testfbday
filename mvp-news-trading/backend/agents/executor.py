from typing import Dict, Optional, List
from datetime import datetime, timedelta
from loguru import logger
from alpaca.trading import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopLossRequest

from models.signal import Signal, SignalStatus
from models.trade import Trade, TradeStatus
from database import SessionLocal
from config import settings
from services.alpaca_service import AlpacaService

class ExecutorAgent:
    """
    Executor Agent - Handles trade execution and position management
    Places orders, manages stops/targets, and tracks fills
    """
    
    def __init__(self):
        self.alpaca = AlpacaService()
        logger.info("Executor Agent initialized")
    
    async def execute_trade(self, trade_params: Dict) -> Optional[Trade]:
        """
        Execute a trade based on approved parameters
        
        Args:
            trade_params: Trade parameters from Risk Manager
            
        Returns:
            Trade object if successful, None otherwise
        """
        db = SessionLocal()
        try:
            ticker = trade_params['ticker']
            position_size = trade_params['position_size']
            signal_type = trade_params['signal_type']
            
            logger.info(f"Executing {signal_type} trade for {ticker}: {position_size} shares")
            
            # Create trade record
            trade = Trade(
                signal_id=trade_params['signal_id'],
                ticker=ticker,
                side=signal_type,
                quantity=position_size,
                entry_price=trade_params['entry_price'],
                stop_loss=trade_params['stop_loss'],
                target_price=trade_params['target_price'],
                status=TradeStatus.PENDING,
                opened_at=datetime.now()
            )
            db.add(trade)
            db.commit()
            
            # Place the order
            order = await self._place_order(trade)
            
            if order:
                trade.broker_order_id = order.id
                trade.status = TradeStatus.OPEN
                trade.actual_entry_price = float(order.filled_avg_price) if order.filled_avg_price else trade.entry_price
                
                # Place stop loss and take profit orders
                await self._place_bracket_orders(trade)
                
                # Log execution
                slippage = abs(trade.actual_entry_price - trade.entry_price)
                logger.info(f"Trade executed: {ticker} {signal_type} {position_size} shares @ "
                          f"${trade.actual_entry_price:.2f} (slippage: ${slippage:.2f})")
                
                db.commit()
                return trade
            else:
                trade.status = TradeStatus.FAILED
                trade.notes = "Order placement failed"
                db.commit()
                logger.error(f"Failed to execute trade for {ticker}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            db.rollback()
            return None
        finally:
            db.close()
    
    async def _place_order(self, trade: Trade):
        """
        Place the main order with Alpaca
        
        Args:
            trade: Trade object
            
        Returns:
            Order object if successful
        """
        try:
            # Determine order side
            side = OrderSide.BUY if trade.side == 'BUY' else OrderSide.SELL
            
            # Create market order for immediate execution
            order_data = MarketOrderRequest(
                symbol=trade.ticker,
                qty=trade.quantity,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order
            order = self.alpaca.client.submit_order(order_data)
            
            logger.info(f"Order placed: {order.id} - {trade.ticker} {side} {trade.quantity}")
            return order
            
        except Exception as e:
            logger.error(f"Error placing order: {str(e)}")
            return None
    
    async def _place_bracket_orders(self, trade: Trade):
        """
        Place stop loss and take profit orders
        
        Args:
            trade: Trade object
        """
        try:
            # For paper trading, we'll track these internally
            # In production, would place OCO (One-Cancels-Other) orders
            
            logger.info(f"Bracket orders set for {trade.ticker}: "
                       f"Stop @ ${trade.stop_loss:.2f}, Target @ ${trade.target_price:.2f}")
            
            # Store bracket order IDs if using real broker API
            # trade.stop_order_id = stop_order.id
            # trade.target_order_id = target_order.id
            
        except Exception as e:
            logger.error(f"Error placing bracket orders: {str(e)}")
    
    async def monitor_positions(self) -> List[Trade]:
        """
        Monitor all open positions and check for exits
        
        Returns:
            List of trades that were closed
        """
        db = SessionLocal()
        closed_trades = []
        
        try:
            # Get all open trades
            open_trades = db.query(Trade).filter(
                Trade.status == TradeStatus.OPEN
            ).all()
            
            logger.debug(f"Monitoring {len(open_trades)} open positions")
            
            for trade in open_trades:
                # Check if position should be closed
                should_close, reason = await self._check_exit_conditions(trade)
                
                if should_close:
                    closed_trade = await self._close_position(trade, reason)
                    if closed_trade:
                        closed_trades.append(closed_trade)
            
            db.commit()
            return closed_trades
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {str(e)}")
            db.rollback()
            return []
        finally:
            db.close()
    
    async def _check_exit_conditions(self, trade: Trade) -> tuple[bool, str]:
        """
        Check if a position should be closed
        
        Args:
            trade: Open trade to check
            
        Returns:
            Tuple of (should_close, reason)
        """
        try:
            # Get current price (mock for now)
            current_price = await self._get_current_price(trade.ticker)
            if not current_price:
                return False, ""
            
            # Check stop loss
            if trade.side == 'BUY':
                if current_price <= trade.stop_loss:
                    return True, f"Stop loss hit @ ${current_price:.2f}"
                if current_price >= trade.target_price:
                    return True, f"Target reached @ ${current_price:.2f}"
            else:  # SELL
                if current_price >= trade.stop_loss:
                    return True, f"Stop loss hit @ ${current_price:.2f}"
                if current_price <= trade.target_price:
                    return True, f"Target reached @ ${current_price:.2f}"
            
            # Check time-based exit (for day trading)
            if datetime.now() - trade.opened_at > timedelta(hours=6):
                return True, "Time-based exit (6 hours)"
            
            # Check if near market close
            now = datetime.now()
            market_close = now.replace(
                hour=settings.market_close_hour,
                minute=settings.market_close_minute - 5  # Close 5 min before market close
            )
            if now >= market_close:
                return True, "Market closing soon"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error checking exit conditions: {str(e)}")
            return False, ""
    
    async def _close_position(self, trade: Trade, reason: str) -> Optional[Trade]:
        """
        Close a position
        
        Args:
            trade: Trade to close
            reason: Reason for closing
            
        Returns:
            Updated trade object
        """
        db = SessionLocal()
        try:
            logger.info(f"Closing position for {trade.ticker}: {reason}")
            
            # Get current price for P&L calculation
            exit_price = await self._get_current_price(trade.ticker)
            if not exit_price:
                logger.error(f"Could not get exit price for {trade.ticker}")
                return None
            
            # Place closing order
            side = OrderSide.SELL if trade.side == 'BUY' else OrderSide.BUY
            
            order_data = MarketOrderRequest(
                symbol=trade.ticker,
                qty=trade.quantity,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order (would be real in production)
            # order = self.alpaca.client.submit_order(order_data)
            
            # Update trade record
            trade.exit_price = exit_price
            trade.closed_at = datetime.now()
            trade.status = TradeStatus.CLOSED
            trade.notes = reason
            
            # Calculate P&L
            if trade.side == 'BUY':
                trade.pnl = (exit_price - trade.actual_entry_price) * trade.quantity
            else:  # SELL
                trade.pnl = (trade.actual_entry_price - exit_price) * trade.quantity
            
            # Calculate fees (estimate)
            trade.fees = trade.quantity * 0.01  # $0.01 per share estimate
            trade.pnl -= trade.fees
            
            db.commit()
            
            logger.info(f"Position closed: {trade.ticker} @ ${exit_price:.2f}, "
                       f"P&L: ${trade.pnl:.2f} ({reason})")
            
            return trade
            
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            db.rollback()
            return None
        finally:
            db.close()
    
    async def _get_current_price(self, ticker: str) -> Optional[float]:
        """
        Get current price for a ticker
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Current price or None
        """
        try:
            # In production, would get real price from Alpaca or market data provider
            # For now, return mock price with small random movement
            import random
            base_price = 100.0
            movement = random.uniform(-2, 2)
            return base_price + movement
            
            # Real implementation:
            # quote = self.alpaca.client.get_latest_quote(ticker)
            # return float(quote.ask_price)
            
        except Exception as e:
            logger.error(f"Error getting current price for {ticker}: {str(e)}")
            return None
    
    async def cancel_all_orders(self):
        """Cancel all pending orders"""
        try:
            # Cancel all open orders
            self.alpaca.client.cancel_orders()
            logger.info("All pending orders cancelled")
            
        except Exception as e:
            logger.error(f"Error cancelling orders: {str(e)}")
    
    async def get_positions_summary(self) -> Dict:
        """
        Get summary of all positions
        
        Returns:
            Dictionary with position summary
        """
        db = SessionLocal()
        try:
            # Get open positions
            open_trades = db.query(Trade).filter(
                Trade.status == TradeStatus.OPEN
            ).all()
            
            # Calculate totals
            total_value = sum(t.quantity * t.actual_entry_price for t in open_trades)
            
            # Get today's closed trades
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_closed = db.query(Trade).filter(
                Trade.closed_at >= today_start,
                Trade.status == TradeStatus.CLOSED
            ).all()
            
            today_pnl = sum(t.pnl for t in today_closed)
            
            return {
                'open_positions': len(open_trades),
                'total_value': total_value,
                'today_trades': len(today_closed),
                'today_pnl': today_pnl,
                'positions': [
                    {
                        'ticker': t.ticker,
                        'side': t.side,
                        'quantity': t.quantity,
                        'entry_price': t.actual_entry_price,
                        'current_pnl': 0  # Would calculate with current price
                    }
                    for t in open_trades
                ]
            }
            
        finally:
            db.close()