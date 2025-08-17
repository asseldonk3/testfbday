"""
News Aggregation Service
Combines news from multiple sources: Gemini (Google Search), Marketaux, and Finnhub
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from collections import defaultdict

from services.gemini_service import GeminiService
from services.marketaux_service import MarketauxService
from services.finnhub_service import FinnhubService


class NewsAggregator:
    """Aggregates news from multiple sources for redundancy and better coverage"""
    
    def __init__(self):
        """Initialize all news services"""
        self.gemini_service = GeminiService()
        self.marketaux_service = MarketauxService()
        self.finnhub_service = FinnhubService()
        
        # Track which services are available
        self.available_services = self._check_available_services()
        logger.info(f"News Aggregator initialized with services: {self.available_services}")
    
    def _check_available_services(self) -> List[str]:
        """Check which services have API keys configured"""
        available = []
        
        from config import settings
        if settings.gemini_api_key:
            available.append("gemini")
        if settings.marketaux_api_key:
            available.append("marketaux")
        if settings.finnhub_api_key:
            available.append("finnhub")
        
        return available
    
    async def get_aggregated_news(self, ticker: str, hours_back: int = 4) -> Dict:
        """
        Get news from all available sources for a ticker
        
        Args:
            ticker: Stock ticker (e.g., "ASML.AS")
            hours_back: How many hours of news to fetch
            
        Returns:
            Aggregated news from all sources with duplicates removed
        """
        try:
            # Run all services in parallel
            tasks = []
            
            if "gemini" in self.available_services:
                tasks.append(self._get_gemini_news(ticker))
            if "marketaux" in self.available_services:
                tasks.append(self.marketaux_service.get_news_for_ticker(ticker, hours_back))
            if "finnhub" in self.available_services:
                tasks.append(self.finnhub_service.get_company_news(ticker))
            
            # Wait for all results
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine and deduplicate
            return self._combine_news_results(ticker, results)
            
        except Exception as e:
            logger.error(f"Error aggregating news for {ticker}: {str(e)}")
            return {
                "ticker": ticker,
                "articles": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_watchlist_news(self, tickers: List[str], hours_back: int = 4) -> Dict:
        """
        Get news for multiple tickers
        
        Args:
            tickers: List of stock tickers
            hours_back: How many hours of news to fetch
            
        Returns:
            News grouped by ticker
        """
        try:
            # Get news for all tickers in parallel
            tasks = [self.get_aggregated_news(ticker, hours_back) for ticker in tickers]
            results = await asyncio.gather(*tasks)
            
            # Group by ticker
            news_by_ticker = {}
            for i, ticker in enumerate(tickers):
                news_by_ticker[ticker] = results[i]
            
            # Summary statistics
            total_articles = sum(len(news.get("articles", [])) for news in news_by_ticker.values())
            fresh_articles = sum(
                len([a for a in news.get("articles", []) if a.get("is_fresh", False)])
                for news in news_by_ticker.values()
            )
            
            return {
                "news_by_ticker": news_by_ticker,
                "total_articles": total_articles,
                "fresh_articles": fresh_articles,
                "tickers_with_news": len([t for t, n in news_by_ticker.items() if n.get("articles")]),
                "timestamp": datetime.now().isoformat(),
                "sources_used": self.available_services
            }
            
        except Exception as e:
            logger.error(f"Error getting watchlist news: {str(e)}")
            return {
                "news_by_ticker": {},
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _get_gemini_news(self, ticker: str) -> Dict:
        """Get news from Gemini with error handling"""
        try:
            # Get company name for better search
            company_names = {
                "ASML.AS": "ASML",
                "SHEL.AS": "Shell",
                "UNA.AS": "Unilever",
                "SAP.DE": "SAP",
                "SIE.DE": "Siemens",
                "MC.PA": "LVMH",
                "TTE.PA": "TotalEnergies",
                "NESN.SW": "Nestle",
                "NOVN.SW": "Novartis",
                "INGA.AS": "ING Group"
            }
            
            company_name = company_names.get(ticker, ticker.split('.')[0])
            result = await self.gemini_service.search_news(ticker, company_name)
            
            # Add api_source to each article
            if "articles" in result:
                for article in result["articles"]:
                    article["api_source"] = "gemini"
                    # Ensure we have time-based fields
                    if "published" in article and "age_hours" not in article:
                        article["age_hours"] = self._calculate_age_hours(article["published"])
                    if "is_fresh" not in article:
                        article["is_fresh"] = article.get("age_hours", 999) <= 4
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini news error for {ticker}: {str(e)}")
            return {"ticker": ticker, "articles": [], "error": str(e)}
    
    def _combine_news_results(self, ticker: str, results: List) -> Dict:
        """Combine news from multiple sources and remove duplicates"""
        
        all_articles = []
        errors = []
        sources_succeeded = []
        
        # Extract articles from each result
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append(str(result))
                continue
            
            if isinstance(result, dict):
                if "error" in result:
                    errors.append(result["error"])
                
                articles = result.get("articles", [])
                if articles:
                    source = articles[0].get("api_source", "unknown") if articles else "unknown"
                    sources_succeeded.append(source)
                    all_articles.extend(articles)
        
        # Deduplicate based on headline similarity
        unique_articles = self._deduplicate_articles(all_articles)
        
        # Sort by freshness and relevance
        unique_articles.sort(key=lambda x: (
            -int(x.get("is_fresh", False)),  # Fresh news first
            x.get("age_hours", 999),  # Then by age
            -x.get("materiality", 0)  # Then by materiality
        ))
        
        # Calculate statistics
        fresh_count = len([a for a in unique_articles if a.get("is_fresh", False)])
        
        return {
            "ticker": ticker,
            "articles": unique_articles,
            "count": len(unique_articles),
            "fresh_count": fresh_count,
            "has_fresh_news": fresh_count > 0,
            "sources_succeeded": sources_succeeded,
            "sources_failed": len(errors),
            "errors": errors if errors else None,
            "timestamp": datetime.now().isoformat()
        }
    
    def _deduplicate_articles(self, articles: List[Dict]) -> List[Dict]:
        """Remove duplicate articles based on headline similarity"""
        
        if not articles:
            return []
        
        unique = []
        seen_headlines = set()
        
        for article in articles:
            headline = article.get("headline", "").lower().strip()
            
            # Skip if no headline
            if not headline:
                continue
            
            # Check for similar headlines (simple approach)
            is_duplicate = False
            for seen in seen_headlines:
                # If headlines are very similar (>80% same words)
                if self._headline_similarity(headline, seen) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(article)
                seen_headlines.add(headline)
        
        return unique
    
    def _headline_similarity(self, h1: str, h2: str) -> float:
        """Calculate similarity between two headlines (0-1)"""
        
        # Simple word-based similarity
        words1 = set(h1.split())
        words2 = set(h2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_age_hours(self, timestamp_str: str) -> float:
        """Calculate age in hours from timestamp string"""
        try:
            # Handle various timestamp formats
            if "ago" in timestamp_str.lower():
                # Parse "X hours ago" format
                import re
                match = re.search(r'(\d+)\s*hours?\s*ago', timestamp_str.lower())
                if match:
                    return float(match.group(1))
                match = re.search(r'(\d+)\s*minutes?\s*ago', timestamp_str.lower())
                if match:
                    return float(match.group(1)) / 60
                return 999  # Unknown format
            else:
                # Parse ISO format or other date formats
                from dateutil import parser
                timestamp = parser.parse(timestamp_str)
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=None)
                    now = datetime.now()
                else:
                    now = datetime.now(timestamp.tzinfo)
                
                age_hours = (now - timestamp).total_seconds() / 3600
                return abs(age_hours)  # Use abs to handle timezone issues
                
        except Exception as e:
            logger.warning(f"Could not parse timestamp '{timestamp_str}': {e}")
            return 999  # Return high number for unknown timestamps
    
    async def get_sentiment_analysis(self, ticker: str, articles: List[Dict]) -> Dict:
        """
        Analyze overall sentiment from aggregated news
        
        Args:
            ticker: Stock ticker
            articles: List of news articles
            
        Returns:
            Overall sentiment analysis
        """
        if not articles:
            return {
                "ticker": ticker,
                "overall_sentiment": "neutral",
                "confidence": 0,
                "reason": "No recent news found"
            }
        
        # Count sentiments
        sentiment_counts = defaultdict(int)
        total_materiality = 0
        materiality_count = 0
        
        for article in articles:
            sentiment = article.get("sentiment", "neutral").lower()
            sentiment_counts[sentiment] += 1
            
            if "materiality" in article:
                total_materiality += article["materiality"]
                materiality_count += 1
        
        # Determine overall sentiment
        total = sum(sentiment_counts.values())
        if total == 0:
            return {
                "ticker": ticker,
                "overall_sentiment": "neutral",
                "confidence": 0
            }
        
        # Calculate weighted sentiment
        positive_ratio = sentiment_counts.get("positive", 0) / total
        negative_ratio = sentiment_counts.get("negative", 0) / total
        
        if positive_ratio > 0.6:
            overall = "bullish"
            confidence = int(positive_ratio * 100)
        elif negative_ratio > 0.6:
            overall = "bearish"
            confidence = int(negative_ratio * 100)
        else:
            overall = "neutral"
            confidence = 50
        
        avg_materiality = total_materiality / materiality_count if materiality_count > 0 else 5
        
        return {
            "ticker": ticker,
            "overall_sentiment": overall,
            "confidence": confidence,
            "article_count": total,
            "sentiment_breakdown": dict(sentiment_counts),
            "average_materiality": round(avg_materiality, 1),
            "fresh_news_count": len([a for a in articles if a.get("is_fresh", False)]),
            "recommendation": self._get_trading_recommendation(overall, confidence, avg_materiality)
        }
    
    def _get_trading_recommendation(self, sentiment: str, confidence: int, materiality: float) -> str:
        """Generate trading recommendation based on sentiment analysis"""
        
        if confidence < 60 or materiality < 5:
            return "HOLD - Insufficient conviction or low materiality"
        
        if sentiment == "bullish" and confidence >= 70:
            return "BUY - Strong positive sentiment with high confidence"
        elif sentiment == "bearish" and confidence >= 70:
            return "SELL - Strong negative sentiment with high confidence"
        elif sentiment == "bullish":
            return "WATCH - Positive sentiment, monitor for entry"
        elif sentiment == "bearish":
            return "CAUTION - Negative sentiment, consider reducing exposure"
        else:
            return "HOLD - Neutral market sentiment"