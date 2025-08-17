from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date

from database import get_db
from models.trade import Trade, TradeStatus

router = APIRouter()

@router.get("/active")
async def get_active_trades(db: Session = Depends(get_db)):
    """Get all currently open trades"""
    trades = db.query(Trade).filter(
        Trade.status == TradeStatus.OPEN
    ).all()
    
    return {
        "count": len(trades),
        "trades": [t.to_dict() for t in trades]
    }

@router.get("/today")
async def get_today_trades(db: Session = Depends(get_db)):
    """Get all trades from today"""
    today = date.today()
    trades = db.query(Trade).filter(
        Trade.created_at >= today
    ).all()
    
    # Calculate today's P&L
    total_pnl = sum(t.pnl or 0 for t in trades)
    winning = [t for t in trades if (t.pnl or 0) > 0]
    losing = [t for t in trades if (t.pnl or 0) < 0]
    
    return {
        "date": today.isoformat(),
        "count": len(trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "total_pnl": total_pnl,
        "trades": [t.to_dict() for t in trades]
    }

@router.get("/history")
async def get_trade_history(
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get trade history with optional filtering"""
    query = db.query(Trade)
    
    if status:
        try:
            trade_status = TradeStatus[status.upper()]
            query = query.filter(Trade.status == trade_status)
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    trades = query.order_by(Trade.created_at.desc()).limit(limit).all()
    
    return {
        "count": len(trades),
        "trades": [t.to_dict() for t in trades]
    }

@router.get("/{trade_id}")
async def get_trade(trade_id: int, db: Session = Depends(get_db)):
    """Get specific trade details"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    return trade.to_dict()

@router.post("/{trade_id}/close")
async def close_trade(
    trade_id: int,
    exit_price: float,
    db: Session = Depends(get_db)
):
    """Manually close a trade"""
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if trade.status != TradeStatus.OPEN:
        raise HTTPException(
            status_code=400,
            detail=f"Trade is {trade.status.value}, cannot close"
        )
    
    # Update trade
    trade.exit_price = exit_price
    trade.status = TradeStatus.CLOSED
    trade.closed_at = datetime.now()
    
    # Calculate P&L
    trade.calculate_pnl()
    
    db.commit()
    
    return {
        "status": "success",
        "trade": trade.to_dict(),
        "pnl": trade.pnl,
        "pnl_percentage": trade.pnl_percentage
    }