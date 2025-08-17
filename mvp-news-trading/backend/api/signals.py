from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from models.signal import Signal, SignalStatus
from agents.scout import ScoutAgent

router = APIRouter()

@router.get("/active")
async def get_active_signals(db: Session = Depends(get_db)):
    """Get all active signals"""
    signals = db.query(Signal).filter(
        Signal.status.in_([SignalStatus.PENDING, SignalStatus.APPROVED])
    ).all()
    
    return {
        "count": len(signals),
        "signals": [s.to_dict() for s in signals]
    }

@router.get("/all")
async def get_all_signals(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all signals with limit"""
    signals = db.query(Signal).order_by(
        Signal.created_at.desc()
    ).limit(limit).all()
    
    return {
        "count": len(signals),
        "signals": [s.to_dict() for s in signals]
    }

@router.post("/scan/{ticker}")
async def scan_ticker_news(ticker: str):
    """Manually trigger news scan for a specific ticker"""
    scout = ScoutAgent()
    
    # Convert ticker to proper format if needed
    if not any(ticker.endswith(suffix) for suffix in ['.AS', '.DE', '.PA', '.SW']):
        ticker = f"{ticker}.AS"  # Default to Amsterdam
    
    result = await scout.scan_stock(ticker)
    
    if result:
        return {
            "status": "success",
            "ticker": ticker,
            "news_count": len(result.get('articles', [])),
            "has_material_news": result.get('has_material_news', False),
            "data": result
        }
    else:
        return {
            "status": "no_news",
            "ticker": ticker,
            "message": "No relevant news found"
        }

@router.post("/scan-all")
async def scan_all_stocks():
    """Manually trigger news scan for all watchlist stocks"""
    scout = ScoutAgent()
    results = await scout.scan_all_stocks()
    
    return {
        "status": "success",
        "scanned_count": len(scout.watchlist),
        "stocks_with_news": len(results),
        "results": results
    }

@router.put("/{signal_id}/approve")
async def approve_signal(
    signal_id: int,
    db: Session = Depends(get_db)
):
    """Approve a pending signal for execution"""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    if signal.status != SignalStatus.PENDING:
        raise HTTPException(
            status_code=400, 
            detail=f"Signal is {signal.status.value}, cannot approve"
        )
    
    signal.status = SignalStatus.APPROVED
    signal.updated_at = datetime.now()
    db.commit()
    
    return {"status": "success", "signal": signal.to_dict()}

@router.put("/{signal_id}/reject")
async def reject_signal(
    signal_id: int,
    reason: str = None,
    db: Session = Depends(get_db)
):
    """Reject a pending signal"""
    signal = db.query(Signal).filter(Signal.id == signal_id).first()
    
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    
    signal.status = SignalStatus.REJECTED
    signal.updated_at = datetime.now()
    if reason:
        signal.reasoning = f"{signal.reasoning}\nRejected: {reason}"
    db.commit()
    
    return {"status": "success", "signal": signal.to_dict()}