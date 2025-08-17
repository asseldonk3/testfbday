#!/usr/bin/env python3
"""
Test various services individually
"""
import os
import asyncio
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def test_environment():
    """Test if environment variables are loaded"""
    print("=" * 50)
    print("TESTING ENVIRONMENT VARIABLES")
    print("=" * 50)
    
    required_vars = [
        "ALPACA_API_KEY",
        "ALPACA_SECRET_KEY", 
        "GEMINI_API_KEY",
        "DATABASE_URL"
    ]
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:20]}...")
        else:
            print(f"❌ {var}: Not set")
    print()

def test_alpaca():
    """Test Alpaca API connection"""
    print("=" * 50)
    print("TESTING ALPACA API")
    print("=" * 50)
    
    try:
        from alpaca.trading import TradingClient
        
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        
        client = TradingClient(api_key=api_key, secret_key=secret_key, paper=True)
        account = client.get_account()
        
        print(f"✅ Alpaca connected!")
        print(f"   Account Status: {account.status}")
        print(f"   Buying Power: ${account.buying_power}")
        print(f"   Portfolio Value: ${account.portfolio_value}")
    except Exception as e:
        print(f"❌ Alpaca failed: {e}")
    print()

async def test_gemini():
    """Test Gemini AI API"""
    print("=" * 50)
    print("TESTING GEMINI AI")
    print("=" * 50)
    
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not set")
            return
            
        genai.configure(api_key=api_key)
        
        # Simple model without tools
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Test with a simple prompt
        response = model.generate_content(
            "What is the stock ticker for Apple Inc? Reply with just the ticker symbol."
        )
        
        print(f"✅ Gemini connected!")
        print(f"   Test response: {response.text}")
        
        # Test news search prompt
        prompt = """
        You are a financial news scout. 
        Search for recent news about Apple (AAPL).
        Return a brief summary in JSON format with:
        - ticker
        - sentiment (bullish/bearish/neutral)
        - key_points (list of 2-3 points)
        """
        
        response = model.generate_content(prompt)
        print(f"   News search test: {response.text[:200]}...")
        
    except Exception as e:
        print(f"❌ Gemini failed: {e}")
    print()

def test_scout_agent():
    """Test if Scout agent can be imported"""
    print("=" * 50)
    print("TESTING SCOUT AGENT")
    print("=" * 50)
    
    try:
        from backend.agents.scout import ScoutAgent
        print("✅ Scout agent imports successfully")
        
        # Try to create instance
        scout = ScoutAgent()
        print("✅ Scout agent instance created")
        
    except ImportError as e:
        print(f"❌ Scout agent import failed: {e}")
    except Exception as e:
        print(f"❌ Scout agent initialization failed: {e}")
    print()

async def main():
    """Run all tests"""
    print("\n🚀 MVP NEWS TRADING SYSTEM - SERVICE TESTS\n")
    
    # Test environment
    test_environment()
    
    # Test Alpaca
    test_alpaca()
    
    # Test Gemini
    await test_gemini()
    
    # Test Scout Agent
    test_scout_agent()
    
    print("\n✨ Tests complete!\n")
    print("Next steps to test:")
    print("1. Start the FastAPI server (after fixing DB connection)")
    print("2. Test the API endpoints")
    print("3. Test the webhook handler")
    print("4. Test the scheduler for periodic tasks")

if __name__ == "__main__":
    asyncio.run(main())