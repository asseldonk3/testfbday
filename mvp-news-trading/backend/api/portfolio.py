from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta

from database import get_db
from models.portfolio import Portfolio, DailyPerformance

router = APIRouter()

@router.get("/status")
async def get_portfolio_status(db: Session = Depends(get_db)):
    """Get current portfolio status"""
    portfolio = db.query(Portfolio).first()
    
    if not portfolio:
        # Create default portfolio if not exists
        portfolio = Portfolio(
            current_balance=5000.0,
            initial_balance=5000.0,
            total_pnl=0.0,
            total_pnl_percentage=0.0
        )
        db.add(portfolio)
        db.commit()
    
    portfolio.calculate_metrics()
    
    return portfolio.to_dict()

@router.get("/performance/daily")
async def get_daily_performance(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get daily performance for the last N days"""
    start_date = date.today() - timedelta(days=days)
    
    performances = db.query(DailyPerformance).filter(
        DailyPerformance.date >= start_date
    ).order_by(DailyPerformance.date).all()
    
    return {
        "days": days,
        "count": len(performances),
        "performances": [p.to_dict() for p in performances]
    }

@router.get("/metrics")
async def get_portfolio_metrics(db: Session = Depends(get_db)):
    """Get detailed portfolio metrics"""
    portfolio = db.query(Portfolio).first()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Calculate additional metrics
    sharpe_ratio = 0.0  # TODO: Implement Sharpe ratio calculation
    max_consecutive_losses = 0  # TODO: Track consecutive losses
    
    return {
        "balance": {
            "current": portfolio.current_balance,
            "initial": portfolio.initial_balance,
            "total_pnl": portfolio.total_pnl,
            "total_pnl_percentage": portfolio.total_pnl_percentage
        },
        "positions": {
            "open": portfolio.open_positions,
            "exposure": portfolio.total_exposure,
            "exposure_percentage": (portfolio.total_exposure / portfolio.current_balance * 100) if portfolio.current_balance > 0 else 0
        },
        "performance": {
            "total_trades": portfolio.total_trades,
            "winning_trades": portfolio.winning_trades,
            "losing_trades": portfolio.losing_trades,
            "win_rate": portfolio.win_rate,
            "avg_win": portfolio.avg_win,
            "avg_loss": portfolio.avg_loss,
            "profit_factor": portfolio.profit_factor
        },
        "risk": {
            "max_drawdown": portfolio.max_drawdown,
            "current_drawdown": portfolio.current_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "max_consecutive_losses": max_consecutive_losses
        }
    }

@router.post("/reset")
async def reset_portfolio(
    initial_balance: float = 5000.0,
    db: Session = Depends(get_db)
):
    """Reset portfolio to initial state (WARNING: This will clear all data)"""
    # Delete existing portfolio
    db.query(Portfolio).delete()
    
    # Create new portfolio
    portfolio = Portfolio(
        current_balance=initial_balance,
        initial_balance=initial_balance,
        total_pnl=0.0,
        total_pnl_percentage=0.0,
        open_positions=0,
        total_exposure=0.0,
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate=0.0
    )
    db.add(portfolio)
    db.commit()
    
    return {
        "status": "success",
        "message": "Portfolio reset successfully",
        "portfolio": portfolio.to_dict()
    }