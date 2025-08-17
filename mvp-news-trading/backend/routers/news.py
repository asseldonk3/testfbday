"""
News API endpoints for aggregated news from multiple sources
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from loguru import logger

from services.news_aggregator import NewsAggregator
from config import settings

router = APIRouter(prefix="/api/news", tags=["news"])

# Initialize news aggregator
news_aggregator = NewsAggregator()


@router.get("/ticker/{ticker}")
async def get_ticker_news(
    ticker: str,
    hours_back: int = Query(4, ge=1, le=48, description="Hours of news history")
):
    """
    Get aggregated news for a specific ticker from all sources
    
    Args:
        ticker: Stock ticker (e.g., ASML.AS)
        hours_back: How many hours of news to fetch (default 4, max 48)
    
    Returns:
        Aggregated news from Gemini, Marketaux, and Finnhub
    """
    try:
        logger.info(f"Fetching news for {ticker} (last {hours_back} hours)")
        
        # Get aggregated news
        news_data = await news_aggregator.get_aggregated_news(ticker, hours_back)
        
        # Add sentiment analysis
        if news_data.get("articles"):
            sentiment = await news_aggregator.get_sentiment_analysis(
                ticker, 
                news_data["articles"]
            )
            news_data["sentiment_analysis"] = sentiment
        
        return news_data
        
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist")
async def get_watchlist_news(
    hours_back: int = Query(4, ge=1, le=48, description="Hours of news history")
):
    """
    Get news for all stocks in the watchlist
    
    Args:
        hours_back: How many hours of news to fetch
    
    Returns:
        News grouped by ticker for all watchlist stocks
    """
    try:
        # Get current watchlist
        watchlist = settings.watchlist
        logger.info(f"Fetching news for {len(watchlist)} stocks")
        
        # Get aggregated news for all tickers
        news_data = await news_aggregator.get_watchlist_news(watchlist, hours_back)
        
        return news_data
        
    except Exception as e:
        logger.error(f"Error fetching watchlist news: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fresh")
async def get_fresh_news():
    """
    Get only fresh news (< 4 hours old) for the entire watchlist
    
    Returns:
        Fresh news articles from all sources
    """
    try:
        watchlist = settings.watchlist
        
        # Get news for last 4 hours only
        news_data = await news_aggregator.get_watchlist_news(watchlist, hours_back=4)
        
        # Filter to only fresh articles
        fresh_articles = []
        for ticker, ticker_news in news_data.get("news_by_ticker", {}).items():
            if isinstance(ticker_news, dict) and "articles" in ticker_news:
                for article in ticker_news["articles"]:
                    if article.get("is_fresh", False):
                        article["ticker"] = ticker  # Ensure ticker is included
                        fresh_articles.append(article)
        
        # Sort by age (newest first)
        fresh_articles.sort(key=lambda x: x.get("age_hours", 999))
        
        return {
            "fresh_articles": fresh_articles,
            "count": len(fresh_articles),
            "timestamp": datetime.now().isoformat(),
            "sources": news_aggregator.available_services
        }
        
    except Exception as e:
        logger.error(f"Error fetching fresh news: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sources")
async def get_news_sources():
    """
    Get information about available news sources
    
    Returns:
        List of configured news sources and their status
    """
    sources = []
    
    # Check Gemini
    sources.append({
        "name": "Gemini (Google Search)",
        "type": "AI-powered search",
        "configured": bool(settings.gemini_api_key),
        "features": ["Real-time search", "AI analysis", "Multiple sources"],
        "latency": "2-5 seconds",
        "coverage": "Global"
    })
    
    # Check Marketaux
    sources.append({
        "name": "Marketaux",
        "type": "News API",
        "configured": bool(settings.marketaux_api_key),
        "features": ["Real-time news", "Sentiment analysis", "Entity extraction"],
        "latency": "< 1 second",
        "coverage": "Global financial news"
    })
    
    # Check Finnhub
    sources.append({
        "name": "Finnhub",
        "type": "Financial data API",
        "configured": bool(settings.finnhub_api_key),
        "features": ["Company news", "Market news", "WebSocket streaming"],
        "latency": "< 1 second",
        "coverage": "US and European markets"
    })
    
    configured_count = sum(1 for s in sources if s["configured"])
    
    return {
        "sources": sources,
        "total": len(sources),
        "configured": configured_count,
        "recommendation": "Configure all 3 sources for best coverage and redundancy" if configured_count < 3 else "All sources configured"
    }


@router.post("/test/{ticker}")
async def test_news_sources(ticker: str):
    """
    Test all configured news sources for a ticker
    
    Args:
        ticker: Stock ticker to test
    
    Returns:
        Results from each source with timing information
    """
    import time
    
    results = {}
    
    # Test Gemini
    if settings.gemini_api_key:
        start = time.time()
        try:
            from services.gemini_service import GeminiService
            gemini = GeminiService()
            gemini_result = await gemini.search_news(ticker)
            results["gemini"] = {
                "success": True,
                "articles": len(gemini_result.get("articles", [])),
                "latency": round(time.time() - start, 2),
                "error": gemini_result.get("error")
            }
        except Exception as e:
            results["gemini"] = {
                "success": False,
                "error": str(e),
                "latency": round(time.time() - start, 2)
            }
    
    # Test Marketaux
    if settings.marketaux_api_key:
        start = time.time()
        try:
            from services.marketaux_service import MarketauxService
            marketaux = MarketauxService()
            marketaux_result = await marketaux.get_news_for_ticker(ticker)
            results["marketaux"] = {
                "success": True,
                "articles": len(marketaux_result.get("articles", [])),
                "latency": round(time.time() - start, 2),
                "error": marketaux_result.get("error")
            }
        except Exception as e:
            results["marketaux"] = {
                "success": False,
                "error": str(e),
                "latency": round(time.time() - start, 2)
            }
    
    # Test Finnhub
    if settings.finnhub_api_key:
        start = time.time()
        try:
            from services.finnhub_service import FinnhubService
            finnhub = FinnhubService()
            finnhub_result = await finnhub.get_company_news(ticker)
            results["finnhub"] = {
                "success": True,
                "articles": len(finnhub_result.get("articles", [])),
                "latency": round(time.time() - start, 2),
                "error": finnhub_result.get("error")
            }
        except Exception as e:
            results["finnhub"] = {
                "success": False,
                "error": str(e),
                "latency": round(time.time() - start, 2)
            }
    
    # Summary
    total_articles = sum(r.get("articles", 0) for r in results.values() if r.get("success"))
    avg_latency = sum(r["latency"] for r in results.values()) / len(results) if results else 0
    
    return {
        "ticker": ticker,
        "results": results,
        "summary": {
            "sources_tested": len(results),
            "sources_successful": sum(1 for r in results.values() if r.get("success")),
            "total_articles": total_articles,
            "average_latency": round(avg_latency, 2)
        },
        "timestamp": datetime.now().isoformat()
    }