import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from config import settings
import time

class MarketauxService:
    """Service for fetching real-time news from Marketaux API"""
    
    BASE_URL = "https://api.marketaux.com/v1/news/all"
    
    def __init__(self):
        """Initialize Marketaux service"""
        self.api_key = settings.marketaux_api_key
        if not self.api_key:
            logger.warning("Marketaux API key not found - using free tier limitations")
        
        logger.info("Marketaux service initialized")
    
    async def get_news_for_ticker(self, ticker: str, hours_back: int = 4) -> Dict:
        """
        Get recent news for a specific ticker
        
        Args:
            ticker: Stock ticker (e.g., "ASML.AS")
            hours_back: How many hours of news to fetch (default 4)
            
        Returns:
            Dictionary with news articles and metadata
        """
        try:
            # Clean ticker for API (remove exchange suffix for some queries)
            base_ticker = ticker.split('.')[0] if '.' in ticker else ticker
            
            # Calculate time range
            now = datetime.utcnow()
            from_time = now - timedelta(hours=hours_back)
            
            # Build query parameters
            params = {
                "symbols": base_ticker,
                "filter_entities": "true",
                "published_after": from_time.strftime("%Y-%m-%dT%H:%M"),
                "language": "en",
                "sort": "published_desc",
                "limit": 10
            }
            
            # Add API key if available
            if self.api_key:
                params["api_token"] = self.api_key
            
            # Make request
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_marketaux_response(data, ticker)
            else:
                logger.error(f"Marketaux API error: {response.status_code} - {response.text}")
                return {"error": f"API error: {response.status_code}", "articles": []}
                
        except Exception as e:
            logger.error(f"Error fetching Marketaux news for {ticker}: {str(e)}")
            return {"error": str(e), "articles": []}
    
    async def get_news_for_watchlist(self, tickers: List[str], hours_back: int = 4) -> Dict:
        """
        Get news for multiple tickers at once
        
        Args:
            tickers: List of stock tickers
            hours_back: How many hours of news to fetch
            
        Returns:
            Dictionary with news grouped by ticker
        """
        try:
            # Clean tickers
            clean_tickers = [t.split('.')[0] if '.' in t else t for t in tickers]
            
            # Calculate time range
            now = datetime.utcnow()
            from_time = now - timedelta(hours=hours_back)
            
            # Build query - Marketaux supports multiple symbols
            params = {
                "symbols": ",".join(clean_tickers),
                "filter_entities": "true",
                "published_after": from_time.strftime("%Y-%m-%dT%H:%M"),
                "language": "en",
                "sort": "published_desc",
                "limit": 50  # More for multiple tickers
            }
            
            if self.api_key:
                params["api_token"] = self.api_key
            
            # Make request
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_marketaux_batch_response(data, tickers)
            else:
                logger.error(f"Marketaux batch API error: {response.status_code}")
                return {"error": f"API error: {response.status_code}", "news_by_ticker": {}}
                
        except Exception as e:
            logger.error(f"Error fetching Marketaux batch news: {str(e)}")
            return {"error": str(e), "news_by_ticker": {}}
    
    def _parse_marketaux_response(self, data: Dict, ticker: str) -> Dict:
        """Parse Marketaux API response"""
        
        articles = []
        
        if "data" in data:
            for item in data["data"]:
                # Calculate age of news
                published_at = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                age_hours = (datetime.utcnow() - published_at.replace(tzinfo=None)).total_seconds() / 3600
                
                article = {
                    "ticker": ticker,
                    "headline": item.get("title", ""),
                    "description": item.get("description", ""),
                    "source": item.get("source", "Unknown"),
                    "source_domain": item.get("source_domain", ""),
                    "url": item.get("url", ""),
                    "published_at": item.get("published_at", ""),
                    "timestamp": published_at.isoformat(),
                    "age_hours": round(age_hours, 1),
                    "is_fresh": age_hours <= 4,
                    "sentiment": self._extract_sentiment(item),
                    "entities": item.get("entities", []),
                    "highlights": item.get("highlight", {}).get("highlight", []) if item.get("highlight") else [],
                    "image_url": item.get("image_url", ""),
                    "api_source": "marketaux"
                }
                
                articles.append(article)
        
        return {
            "ticker": ticker,
            "articles": articles,
            "count": len(articles),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "marketaux",
            "has_fresh_news": any(a["is_fresh"] for a in articles)
        }
    
    def _parse_marketaux_batch_response(self, data: Dict, tickers: List[str]) -> Dict:
        """Parse batch response and group by ticker"""
        
        news_by_ticker = {ticker: [] for ticker in tickers}
        
        if "data" in data:
            for item in data["data"]:
                # Extract tickers from entities
                article_tickers = []
                for entity in item.get("entities", []):
                    if entity.get("type") == "equity" and entity.get("symbol"):
                        # Match with our watchlist tickers
                        symbol = entity["symbol"]
                        for ticker in tickers:
                            if symbol in ticker or ticker.split('.')[0] == symbol:
                                article_tickers.append(ticker)
                
                # Add article to each relevant ticker
                for ticker in article_tickers:
                    published_at = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
                    age_hours = (datetime.utcnow() - published_at.replace(tzinfo=None)).total_seconds() / 3600
                    
                    article = {
                        "ticker": ticker,
                        "headline": item.get("title", ""),
                        "description": item.get("description", ""),
                        "source": item.get("source", "Unknown"),
                        "url": item.get("url", ""),
                        "published_at": item.get("published_at", ""),
                        "timestamp": published_at.isoformat(),
                        "age_hours": round(age_hours, 1),
                        "is_fresh": age_hours <= 4,
                        "sentiment": self._extract_sentiment(item),
                        "api_source": "marketaux"
                    }
                    
                    news_by_ticker[ticker].append(article)
        
        return {
            "news_by_ticker": news_by_ticker,
            "total_articles": sum(len(articles) for articles in news_by_ticker.values()),
            "timestamp": datetime.utcnow().isoformat(),
            "source": "marketaux"
        }
    
    def _extract_sentiment(self, item: Dict) -> str:
        """Extract sentiment from Marketaux data"""
        
        # Marketaux may provide sentiment scores
        if "sentiment" in item:
            sentiment_score = item["sentiment"]
            if isinstance(sentiment_score, dict):
                # Handle different sentiment formats
                if "score" in sentiment_score:
                    score = sentiment_score["score"]
                    if score > 0.2:
                        return "positive"
                    elif score < -0.2:
                        return "negative"
                    else:
                        return "neutral"
        
        # Fallback to keyword analysis
        text = (item.get("title", "") + " " + item.get("description", "")).lower()
        
        positive_keywords = ["surge", "jump", "rise", "gain", "beat", "upgrade", "buy", "growth", "record", "breakthrough"]
        negative_keywords = ["fall", "drop", "decline", "loss", "miss", "downgrade", "sell", "warning", "cut", "lawsuit"]
        
        pos_count = sum(1 for word in positive_keywords if word in text)
        neg_count = sum(1 for word in negative_keywords if word in text)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"