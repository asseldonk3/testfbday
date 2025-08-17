from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime
import hashlib
import hmac
import json
from loguru import logger
from sqlalchemy.orm import Session

from database import get_db
from config import settings
from agents.analyst import AnalystAgent
from agents.risk_manager import RiskManagerAgent
from agents.executor import ExecutorAgent

router = APIRouter(prefix="/webhook", tags=["webhook"])

# Initialize agents
analyst_agent = AnalystAgent()
risk_manager = RiskManagerAgent()
executor_agent = ExecutorAgent()

class PredictionWebhook(BaseModel):
    """Webhook payload from prediction tool"""
    ticker: str
    prediction: Dict
    source: Optional[str] = "external"
    timestamp: Optional[datetime] = None
    metadata: Optional[Dict] = {}

class WebhookLog(BaseModel):
    """Log webhook events"""
    webhook_id: str
    source: str
    ticker: str
    received_at: datetime
    payload: Dict
    processed: bool = False
    signal_generated: bool = False
    error: Optional[str] = None

@router.post("/prediction")
async def handle_prediction_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle incoming prediction signals from external tools
    
    Flow:
    1. Validate webhook signature
    2. Parse prediction data
    3. Generate signal via Analyst Agent
    4. Apply risk filters via Risk Manager
    5. Execute trade if approved
    6. Log everything
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify webhook signature (if configured)
        if settings.webhook_secret:
            signature = request.headers.get("X-Webhook-Signature", "")
            if not verify_webhook_signature(body, signature):
                logger.warning("Invalid webhook signature")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook body")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Log webhook receipt
        webhook_log = {
            "webhook_id": request.headers.get("X-Webhook-Id", "unknown"),
            "source": data.get("source", "unknown"),
            "ticker": data.get("ticker", ""),
            "received_at": datetime.now(),
            "payload": data,
            "processed": False
        }
        
        logger.info(f"Webhook received for {webhook_log['ticker']} from {webhook_log['source']}")
        
        # Validate required fields
        if not data.get("ticker"):
            webhook_log["error"] = "Missing ticker"
            await save_webhook_log(webhook_log)
            raise HTTPException(status_code=400, detail="Missing ticker")
        
        if not data.get("prediction"):
            webhook_log["error"] = "Missing prediction"
            await save_webhook_log(webhook_log)
            raise HTTPException(status_code=400, detail="Missing prediction")
        
        # Process prediction
        result = await process_prediction(data, db)
        
        # Update webhook log
        webhook_log["processed"] = True
        webhook_log["signal_generated"] = result.get("signal_generated", False)
        await save_webhook_log(webhook_log)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Webhook processed",
                "result": result
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        
        # Log error
        if 'webhook_log' in locals():
            webhook_log["error"] = str(e)
            await save_webhook_log(webhook_log)
        
        raise HTTPException(status_code=500, detail="Internal server error")

def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify webhook signature using HMAC
    
    Args:
        body: Raw request body
        signature: Signature from header
        
    Returns:
        True if signature is valid
    """
    if not settings.webhook_secret:
        return True  # No secret configured, skip verification
    
    expected_signature = hmac.new(
        settings.webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

async def process_prediction(data: Dict, db: Session) -> Dict:
    """
    Process prediction data through the trading pipeline
    
    Args:
        data: Webhook data
        db: Database session
        
    Returns:
        Processing result
    """
    try:
        # 1. Generate signal from webhook data
        signal = await analyst_agent.generate_signal_from_webhook(data)
        
        if not signal:
            return {
                "signal_generated": False,
                "reason": "Could not generate signal from prediction"
            }
        
        logger.info(f"Signal generated for {signal.ticker}: {signal.signal_type} @ {signal.confidence}%")
        
        # 2. Validate with Risk Manager
        approved, rejection_reason, trade_params = await risk_manager.validate_signal(signal)
        
        if not approved:
            logger.info(f"Signal rejected by Risk Manager: {rejection_reason}")
            return {
                "signal_generated": True,
                "signal_id": signal.id,
                "approved": False,
                "reason": rejection_reason
            }
        
        # 3. Execute trade
        trade = await executor_agent.execute_trade(trade_params)
        
        if trade:
            logger.success(f"Trade executed: {trade.ticker} {trade.side} {trade.quantity} shares")
            return {
                "signal_generated": True,
                "signal_id": signal.id,
                "approved": True,
                "trade_executed": True,
                "trade_id": trade.id,
                "ticker": trade.ticker,
                "side": trade.side,
                "quantity": trade.quantity,
                "entry_price": trade.entry_price
            }
        else:
            return {
                "signal_generated": True,
                "signal_id": signal.id,
                "approved": True,
                "trade_executed": False,
                "reason": "Trade execution failed"
            }
            
    except Exception as e:
        logger.error(f"Error processing prediction: {str(e)}")
        return {
            "signal_generated": False,
            "error": str(e)
        }

async def save_webhook_log(log_data: Dict):
    """
    Save webhook log to file (or database in production)
    
    Args:
        log_data: Webhook log data
    """
    try:
        # For now, save to JSON file
        import os
        log_file = "/home/bramvansseldonk/testFBday/mvp-news-trading/logs/webhook_logs.json"
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Read existing logs
        logs = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        # Convert datetime to string
        if isinstance(log_data.get("received_at"), datetime):
            log_data["received_at"] = log_data["received_at"].isoformat()
        
        # Append new log
        logs.append(log_data)
        
        # Keep only last 1000 logs
        logs = logs[-1000:]
        
        # Save back
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2, default=str)
            
    except Exception as e:
        logger.error(f"Error saving webhook log: {str(e)}")

@router.get("/logs")
async def get_webhook_logs(limit: int = 100):
    """
    Get recent webhook logs
    
    Args:
        limit: Number of logs to return
        
    Returns:
        List of webhook logs
    """
    try:
        import os
        log_file = "/home/bramvansseldonk/testFBday/mvp-news-trading/logs/webhook_logs.json"
        
        if not os.path.exists(log_file):
            return []
        
        with open(log_file, 'r') as f:
            logs = json.load(f)
        
        # Return most recent logs
        return logs[-limit:]
        
    except Exception as e:
        logger.error(f"Error reading webhook logs: {str(e)}")
        return []

@router.post("/test")
async def test_webhook():
    """
    Test webhook endpoint
    
    Returns:
        Test confirmation
    """
    return {
        "status": "success",
        "message": "Webhook endpoint is working",
        "timestamp": datetime.now().isoformat()
    }