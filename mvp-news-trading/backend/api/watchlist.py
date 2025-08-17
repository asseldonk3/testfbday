from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from pydantic import BaseModel
from datetime import datetime
from loguru import logger
import json
import os

from config import settings
from database import SessionLocal, get_db

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

# File to store custom watchlist
WATCHLIST_FILE = "data/watchlist.json"

class WatchlistUpdate(BaseModel):
    stocks: List[str]
    reason: str = ""
    
class StockInfo(BaseModel):
    ticker: str
    company_name: str
    exchange: str
    
class WatchlistResponse(BaseModel):
    current_watchlist: List[str]
    last_updated: str
    total_stocks: int
    reason: str = ""

# EU Stock Universe for day trading
EU_STOCK_UNIVERSE = {
    # Amsterdam (AEX)
    "ASML.AS": {"name": "ASML Holding", "exchange": "Amsterdam", "sector": "Technology"},
    "SHEL.AS": {"name": "Shell", "exchange": "Amsterdam", "sector": "Energy"},
    "UNA.AS": {"name": "Unilever", "exchange": "Amsterdam", "sector": "Consumer"},
    "INGA.AS": {"name": "ING Group", "exchange": "Amsterdam", "sector": "Banking"},
    "ABN.AS": {"name": "ABN AMRO", "exchange": "Amsterdam", "sector": "Banking"},
    "RAND.AS": {"name": "Randstad", "exchange": "Amsterdam", "sector": "Staffing"},
    "HEIA.AS": {"name": "Heineken", "exchange": "Amsterdam", "sector": "Beverages"},
    "PHIA.AS": {"name": "Philips", "exchange": "Amsterdam", "sector": "Healthcare"},
    "AD.AS": {"name": "Ahold Delhaize", "exchange": "Amsterdam", "sector": "Retail"},
    "KPN.AS": {"name": "KPN", "exchange": "Amsterdam", "sector": "Telecom"},
    
    # Frankfurt (DAX)
    "SAP.DE": {"name": "SAP SE", "exchange": "Frankfurt", "sector": "Software"},
    "SIE.DE": {"name": "Siemens", "exchange": "Frankfurt", "sector": "Industrial"},
    "VOW3.DE": {"name": "Volkswagen", "exchange": "Frankfurt", "sector": "Automotive"},
    "DBK.DE": {"name": "Deutsche Bank", "exchange": "Frankfurt", "sector": "Banking"},
    "BMW.DE": {"name": "BMW", "exchange": "Frankfurt", "sector": "Automotive"},
    "BAS.DE": {"name": "BASF", "exchange": "Frankfurt", "sector": "Chemicals"},
    "BAYN.DE": {"name": "Bayer", "exchange": "Frankfurt", "sector": "Pharma"},
    "DTE.DE": {"name": "Deutsche Telekom", "exchange": "Frankfurt", "sector": "Telecom"},
    "ALV.DE": {"name": "Allianz", "exchange": "Frankfurt", "sector": "Insurance"},
    "MBG.DE": {"name": "Mercedes-Benz", "exchange": "Frankfurt", "sector": "Automotive"},
    
    # Paris (CAC40)
    "MC.PA": {"name": "LVMH", "exchange": "Paris", "sector": "Luxury"},
    "TTE.PA": {"name": "TotalEnergies", "exchange": "Paris", "sector": "Energy"},
    "SAN.PA": {"name": "Sanofi", "exchange": "Paris", "sector": "Pharma"},
    "BNP.PA": {"name": "BNP Paribas", "exchange": "Paris", "sector": "Banking"},
    "OR.PA": {"name": "L'Oreal", "exchange": "Paris", "sector": "Consumer"},
    "AIR.PA": {"name": "Airbus", "exchange": "Paris", "sector": "Aerospace"},
    "SU.PA": {"name": "Schneider Electric", "exchange": "Paris", "sector": "Industrial"},
    "CS.PA": {"name": "AXA", "exchange": "Paris", "sector": "Insurance"},
    "SGO.PA": {"name": "Saint-Gobain", "exchange": "Paris", "sector": "Materials"},
    "RNO.PA": {"name": "Renault", "exchange": "Paris", "sector": "Automotive"},
    
    # Swiss (SMI)
    "NESN.SW": {"name": "Nestle", "exchange": "Swiss", "sector": "Food"},
    "NOVN.SW": {"name": "Novartis", "exchange": "Swiss", "sector": "Pharma"},
    "ROG.SW": {"name": "Roche", "exchange": "Swiss", "sector": "Pharma"},
    "UBSG.SW": {"name": "UBS", "exchange": "Swiss", "sector": "Banking"},
    "CSGN.SW": {"name": "Credit Suisse", "exchange": "Swiss", "sector": "Banking"},
    "ABBN.SW": {"name": "ABB", "exchange": "Swiss", "sector": "Industrial"},
    
    # Milan (FTSE MIB)
    "UCG.MI": {"name": "UniCredit", "exchange": "Milan", "sector": "Banking"},
    "ISP.MI": {"name": "Intesa Sanpaolo", "exchange": "Milan", "sector": "Banking"},
    "ENEL.MI": {"name": "Enel", "exchange": "Milan", "sector": "Utilities"},
    "ENI.MI": {"name": "Eni", "exchange": "Milan", "sector": "Energy"},
    "G.MI": {"name": "Generali", "exchange": "Milan", "sector": "Insurance"},
    
    # Madrid (IBEX 35)
    "SAN.MC": {"name": "Santander", "exchange": "Madrid", "sector": "Banking"},
    "BBVA.MC": {"name": "BBVA", "exchange": "Madrid", "sector": "Banking"},
    "TEF.MC": {"name": "Telefonica", "exchange": "Madrid", "sector": "Telecom"},
    "IBE.MC": {"name": "Iberdrola", "exchange": "Madrid", "sector": "Utilities"},
    "ITX.MC": {"name": "Inditex", "exchange": "Madrid", "sector": "Retail"},
    "REP.MC": {"name": "Repsol", "exchange": "Madrid", "sector": "Energy"},
}

def load_current_watchlist():
    """Load watchlist from file or use default"""
    try:
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, 'r') as f:
                data = json.load(f)
                return data.get('stocks', settings.watchlist)
        else:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
    except Exception as e:
        logger.error(f"Error loading watchlist: {e}")
    
    return settings.watchlist

def save_watchlist(stocks: List[str], reason: str = ""):
    """Save watchlist to file"""
    try:
        os.makedirs(os.path.dirname(WATCHLIST_FILE), exist_ok=True)
        data = {
            "stocks": stocks,
            "last_updated": datetime.now().isoformat(),
            "reason": reason
        }
        with open(WATCHLIST_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Also update the settings in memory
        settings.watchlist = stocks
        logger.info(f"Watchlist updated with {len(stocks)} stocks")
        return True
    except Exception as e:
        logger.error(f"Error saving watchlist: {e}")
        return False

@router.get("/current", response_model=WatchlistResponse)
async def get_current_watchlist():
    """Get current watchlist"""
    try:
        stocks = load_current_watchlist()
        
        # Load metadata if available
        metadata = {"last_updated": datetime.now().isoformat(), "reason": ""}
        if os.path.exists(WATCHLIST_FILE):
            with open(WATCHLIST_FILE, 'r') as f:
                data = json.load(f)
                metadata["last_updated"] = data.get("last_updated", metadata["last_updated"])
                metadata["reason"] = data.get("reason", "")
        
        return WatchlistResponse(
            current_watchlist=stocks,
            last_updated=metadata["last_updated"],
            total_stocks=len(stocks),
            reason=metadata["reason"]
        )
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/update")
async def update_watchlist(update: WatchlistUpdate):
    """Update the watchlist with new stocks"""
    try:
        # Validate stocks exist in universe
        invalid_stocks = [s for s in update.stocks if s not in EU_STOCK_UNIVERSE]
        if invalid_stocks:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid stocks not in universe: {invalid_stocks}"
            )
        
        # Save new watchlist
        if save_watchlist(update.stocks, update.reason):
            logger.info(f"Watchlist updated: {len(update.stocks)} stocks - {update.reason}")
            
            return {
                "success": True,
                "message": f"Watchlist updated with {len(update.stocks)} stocks",
                "stocks": update.stocks,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save watchlist")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/universe")
async def get_stock_universe():
    """Get all available EU stocks"""
    try:
        # Format universe for frontend
        universe = []
        for ticker, info in EU_STOCK_UNIVERSE.items():
            universe.append({
                "ticker": ticker,
                "company_name": info["name"],
                "exchange": info["exchange"],
                "sector": info["sector"]
            })
        
        # Sort by exchange and name
        universe.sort(key=lambda x: (x["exchange"], x["company_name"]))
        
        return {
            "total": len(universe),
            "stocks": universe,
            "exchanges": list(set(s["exchange"] for s in universe)),
            "sectors": list(set(s["sector"] for s in universe))
        }
    except Exception as e:
        logger.error(f"Error getting universe: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-stock/{ticker}")
async def add_stock_to_watchlist(ticker: str):
    """Add a single stock to watchlist"""
    try:
        if ticker not in EU_STOCK_UNIVERSE:
            raise HTTPException(status_code=400, detail=f"Stock {ticker} not in universe")
        
        current = load_current_watchlist()
        if ticker in current:
            return {"success": False, "message": f"{ticker} already in watchlist"}
        
        current.append(ticker)
        if save_watchlist(current, f"Added {ticker}"):
            return {"success": True, "message": f"Added {ticker} to watchlist"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save watchlist")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/remove-stock/{ticker}")
async def remove_stock_from_watchlist(ticker: str):
    """Remove a single stock from watchlist"""
    try:
        current = load_current_watchlist()
        if ticker not in current:
            return {"success": False, "message": f"{ticker} not in watchlist"}
        
        current.remove(ticker)
        if save_watchlist(current, f"Removed {ticker}"):
            return {"success": True, "message": f"Removed {ticker} from watchlist"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save watchlist")
            
    except Exception as e:
        logger.error(f"Error removing stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suggestions")
async def get_watchlist_suggestions():
    """Get AI-suggested stocks for the week based on upcoming catalysts"""
    try:
        # This would normally query catalyst calendars and score stocks
        # For now, return mock suggestions
        suggestions = {
            "earnings": ["SAP.DE", "ASML.AS", "MC.PA"],  # Stocks with earnings
            "high_volume": ["SHEL.AS", "TTE.PA", "DBK.DE"],  # Recent high volume
            "volatile": ["UCG.MI", "SAN.MC", "BMW.DE"],  # High intraday range
            "catalyst_date": {
                "SAP.DE": "Earnings Thursday",
                "ASML.AS": "Investor Day Wednesday",
                "MC.PA": "Sales Report Tuesday"
            }
        }
        
        return suggestions
    except Exception as e:
        logger.error(f"Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))