import requests
import websocket
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from config import settings
import json
import threading

class FinnhubService:
    """Service for fetching real-time news and data from Finnhub API"""
    
    BASE_URL = "https://finnhub.io/api/v1"
    WS_URL = "wss://ws.finnhub.io"
    
    def __init__(self):
        """Initialize Finnhub service"""
        self.api_key = settings.finnhub_api_key
        if not self.api_key:
            logger.warning("Finnhub API key not found - limited functionality")
        
        self.ws = None
        self.ws_thread = None
        self.news_cache = {}
        
        logger.info("Finnhub service initialized")
    
    async def get_company_news(self, ticker: str, from_date: str = None, to_date: str = None) -> Dict:
        """
        Get company-specific news from Finnhub
        
        Args:
            ticker: Stock ticker (e.g., "ASML")
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            
        Returns:
            Dictionary with news articles
        """
        try:
            # Default to last 24 hours if no dates provided
            if not from_date:
                from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            if not to_date:
                to_date = datetime.now().strftime("%Y-%m-%d")
            
            # Clean ticker for Finnhub (usually wants just the base symbol)
            base_ticker = ticker.split('.')[0] if '.' in ticker else ticker
            
            # Build request URL
            url = f"{self.BASE_URL}/company-news"
            params = {
                "symbol": base_ticker,
                "from": from_date,
                "to": to_date,
                "token": self.api_key
            }
            
            # Make request
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_finnhub_news(data, ticker)
            else:
                logger.error(f"Finnhub API error: {response.status_code}")
                return {"error": f"API error: {response.status_code}", "articles": []}
                
        except Exception as e:
            logger.error(f"Error fetching Finnhub news for {ticker}: {str(e)}")
            return {"error": str(e), "articles": []}
    
    async def get_market_news(self, category: str = "general") -> Dict:
        """
        Get general market news
        
        Args:
            category: News category (general, forex, crypto, merger)
            
        Returns:
            Dictionary with market news
        """
        try:
            url = f"{self.BASE_URL}/news"
            params = {
                "category": category,
                "token": self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_market_news(data)
            else:
                logger.error(f"Finnhub market news error: {response.status_code}")
                return {"error": f"API error: {response.status_code}", "articles": []}
                
        except Exception as e:
            logger.error(f"Error fetching Finnhub market news: {str(e)}")
            return {"error": str(e), "articles": []}
    
    async def get_news_sentiment(self, ticker: str) -> Dict:
        """
        Get news sentiment analysis for a ticker
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Dictionary with sentiment data
        """
        try:
            base_ticker = ticker.split('.')[0] if '.' in ticker else ticker
            
            url = f"{self.BASE_URL}/news-sentiment"
            params = {
                "symbol": base_ticker,
                "token": self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_sentiment(data, ticker)
            else:
                logger.error(f"Finnhub sentiment error: {response.status_code}")
                return {"error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error fetching Finnhub sentiment: {str(e)}")
            return {"error": str(e)}
    
    def start_websocket_stream(self, tickers: List[str]):
        """
        Start WebSocket connection for real-time news
        
        Args:
            tickers: List of tickers to subscribe to
        """
        if not self.api_key:
            logger.error("Cannot start WebSocket without API key")
            return
        
        def on_message(ws, message):
            """Handle incoming WebSocket messages"""
            try:
                data = json.loads(message)
                if data["type"] == "news":
                    self._process_realtime_news(data["data"])
            except Exception as e:
                logger.error(f"WebSocket message error: {e}")
        
        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("WebSocket connection closed")
        
        def on_open(ws):
            logger.info("WebSocket connection opened")
            # Subscribe to news for each ticker
            for ticker in tickers:
                base_ticker = ticker.split('.')[0] if '.' in ticker else ticker
                ws.send(json.dumps({
                    "type": "subscribe",
                    "symbol": base_ticker
                }))
        
        # Create WebSocket connection
        websocket_url = f"{self.WS_URL}?token={self.api_key}"
        self.ws = websocket.WebSocketApp(
            websocket_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Run in separate thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        logger.info(f"Started Finnhub WebSocket for {len(tickers)} tickers")
    
    def stop_websocket_stream(self):
        """Stop WebSocket connection"""
        if self.ws:
            self.ws.close()
            logger.info("Stopped Finnhub WebSocket")
    
    def _parse_finnhub_news(self, data: List[Dict], ticker: str) -> Dict:
        """Parse Finnhub company news response"""
        
        articles = []
        
        for item in data:
            # Convert Unix timestamp to datetime
            published_at = datetime.fromtimestamp(item.get("datetime", 0))
            age_hours = (datetime.now() - published_at).total_seconds() / 3600
            
            article = {
                "ticker": ticker,
                "headline": item.get("headline", ""),
                "summary": item.get("summary", ""),
                "source": item.get("source", "Unknown"),
                "url": item.get("url", ""),
                "published_at": published_at.isoformat(),
                "timestamp": published_at.isoformat(),
                "age_hours": round(age_hours, 1),
                "is_fresh": age_hours <= 4,
                "category": item.get("category", "general"),
                "related_tickers": item.get("related", ticker),
                "image": item.get("image", ""),
                "api_source": "finnhub"
            }
            
            # Basic sentiment from headline/summary
            article["sentiment"] = self._analyze_text_sentiment(
                item.get("headline", "") + " " + item.get("summary", "")
            )
            
            articles.append(article)
        
        # Sort by recency
        articles.sort(key=lambda x: x["published_at"], reverse=True)
        
        return {
            "ticker": ticker,
            "articles": articles,
            "count": len(articles),
            "timestamp": datetime.now().isoformat(),
            "source": "finnhub",
            "has_fresh_news": any(a["is_fresh"] for a in articles)
        }
    
    def _parse_market_news(self, data: List[Dict]) -> Dict:
        """Parse general market news"""
        
        articles = []
        
        for item in data:
            published_at = datetime.fromtimestamp(item.get("datetime", 0))
            age_hours = (datetime.now() - published_at).total_seconds() / 3600
            
            article = {
                "headline": item.get("headline", ""),
                "summary": item.get("summary", ""),
                "source": item.get("source", "Unknown"),
                "url": item.get("url", ""),
                "published_at": published_at.isoformat(),
                "age_hours": round(age_hours, 1),
                "is_fresh": age_hours <= 4,
                "category": item.get("category", "general"),
                "image": item.get("image", ""),
                "api_source": "finnhub"
            }
            
            articles.append(article)
        
        return {
            "articles": articles,
            "count": len(articles),
            "timestamp": datetime.now().isoformat(),
            "source": "finnhub_market"
        }
    
    def _parse_sentiment(self, data: Dict, ticker: str) -> Dict:
        """Parse Finnhub sentiment data"""
        
        sentiment_data = {
            "ticker": ticker,
            "buzz": {
                "articles_in_last_week": data.get("buzz", {}).get("articlesInLastWeek", 0),
                "weekly_average": data.get("buzz", {}).get("weeklyAverage", 0),
                "buzz_score": data.get("buzz", {}).get("buzz", 0)
            },
            "sentiment": {
                "bullish_percent": data.get("sentiment", {}).get("bullishPercent", 0),
                "bearish_percent": data.get("sentiment", {}).get("bearishPercent", 0),
                "sector_average_bullish": data.get("sectorAverageBullishPercent", 0),
                "sector_average_news_score": data.get("sectorAverageNewsScore", 0),
                "company_news_score": data.get("companyNewsScore", 0)
            },
            "timestamp": datetime.now().isoformat(),
            "source": "finnhub_sentiment"
        }
        
        # Determine overall sentiment
        bullish = sentiment_data["sentiment"]["bullish_percent"]
        bearish = sentiment_data["sentiment"]["bearish_percent"]
        
        if bullish > 60:
            sentiment_data["overall_sentiment"] = "bullish"
        elif bearish > 60:
            sentiment_data["overall_sentiment"] = "bearish"
        else:
            sentiment_data["overall_sentiment"] = "neutral"
        
        return sentiment_data
    
    def _analyze_text_sentiment(self, text: str) -> str:
        """Simple sentiment analysis based on keywords"""
        
        text_lower = text.lower()
        
        positive_keywords = [
            "surge", "jump", "rise", "gain", "beat", "upgrade", "buy",
            "growth", "record", "breakthrough", "profit", "revenue",
            "strong", "outperform", "positive", "bullish"
        ]
        
        negative_keywords = [
            "fall", "drop", "decline", "loss", "miss", "downgrade", "sell",
            "warning", "cut", "lawsuit", "weak", "underperform", "negative",
            "bearish", "concern", "risk", "investigation"
        ]
        
        pos_count = sum(1 for word in positive_keywords if word in text_lower)
        neg_count = sum(1 for word in negative_keywords if word in text_lower)
        
        if pos_count > neg_count + 1:
            return "positive"
        elif neg_count > pos_count + 1:
            return "negative"
        else:
            return "neutral"
    
    def _process_realtime_news(self, news_data: List[Dict]):
        """Process real-time news from WebSocket"""
        
        for item in news_data:
            ticker = item.get("s", "UNKNOWN")
            
            # Add to cache
            if ticker not in self.news_cache:
                self.news_cache[ticker] = []
            
            news_item = {
                "ticker": ticker,
                "headline": item.get("headline", ""),
                "timestamp": datetime.now().isoformat(),
                "is_realtime": True,
                "api_source": "finnhub_websocket"
            }
            
            self.news_cache[ticker].append(news_item)
            
            # Keep only last 100 items per ticker
            if len(self.news_cache[ticker]) > 100:
                self.news_cache[ticker] = self.news_cache[ticker][-100:]
            
            logger.info(f"Real-time news for {ticker}: {news_item['headline'][:50]}...")
    
    def get_cached_realtime_news(self, ticker: str = None) -> Dict:
        """Get cached real-time news"""
        
        if ticker:
            return {
                "ticker": ticker,
                "articles": self.news_cache.get(ticker, []),
                "source": "finnhub_realtime_cache"
            }
        else:
            return {
                "all_cached_news": self.news_cache,
                "total_articles": sum(len(v) for v in self.news_cache.values()),
                "source": "finnhub_realtime_cache"
            }