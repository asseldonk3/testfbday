#!/usr/bin/env python3
"""
Test Alpaca API connection directly
"""
import os
from dotenv import load_dotenv
from alpaca.trading import TradingClient

# Load environment variables
load_dotenv()

# Get credentials
api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")

print(f"API Key: {api_key[:10]}...")
print(f"Secret Key: {secret_key[:10]}...")

# Try to connect
try:
    # Create trading client for paper trading
    trading_client = TradingClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=True
    )
    
    # Get account info
    account = trading_client.get_account()
    
    print("\n✅ Connection successful!")
    print(f"Account Status: {account.status}")
    print(f"Buying Power: ${account.buying_power}")
    print(f"Cash: ${account.cash}")
    print(f"Portfolio Value: ${account.portfolio_value}")
    print(f"Currency: {account.currency}")
    print(f"Pattern Day Trader: {account.pattern_day_trader}")
    
except Exception as e:
    print(f"\n❌ Connection failed: {str(e)}")
    print("\nPossible issues:")
    print("1. API keys might be for live trading instead of paper trading")
    print("2. API keys might be expired or revoked")
    print("3. Account might not be activated for paper trading")
    print("\nTo get paper trading keys:")
    print("1. Log into https://app.alpaca.markets/")
    print("2. Switch to Paper Trading mode (toggle in top right)")
    print("3. Go to API Keys section")
    print("4. Generate new keys specifically for paper trading")