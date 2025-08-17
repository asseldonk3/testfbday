#!/usr/bin/env python3
"""
Minimal API test without database dependency
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
from alpaca.trading import TradingClient
import google.generativeai as genai

# Load environment
load_dotenv()

# Initialize services
alpaca_client = TradingClient(
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    paper=True
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-1.5-flash')

# Create FastAPI app
app = FastAPI(title="MVP News Trading - Test API")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class NewsAnalysisRequest(BaseModel):
    ticker: str
    news_text: str

class TradingSignal(BaseModel):
    ticker: str
    signal: str  # BUY, SELL, HOLD
    confidence: float
    reasoning: str
    timestamp: datetime

# Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "MVP News Trading API",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/account")
async def get_account():
    """Get Alpaca account info"""
    try:
        account = alpaca_client.get_account()
        return {
            "status": str(account.status),
            "buying_power": float(account.buying_power),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
            "currency": account.currency
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze", response_model=TradingSignal)
async def analyze_news(request: NewsAnalysisRequest):
    """Analyze news using Gemini AI"""
    try:
        prompt = f"""
        Analyze this news about {request.ticker} and provide a trading signal.
        
        News: {request.news_text}
        
        Respond in JSON format with:
        - signal: BUY, SELL, or HOLD
        - confidence: 0-100
        - reasoning: brief explanation
        """
        
        response = gemini_model.generate_content(prompt)
        
        # Parse response (simplified - in production use proper JSON parsing)
        import json
        import re
        
        # Extract JSON from response
        text = response.text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if json_match:
            data = json.loads(json_match.group())
        else:
            # Fallback
            data = {
                "signal": "HOLD",
                "confidence": 50,
                "reasoning": "Could not parse AI response"
            }
        
        return TradingSignal(
            ticker=request.ticker,
            signal=data.get("signal", "HOLD"),
            confidence=data.get("confidence", 50),
            reasoning=data.get("reasoning", "AI analysis"),
            timestamp=datetime.now()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/positions")
async def get_positions():
    """Get current positions from Alpaca"""
    try:
        positions = alpaca_client.get_all_positions()
        return [
            {
                "symbol": p.symbol,
                "qty": float(p.qty),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl) if p.unrealized_pl else 0
            }
            for p in positions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting test API server...")
    print("📍 Access at: http://localhost:8000")
    print("📚 API docs at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)