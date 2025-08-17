import os
from typing import List
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://trader:tradingpass123@localhost:5432/trading_db")
    
    # API Keys
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    alpaca_api_key: str = os.getenv("ALPACA_API_KEY", "")
    alpaca_secret_key: str = os.getenv("ALPACA_SECRET_KEY", "")
    alpaca_base_url: str = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
    
    # News API Keys
    marketaux_api_key: str = os.getenv("MARKETAUX_API_KEY", "")
    finnhub_api_key: str = os.getenv("FINNHUB_API_KEY", "")
    
    # Telegram
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Webhook
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "")
    
    # Trading Configuration
    max_trades_per_day: int = 3
    max_risk_per_trade: float = 0.02  # 2% risk per trade
    max_daily_loss: float = 0.05  # 5% max daily loss
    starting_capital: float = 2000.0  # Simulated capital limit (actual paper account has $100k)
    
    # Agent Settings
    scout_interval_minutes: int = 30
    confidence_threshold: int = 70
    min_liquidity: int = 10000000  # 10M daily volume
    
    # Market Configuration
    market_open_hour: int = 9  # 9:00 CET
    market_close_hour: int = 17  # 17:30 CET
    market_close_minute: int = 30
    
    # EU Stocks Watchlist (Top 10 liquid stocks)
    watchlist: List[str] = [
        "ASML.AS",  # ASML - Amsterdam
        "SHEL.AS",  # Shell - Amsterdam
        "UNA.AS",   # Unilever - Amsterdam
        "SAP.DE",   # SAP - Frankfurt
        "SIE.DE",   # Siemens - Frankfurt
        "MC.PA",    # LVMH - Paris
        "TTE.PA",   # TotalEnergies - Paris
        "NESN.SW",  # Nestle - Swiss
        "NOVN.SW",  # Novartis - Swiss
        "INGA.AS",  # ING - Amsterdam
    ]
    
    # Application Settings
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()