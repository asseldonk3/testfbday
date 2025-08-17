from alpaca.trading import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from typing import Dict, List, Optional
from loguru import logger
from config import settings
from datetime import datetime

class AlpacaService:
    """Service for interacting with Alpaca paper trading API"""
    
    def __init__(self):
        """Initialize Alpaca clients"""
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            logger.error("Alpaca API keys not found")
            raise ValueError("Alpaca API keys are required")
        
        # Trading client for orders
        self.trading_client = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=True  # Always use paper trading
        )
        
        # Data client for market data
        self.data_client = StockHistoricalDataClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key
        )
        
        logger.info("Alpaca service initialized for paper trading")
    
    def get_account_info(self) -> Dict:
        """Get account information"""
        try:
            account = self.trading_client.get_account()
            return {
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "day_trade_count": account.daytrade_count,
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "account_blocked": account.account_blocked,
                "currency": account.currency
            }
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return None
    
    def get_positions(self) -> List[Dict]:
        """Get all current positions"""
        try:
            positions = self.trading_client.get_all_positions()
            return [
                {
                    "symbol": pos.symbol,
                    "qty": float(pos.qty),
                    "side": pos.side.value if pos.side else None,
                    "market_value": float(pos.market_value) if pos.market_value else 0,
                    "cost_basis": float(pos.cost_basis) if pos.cost_basis else 0,
                    "unrealized_pl": float(pos.unrealized_pl) if pos.unrealized_pl else 0,
                    "unrealized_plpc": float(pos.unrealized_plpc) if pos.unrealized_plpc else 0,
                    "current_price": float(pos.current_price) if pos.current_price else 0,
                    "avg_entry_price": float(pos.avg_entry_price) if pos.avg_entry_price else 0
                }
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Error getting positions: {str(e)}")
            return []
    
    def place_market_order(
        self, 
        symbol: str, 
        qty: int, 
        side: str,
        time_in_force: str = "day"
    ) -> Optional[Dict]:
        """
        Place a market order
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            qty: Number of shares
            side: 'buy' or 'sell'
            time_in_force: 'day', 'gtc', 'ioc', 'fok'
            
        Returns:
            Order details or None if failed
        """
        try:
            # Convert string to enum
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            tif = TimeInForce.DAY if time_in_force.lower() == 'day' else TimeInForce.GTC
            
            # Create order request
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif
            )
            
            # Submit order
            order = self.trading_client.submit_order(order_data)
            
            logger.info(f"Market order placed: {side} {qty} {symbol}")
            
            return {
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty) if order.qty else 0,
                "side": order.side.value if order.side else None,
                "status": order.status.value if order.status else None,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None
            }
            
        except Exception as e:
            logger.error(f"Error placing market order: {str(e)}")
            return None
    
    def place_limit_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        limit_price: float,
        time_in_force: str = "day"
    ) -> Optional[Dict]:
        """Place a limit order"""
        try:
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL
            tif = TimeInForce.DAY if time_in_force.lower() == 'day' else TimeInForce.GTC
            
            order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif,
                limit_price=limit_price
            )
            
            order = self.trading_client.submit_order(order_data)
            
            logger.info(f"Limit order placed: {side} {qty} {symbol} @ ${limit_price}")
            
            return {
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty) if order.qty else 0,
                "side": order.side.value if order.side else None,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "status": order.status.value if order.status else None
            }
            
        except Exception as e:
            logger.error(f"Error placing limit order: {str(e)}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID"""
        try:
            self.trading_client.cancel_order_by_id(order_id)
            logger.info(f"Order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order details by ID"""
        try:
            order = self.trading_client.get_order_by_id(order_id)
            return {
                "id": order.id,
                "symbol": order.symbol,
                "qty": float(order.qty) if order.qty else 0,
                "filled_qty": float(order.filled_qty) if order.filled_qty else 0,
                "status": order.status.value if order.status else None,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None
            }
        except Exception as e:
            logger.error(f"Error getting order: {str(e)}")
            return None
    
    def get_all_orders(self, status: str = "all", limit: int = 50) -> List[Dict]:
        """Get all orders with optional status filter"""
        try:
            request = GetOrdersRequest(
                status=status,
                limit=limit
            )
            orders = self.trading_client.get_orders(request)
            
            return [
                {
                    "id": order.id,
                    "symbol": order.symbol,
                    "qty": float(order.qty) if order.qty else 0,
                    "side": order.side.value if order.side else None,
                    "status": order.status.value if order.status else None,
                    "created_at": order.created_at.isoformat() if order.created_at else None
                }
                for order in orders
            ]
        except Exception as e:
            logger.error(f"Error getting orders: {str(e)}")
            return []
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict]:
        """Get latest quote for a symbol"""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.data_client.get_stock_latest_quote(request)
            
            if symbol in quotes:
                quote = quotes[symbol]
                return {
                    "symbol": symbol,
                    "ask_price": float(quote.ask_price) if quote.ask_price else 0,
                    "bid_price": float(quote.bid_price) if quote.bid_price else 0,
                    "ask_size": quote.ask_size,
                    "bid_size": quote.bid_size,
                    "timestamp": quote.timestamp.isoformat() if quote.timestamp else None
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {str(e)}")
            return None
    
    def close_position(self, symbol: str) -> bool:
        """Close a position completely"""
        try:
            self.trading_client.close_position(symbol)
            logger.info(f"Position closed for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
            return False
    
    def close_all_positions(self) -> bool:
        """Close all open positions"""
        try:
            self.trading_client.close_all_positions()
            logger.info("All positions closed")
            return True
        except Exception as e:
            logger.error(f"Error closing all positions: {str(e)}")
            return False