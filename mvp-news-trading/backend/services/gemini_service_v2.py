"""
Gemini Service V2 - Using Google Search Grounding for real-time news
"""

from google import genai
from google.genai import types
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from config import settings
import json


class GeminiServiceV2:
    """Enhanced Gemini service with Google Search grounding for real-time news"""
    
    def __init__(self):
        """Initialize Gemini with API key and grounding tool"""
        if not settings.gemini_api_key:
            logger.error("Gemini API key not found")
            raise ValueError("Gemini API key is required")
        
        # Initialize client with API key
        self.client = genai.Client(api_key=settings.gemini_api_key)
        
        # Define the grounding tool for Google Search
        self.grounding_tool = types.Tool(
            google_search=types.GoogleSearch()
        )
        
        # Configure generation settings with grounding
        self.config = types.GenerateContentConfig(
            tools=[self.grounding_tool],
            temperature=0.3,  # Lower temperature for factual news
        )
        
        logger.info("Gemini V2 service initialized with Google Search grounding")
    
    async def search_real_time_news(self, ticker: str, company_name: str = None) -> Dict:
        """
        Search for real-time news using Google Search grounding
        
        Args:
            ticker: Stock ticker (e.g., "ASML.AS")
            company_name: Company name for better search
            
        Returns:
            Dictionary with real-time news and grounding metadata
        """
        try:
            company = company_name or ticker
            current_time = datetime.now()
            
            # Create a targeted prompt for real-time news
            prompt = f"""
            Current time: {current_time.strftime('%B %d, %Y at %H:%M %Z')}
            
            Search for the LATEST breaking news about {company} ({ticker}) stock.
            
            Focus on:
            1. News from the last 4 hours (priority) or last 24 hours
            2. Price-moving events: earnings, M&A, regulatory decisions
            3. Trading halts or unusual volume
            4. Analyst upgrades/downgrades TODAY
            5. Management changes or major announcements
            
            For each news item found, provide:
            - Exact headline
            - Source website
            - EXACT publication time (not just date)
            - Brief summary (2-3 sentences)
            - Sentiment: POSITIVE/NEGATIVE/NEUTRAL
            - Materiality score: 1-10 (10 being most price-moving)
            
            Format as JSON array with these fields:
            [{{
                "headline": "...",
                "source": "...",
                "published_at": "...",
                "summary": "...",
                "sentiment": "...",
                "materiality": X,
                "url": "..."
            }}]
            
            If no recent news exists, return empty array [].
            """
            
            # Make grounded request
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",  # Latest model with grounding
                contents=prompt,
                config=self.config
            )
            
            # Parse response and extract grounding metadata
            return self._parse_grounded_response(response, ticker)
            
        except Exception as e:
            logger.error(f"Error searching real-time news for {ticker}: {str(e)}")
            return {
                "ticker": ticker,
                "articles": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def analyze_news_batch(self, tickers: List[str]) -> Dict:
        """
        Search for news on multiple tickers efficiently
        
        Args:
            tickers: List of stock tickers
            
        Returns:
            News grouped by ticker with grounding
        """
        try:
            # Build efficient batch prompt
            ticker_list = ", ".join([f"{t}" for t in tickers])
            current_time = datetime.now()
            
            prompt = f"""
            Current time: {current_time.strftime('%B %d, %Y at %H:%M %Z')}
            
            Search for the LATEST news (last 4-24 hours) for these EU stocks:
            {ticker_list}
            
            For each company with news, provide:
            - Ticker symbol
            - News headline
            - Source and exact time
            - Brief summary
            - Sentiment and materiality (1-10)
            
            Focus only on material, price-moving news.
            Skip companies with no recent news.
            
            Format as JSON:
            {{
                "TICKER": [{{
                    "headline": "...",
                    "source": "...",
                    "published_at": "...",
                    "summary": "...",
                    "sentiment": "POSITIVE/NEGATIVE/NEUTRAL",
                    "materiality": X
                }}]
            }}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=self.config
            )
            
            return self._parse_batch_response(response, tickers)
            
        except Exception as e:
            logger.error(f"Error in batch news search: {str(e)}")
            return {"error": str(e), "news_by_ticker": {}}
    
    def _parse_grounded_response(self, response, ticker: str) -> Dict:
        """Parse response with grounding metadata"""
        
        articles = []
        
        try:
            # Extract text response
            text = response.text if hasattr(response, 'text') else str(response)
            
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\[.*?\]', text, re.DOTALL)
            if json_match:
                news_data = json.loads(json_match.group())
                
                for item in news_data:
                    # Calculate age
                    published_at = item.get("published_at", "")
                    age_hours = self._calculate_age(published_at)
                    
                    article = {
                        "ticker": ticker,
                        "headline": item.get("headline", ""),
                        "source": item.get("source", "Unknown"),
                        "url": item.get("url", ""),
                        "published_at": published_at,
                        "timestamp": datetime.now().isoformat(),
                        "summary": item.get("summary", ""),
                        "sentiment": item.get("sentiment", "neutral").lower(),
                        "materiality": item.get("materiality", 5),
                        "age_hours": age_hours,
                        "is_fresh": age_hours <= 4,
                        "api_source": "gemini_grounded"
                    }
                    articles.append(article)
            
            # Extract grounding metadata if available
            grounding_metadata = {}
            if hasattr(response, 'grounding_metadata'):
                grounding_metadata = {
                    "search_queries": response.grounding_metadata.get("search_queries", []),
                    "sources": response.grounding_metadata.get("sources", [])
                }
            
        except json.JSONDecodeError:
            logger.warning(f"Could not parse JSON from Gemini response for {ticker}")
            # Fall back to text parsing
            articles = self._parse_text_response(text, ticker)
        except Exception as e:
            logger.error(f"Error parsing grounded response: {str(e)}")
        
        return {
            "ticker": ticker,
            "articles": articles,
            "count": len(articles),
            "has_fresh_news": any(a["is_fresh"] for a in articles),
            "timestamp": datetime.now().isoformat(),
            "source": "gemini_grounded",
            "grounding_metadata": grounding_metadata if 'grounding_metadata' in locals() else {}
        }
    
    def _parse_batch_response(self, response, tickers: List[str]) -> Dict:
        """Parse batch response for multiple tickers"""
        
        news_by_ticker = {ticker: [] for ticker in tickers}
        
        try:
            text = response.text if hasattr(response, 'text') else str(response)
            
            # Try to parse JSON
            import re
            json_match = re.search(r'\{.*?\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                
                for ticker, articles in data.items():
                    if ticker in news_by_ticker and isinstance(articles, list):
                        for item in articles:
                            age_hours = self._calculate_age(item.get("published_at", ""))
                            
                            article = {
                                "ticker": ticker,
                                "headline": item.get("headline", ""),
                                "source": item.get("source", "Unknown"),
                                "published_at": item.get("published_at", ""),
                                "summary": item.get("summary", ""),
                                "sentiment": item.get("sentiment", "neutral").lower(),
                                "materiality": item.get("materiality", 5),
                                "age_hours": age_hours,
                                "is_fresh": age_hours <= 4,
                                "api_source": "gemini_grounded"
                            }
                            news_by_ticker[ticker].append(article)
        
        except Exception as e:
            logger.error(f"Error parsing batch response: {str(e)}")
        
        return {
            "news_by_ticker": news_by_ticker,
            "total_articles": sum(len(articles) for articles in news_by_ticker.values()),
            "timestamp": datetime.now().isoformat(),
            "source": "gemini_grounded"
        }
    
    def _parse_text_response(self, text: str, ticker: str) -> List[Dict]:
        """Fallback text parser when JSON parsing fails"""
        
        articles = []
        lines = text.split('\n')
        current_article = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_article and 'headline' in current_article:
                    current_article['ticker'] = ticker
                    current_article['api_source'] = 'gemini_grounded'
                    current_article['is_fresh'] = True  # Assume fresh if from search
                    articles.append(current_article)
                    current_article = {}
                continue
            
            # Parse different fields
            lower_line = line.lower()
            if 'headline:' in lower_line:
                current_article['headline'] = line.split(':', 1)[1].strip()
            elif 'source:' in lower_line:
                current_article['source'] = line.split(':', 1)[1].strip()
            elif 'published' in lower_line or 'time:' in lower_line:
                current_article['published_at'] = line.split(':', 1)[1].strip()
            elif 'sentiment:' in lower_line:
                current_article['sentiment'] = line.split(':', 1)[1].strip().lower()
            elif 'materiality:' in lower_line:
                try:
                    current_article['materiality'] = int(line.split(':', 1)[1].strip())
                except:
                    current_article['materiality'] = 5
            elif 'summary:' in lower_line:
                current_article['summary'] = line.split(':', 1)[1].strip()
        
        # Add last article if exists
        if current_article and 'headline' in current_article:
            current_article['ticker'] = ticker
            current_article['api_source'] = 'gemini_grounded'
            current_article['is_fresh'] = True
            articles.append(current_article)
        
        return articles
    
    def _calculate_age(self, published_str: str) -> float:
        """Calculate age in hours from published string"""
        
        try:
            # Handle various time formats
            if "hour" in published_str.lower() and "ago" in published_str.lower():
                import re
                match = re.search(r'(\d+)\s*hour', published_str.lower())
                if match:
                    return float(match.group(1))
            
            if "minute" in published_str.lower() and "ago" in published_str.lower():
                import re
                match = re.search(r'(\d+)\s*minute', published_str.lower())
                if match:
                    return float(match.group(1)) / 60
            
            # Try parsing as date
            from dateutil import parser
            published_date = parser.parse(published_str)
            age_hours = (datetime.now() - published_date).total_seconds() / 3600
            return abs(age_hours)
            
        except:
            return 999  # Unknown age