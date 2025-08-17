from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio

from services.gemini_service import GeminiService
from models.signal import Signal, SignalStatus
from database import SessionLocal
from config import settings

class ScoutAgent:
    """
    Scout Agent - Monitors news for watchlist stocks every 30 minutes
    Uses Gemini with Google Search grounding to find breaking news
    """
    
    def __init__(self):
        self.gemini_service = GeminiService()
        self.watchlist = settings.watchlist
        self.company_names = {
            "ASML.AS": "ASML Holding",
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
        logger.info(f"Scout Agent initialized with {len(self.watchlist)} stocks")
    
    async def scan_all_stocks(self) -> List[Dict]:
        """
        Scan all stocks in watchlist for news
        
        Returns:
            List of news findings for all stocks
        """
        logger.info("Starting news scan for all watchlist stocks")
        all_news = []
        
        # Create tasks for parallel processing
        tasks = []
        for ticker in self.watchlist:
            company_name = self.company_names.get(ticker, ticker)
            tasks.append(self.scan_stock(ticker, company_name))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error scanning {self.watchlist[i]}: {result}")
            elif result and result.get('articles'):
                all_news.append(result)
        
        logger.info(f"News scan complete. Found news for {len(all_news)} stocks")
        return all_news
    
    async def scan_stock(self, ticker: str, company_name: str = None) -> Optional[Dict]:
        """
        Scan news for a specific stock
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name for better search
            
        Returns:
            News data if found, None otherwise
        """
        try:
            logger.debug(f"Scanning news for {ticker}")
            
            # Search news using Gemini with Google Search
            news_data = await self.gemini_service.search_news(ticker, company_name)
            
            if not news_data.get('articles'):
                logger.debug(f"No news found for {ticker}")
                return None
            
            # Filter for relevant news (high relevance or breaking news)
            relevant_articles = self._filter_relevant_news(news_data['articles'])
            
            if relevant_articles:
                news_data['articles'] = relevant_articles
                news_data['has_material_news'] = True
                
                # Store important findings in database
                await self._store_news_findings(ticker, news_data)
                
                logger.info(f"Found {len(relevant_articles)} relevant news items for {ticker}")
                return news_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error scanning {ticker}: {str(e)}")
            return None
    
    def _filter_relevant_news(self, articles: List[Dict]) -> List[Dict]:
        """
        Filter news articles for relevance and materiality
        
        Args:
            articles: List of news articles
            
        Returns:
            Filtered list of relevant articles
        """
        relevant = []
        
        for article in articles:
            # Check relevance
            relevance = article.get('relevance', '').lower()
            sentiment = article.get('sentiment', '').lower()
            headline = article.get('headline', '').lower()
            
            # High relevance or strong sentiment
            if relevance == 'high':
                relevant.append(article)
            elif sentiment in ['positive', 'negative', 'bullish', 'bearish']:
                # Check for material keywords
                material_keywords = [
                    'earnings', 'profit', 'revenue', 'guidance', 'upgrade', 'downgrade',
                    'merger', 'acquisition', 'fda', 'approval', 'lawsuit', 'investigation',
                    'ceo', 'dividend', 'buyback', 'restructuring', 'bankruptcy',
                    'contract', 'partnership', 'breakthrough', 'recall'
                ]
                
                if any(keyword in headline for keyword in material_keywords):
                    relevant.append(article)
        
        return relevant
    
    async def _store_news_findings(self, ticker: str, news_data: Dict):
        """
        Store news findings that might generate signals
        
        Args:
            ticker: Stock ticker
            news_data: News data to store
        """
        db = SessionLocal()
        try:
            # Check if we already have a recent signal for this ticker
            recent_signal = db.query(Signal).filter(
                Signal.ticker == ticker,
                Signal.created_at >= datetime.now() - timedelta(hours=4)
            ).first()
            
            if recent_signal:
                logger.debug(f"Recent signal already exists for {ticker}, skipping")
                return
            
            # Calculate aggregate sentiment
            sentiments = [a.get('sentiment', 'neutral').lower() for a in news_data['articles']]
            bullish_count = sum(1 for s in sentiments if s in ['positive', 'bullish'])
            bearish_count = sum(1 for s in sentiments if s in ['negative', 'bearish'])
            
            # Determine overall sentiment
            if bullish_count > bearish_count and bullish_count >= 2:
                overall_sentiment = 'bullish'
            elif bearish_count > bullish_count and bearish_count >= 2:
                overall_sentiment = 'bearish'
            else:
                overall_sentiment = 'neutral'
            
            # Store as potential signal if sentiment is strong
            if overall_sentiment != 'neutral':
                # Create news summary
                news_summary = self._create_news_summary(news_data)
                
                # This will be picked up by the Analyst agent
                signal = Signal(
                    ticker=ticker,
                    exchange=self._get_exchange(ticker),
                    signal_type='BUY' if overall_sentiment == 'bullish' else 'SELL',
                    confidence=0,  # Will be set by Analyst
                    news_source=news_summary,
                    reasoning="Pending analysis",
                    materiality_score=7,  # Initial score
                    status=SignalStatus.PENDING,
                    expires_at=datetime.now() + timedelta(hours=2)
                )
                
                db.add(signal)
                db.commit()
                logger.info(f"Created pending signal for {ticker} based on {overall_sentiment} news")
                
        except Exception as e:
            logger.error(f"Error storing news findings: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    def _create_news_summary(self, news_data: Dict) -> str:
        """Create a summary of news articles"""
        summary_parts = []
        
        for article in news_data.get('articles', [])[:3]:  # Top 3 articles
            summary_parts.append(
                f"• {article.get('headline', 'No headline')} "
                f"({article.get('source', 'Unknown')}) "
                f"- {article.get('sentiment', 'neutral')}"
            )
        
        return "\n".join(summary_parts)
    
    def _get_exchange(self, ticker: str) -> str:
        """Get exchange based on ticker suffix"""
        if ticker.endswith('.AS'):
            return 'AMS'
        elif ticker.endswith('.DE'):
            return 'XETRA'
        elif ticker.endswith('.PA'):
            return 'EPA'
        elif ticker.endswith('.SW'):
            return 'SIX'
        else:
            return 'UNKNOWN'
    
    async def run_scheduled_scan(self):
        """Run scheduled news scan (called every 30 minutes)"""
        try:
            logger.info("=== Starting scheduled news scan ===")
            
            # Check if market is open or about to open
            now = datetime.now()
            market_open = now.replace(hour=settings.market_open_hour, minute=0)
            market_close = now.replace(
                hour=settings.market_close_hour, 
                minute=settings.market_close_minute
            )
            
            # Scan news 1 hour before market open through 1 hour after close
            scan_start = market_open - timedelta(hours=1)
            scan_end = market_close + timedelta(hours=1)
            
            if not (scan_start <= now <= scan_end):
                logger.info("Outside scanning hours, skipping")
                return
            
            # Run the scan
            news_results = await self.scan_all_stocks()
            
            # Log summary
            total_articles = sum(len(r.get('articles', [])) for r in news_results)
            logger.info(f"Scan complete: {len(news_results)} stocks with news, {total_articles} total articles")
            
            return news_results
            
        except Exception as e:
            logger.error(f"Error in scheduled scan: {str(e)}")
            return []