import google.generativeai as genai
from typing import Dict, List, Optional
from loguru import logger
from config import settings
import json
from datetime import datetime

class GeminiService:
    """Service for interacting with Gemini API with Google Search grounding"""
    
    def __init__(self):
        """Initialize Gemini with API key"""
        if not settings.gemini_api_key:
            logger.error("Gemini API key not found")
            raise ValueError("Gemini API key is required")
        
        genai.configure(api_key=settings.gemini_api_key)
        
        # Initialize model - simplified for now
        # Google Search requires specific setup
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        logger.info("Gemini service initialized")
    
    async def search_news(self, ticker: str, company_name: str = None) -> Dict:
        """
        Search for latest news about a stock using Gemini with Google Search
        
        Args:
            ticker: Stock ticker symbol
            company_name: Company name for better search results
            
        Returns:
            Dictionary with news results and analysis
        """
        try:
            # Create search prompt
            prompt = self._create_news_search_prompt(ticker, company_name)
            
            # Generate content
            response = self.model.generate_content(prompt)
            
            # Parse and structure the response
            news_data = self._parse_news_response(response.text, ticker)
            
            logger.info(f"Found {len(news_data.get('articles', []))} news items for {ticker}")
            return news_data
            
        except Exception as e:
            logger.error(f"Error searching news for {ticker}: {str(e)}")
            return {
                "ticker": ticker,
                "articles": [],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def analyze_sentiment(self, news_text: str, ticker: str) -> Dict:
        """
        Analyze sentiment and trading implications of news
        
        Args:
            news_text: Combined news text to analyze
            ticker: Stock ticker for context
            
        Returns:
            Sentiment analysis and trading signals
        """
        try:
            prompt = f"""
            Analyze the following news for {ticker} and provide trading insights:
            
            News: {news_text}
            
            Provide analysis in this JSON format:
            {{
                "sentiment": "bullish/bearish/neutral",
                "confidence": 0-100,
                "materiality": 1-10,
                "price_impact": "positive/negative/neutral",
                "time_horizon": "intraday/short-term/long-term",
                "key_factors": ["factor1", "factor2"],
                "trading_action": "buy/sell/hold",
                "reasoning": "detailed explanation"
            }}
            """
            
            response = self.model.generate_content(prompt)
            
            # Try to parse JSON from response
            try:
                # Extract JSON from response text
                text = response.text
                start = text.find('{')
                end = text.rfind('}') + 1
                if start >= 0 and end > start:
                    json_str = text[start:end]
                    return json.loads(json_str)
            except:
                # Fallback to text parsing
                return self._parse_sentiment_text(response.text)
                
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {
                "sentiment": "neutral",
                "confidence": 0,
                "error": str(e)
            }
    
    def _create_news_search_prompt(self, ticker: str, company_name: str = None) -> str:
        """Create optimized prompt for news search"""
        
        company = company_name or ticker
        current_time = datetime.now()
        
        return f"""
        CRITICAL: Today is {current_time.strftime('%B %d, %Y at %H:%M %Z')}
        
        Using Google Search, find ONLY the MOST RECENT news for {company} ({ticker}).
        
        TIME REQUIREMENTS - ABSOLUTELY CRITICAL:
        - ONLY news from the LAST 4 HOURS
        - If no news in last 4 hours, search last 24 hours
        - REJECT any news older than 48 hours
        - ALWAYS include exact publication time (not just date)
        - Use search operators like "after:2025-08-16" or "when:4h" 
        
        Focus on these reliable financial sources:
        - Reuters (reuters.com)
        - Bloomberg (bloomberg.com)
        - Financial Times (ft.com)
        - MarketWatch (marketwatch.com)
        - CNBC Europe (cnbc.com)
        - Yahoo Finance (finance.yahoo.com)
        - Investing.com
        - Euronext Live (live.euronext.com)
        - Local sources: Handelsblatt (DE), Les Echos (FR), Het Financieele Dagblad (NL)
        
        Search queries to use:
        - "{company} {ticker} news today"
        - "{company} latest news past 4 hours"
        - "{ticker} stock news {current_time.strftime('%Y-%m-%d')}"
        - "{company} breaking news"
        
        Types of news to find:
        1. Breaking news and price-moving events
        2. Trading halts or unusual volume
        3. Analyst actions (upgrades/downgrades) TODAY
        4. Earnings or guidance changes
        5. M&A activity or rumors
        6. Management changes
        7. Regulatory approvals/issues
        8. Major contract wins/losses
        
        For each news item, you MUST provide:
        - Source: [exact website]
        - Headline: [exact headline]
        - Time: [EXACT time like "10:45 AM CET" or "2 hours ago" - NEVER just a date]
        - Age: [how many hours/minutes old]
        - Key points: [2-3 bullet points]
        - Price Impact: [High/Medium/Low]
        - Sentiment: [Positive/Negative/Neutral]
        
        If you find news from January 2025 or older, EXPLICITLY mark it as "OUTDATED - DO NOT USE"
        
        If no recent news exists, return:
        "NO RECENT NEWS - Last update was [X hours/days] ago: [brief description]"
        """
    
    def _parse_news_response(self, response_text: str, ticker: str) -> Dict:
        """Parse Gemini's response into structured news data"""
        
        articles = []
        lines = response_text.split('\n')
        current_article = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_article:
                    articles.append(current_article)
                    current_article = {}
                continue
            
            # Parse different fields
            if 'source:' in line.lower():
                current_article['source'] = line.split(':', 1)[1].strip()
            elif 'headline:' in line.lower():
                current_article['headline'] = line.split(':', 1)[1].strip()
            elif 'url:' in line.lower() or 'link:' in line.lower():
                current_article['url'] = line.split(':', 1)[1].strip()
            elif 'sentiment:' in line.lower():
                sentiment = line.split(':', 1)[1].strip().lower()
                current_article['sentiment'] = sentiment
            elif 'relevance:' in line.lower():
                current_article['relevance'] = line.split(':', 1)[1].strip()
            elif 'time:' in line.lower() or 'published:' in line.lower():
                current_article['published'] = line.split(':', 1)[1].strip()
            elif line.startswith('-') or line.startswith('•'):
                # Key points
                if 'key_points' not in current_article:
                    current_article['key_points'] = []
                current_article['key_points'].append(line[1:].strip())
        
        # Add last article if exists
        if current_article:
            articles.append(current_article)
        
        return {
            "ticker": ticker,
            "articles": articles,
            "count": len(articles),
            "timestamp": datetime.now().isoformat(),
            "has_breaking_news": any(
                'breaking' in str(a.get('headline', '')).lower() 
                for a in articles
            )
        }
    
    def _parse_sentiment_text(self, text: str) -> Dict:
        """Fallback parser for sentiment analysis"""
        
        result = {
            "sentiment": "neutral",
            "confidence": 50,
            "materiality": 5,
            "price_impact": "neutral",
            "trading_action": "hold"
        }
        
        text_lower = text.lower()
        
        # Detect sentiment
        if any(word in text_lower for word in ['bullish', 'positive', 'upgrade', 'buy']):
            result["sentiment"] = "bullish"
            result["price_impact"] = "positive"
            result["trading_action"] = "buy"
        elif any(word in text_lower for word in ['bearish', 'negative', 'downgrade', 'sell']):
            result["sentiment"] = "bearish"
            result["price_impact"] = "negative"
            result["trading_action"] = "sell"
        
        # Extract confidence if mentioned
        import re
        confidence_match = re.search(r'(\d+)%?\s*confiden', text_lower)
        if confidence_match:
            result["confidence"] = int(confidence_match.group(1))
        
        return result