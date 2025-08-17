from typing import Dict, Optional, List
from datetime import datetime, timedelta
from loguru import logger
import google.generativeai as genai
import json

from models.signal import Signal, SignalStatus
from database import SessionLocal
from config import settings
from services.alpaca_service import AlpacaService

class AnalystAgent:
    """
    Analyst Agent - Converts raw news information into actionable trade signals
    Analyzes sentiment, materiality, and market conditions to generate signals
    """
    
    def __init__(self):
        # Configure Gemini for analysis
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.alpaca = AlpacaService()
        
        # Signal generation thresholds
        self.confidence_threshold = settings.confidence_threshold
        self.min_materiality_score = 7
        
        logger.info("Analyst Agent initialized")
    
    async def analyze_pending_signals(self) -> List[Signal]:
        """
        Analyze all pending signals from Scout agent
        
        Returns:
            List of analyzed signals ready for risk assessment
        """
        db = SessionLocal()
        try:
            # Get all pending signals
            pending_signals = db.query(Signal).filter(
                Signal.status == SignalStatus.PENDING
            ).all()
            
            logger.info(f"Found {len(pending_signals)} pending signals to analyze")
            
            analyzed_signals = []
            for signal in pending_signals:
                analyzed = await self.analyze_signal(signal)
                if analyzed:
                    analyzed_signals.append(analyzed)
            
            return analyzed_signals
            
        finally:
            db.close()
    
    async def analyze_signal(self, signal: Signal) -> Optional[Signal]:
        """
        Analyze a single signal and determine if it's actionable
        
        Args:
            signal: Pending signal to analyze
            
        Returns:
            Updated signal with analysis or None if not actionable
        """
        db = SessionLocal()
        try:
            logger.info(f"Analyzing signal for {signal.ticker}")
            
            # Get current market data
            market_data = await self._get_market_data(signal.ticker)
            
            # Perform deep analysis using AI
            analysis = await self._perform_ai_analysis(
                signal.ticker,
                signal.news_source,
                market_data
            )
            
            if not analysis:
                logger.warning(f"Failed to analyze signal for {signal.ticker}")
                signal.status = SignalStatus.REJECTED
                signal.reasoning = "Analysis failed"
                db.commit()
                return None
            
            # Update signal with analysis results
            signal.confidence = analysis['confidence']
            signal.signal_type = analysis['signal_type']
            signal.entry_price = analysis['entry_price']
            signal.stop_loss = analysis['stop_loss']
            signal.target_price = analysis['target_price']
            signal.reasoning = analysis['reasoning']
            signal.materiality_score = analysis['materiality_score']
            
            # Check if signal meets thresholds
            if signal.confidence >= self.confidence_threshold and \
               signal.materiality_score >= self.min_materiality_score:
                signal.status = SignalStatus.ANALYZED
                logger.info(f"Signal for {signal.ticker} approved with {signal.confidence}% confidence")
            else:
                signal.status = SignalStatus.REJECTED
                signal.reasoning += f" (Confidence: {signal.confidence}%, Materiality: {signal.materiality_score})"
                logger.info(f"Signal for {signal.ticker} rejected - below thresholds")
            
            db.commit()
            return signal if signal.status == SignalStatus.ANALYZED else None
            
        except Exception as e:
            logger.error(f"Error analyzing signal: {str(e)}")
            db.rollback()
            return None
        finally:
            db.close()
    
    async def _get_market_data(self, ticker: str) -> Dict:
        """
        Get current market data for the ticker
        
        Args:
            ticker: Stock ticker
            
        Returns:
            Market data dictionary
        """
        try:
            # For EU stocks, we might need to handle differently
            # For now, return mock data if Alpaca doesn't support EU stocks
            data = {
                'current_price': 100.0,  # Would get from market data API
                'volume': 1000000,
                'avg_volume': 800000,
                'day_change': 0.5,
                'volatility': 0.02
            }
            
            # Try to get real data if available
            # quote = await self.alpaca.get_latest_quote(ticker)
            # if quote:
            #     data['current_price'] = float(quote.ask_price)
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting market data for {ticker}: {str(e)}")
            return {}
    
    async def _perform_ai_analysis(self, ticker: str, news: str, market_data: Dict) -> Optional[Dict]:
        """
        Perform AI analysis on the signal
        
        Args:
            ticker: Stock ticker
            news: News summary
            market_data: Current market data
            
        Returns:
            Analysis results dictionary
        """
        try:
            prompt = f"""
            You are an expert financial analyst. Analyze this information and provide a trading signal.
            
            Stock: {ticker}
            
            News Information:
            {news}
            
            Market Data:
            - Current Price: ${market_data.get('current_price', 'N/A')}
            - Volume: {market_data.get('volume', 'N/A')}
            - Day Change: {market_data.get('day_change', 'N/A')}%
            
            Provide your analysis in JSON format with exactly these fields:
            {{
                "signal_type": "BUY" or "SELL" or "HOLD",
                "confidence": <number 0-100>,
                "materiality_score": <number 1-10>,
                "entry_price": <number>,
                "stop_loss": <number>,
                "target_price": <number>,
                "reasoning": "<detailed explanation>",
                "risk_factors": ["<risk1>", "<risk2>"],
                "catalysts": ["<catalyst1>", "<catalyst2>"]
            }}
            
            Consider:
            1. News sentiment and materiality
            2. Potential market impact
            3. Risk/reward ratio
            4. Technical levels for entry/exit
            5. Time horizon (intraday trading)
            
            Be conservative with confidence scores. Only give high confidence (>80) for very clear opportunities.
            """
            
            response = self.model.generate_content(prompt)
            
            # Parse JSON from response
            text = response.text
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            
            if json_match:
                analysis = json.loads(json_match.group())
                
                # Validate required fields
                required_fields = ['signal_type', 'confidence', 'materiality_score', 
                                 'entry_price', 'stop_loss', 'target_price', 'reasoning']
                
                if all(field in analysis for field in required_fields):
                    # Ensure prices are reasonable
                    current_price = market_data.get('current_price', 100)
                    
                    # Set reasonable defaults if AI gives unrealistic values
                    if analysis['signal_type'] == 'BUY':
                        if analysis['stop_loss'] >= current_price:
                            analysis['stop_loss'] = current_price * 0.98  # 2% stop
                        if analysis['target_price'] <= current_price:
                            analysis['target_price'] = current_price * 1.03  # 3% target
                    elif analysis['signal_type'] == 'SELL':
                        if analysis['stop_loss'] <= current_price:
                            analysis['stop_loss'] = current_price * 1.02  # 2% stop
                        if analysis['target_price'] >= current_price:
                            analysis['target_price'] = current_price * 0.97  # 3% target
                    
                    return analysis
                else:
                    logger.error(f"Missing required fields in AI analysis")
                    return None
            else:
                logger.error("Could not parse JSON from AI response")
                return None
                
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            return None
    
    async def generate_signal_from_webhook(self, webhook_data: Dict) -> Optional[Signal]:
        """
        Generate a signal from webhook prediction data
        
        Args:
            webhook_data: Data from prediction webhook
            
        Returns:
            Generated signal or None
        """
        try:
            # Extract data from webhook
            ticker = webhook_data.get('ticker')
            prediction = webhook_data.get('prediction', {})
            confidence = prediction.get('confidence', 0)
            direction = prediction.get('direction', 'HOLD').upper()
            
            if not ticker or direction == 'HOLD':
                return None
            
            # Get market data
            market_data = await self._get_market_data(ticker)
            current_price = market_data.get('current_price', 100)
            
            # Calculate entry, stop, target based on prediction
            if direction == 'BUY':
                entry_price = current_price * 1.001  # Slight above market
                stop_loss = current_price * 0.98  # 2% stop
                target_price = current_price * 1.03  # 3% target
            else:  # SELL
                entry_price = current_price * 0.999  # Slight below market
                stop_loss = current_price * 1.02  # 2% stop
                target_price = current_price * 0.97  # 3% target
            
            # Create signal
            db = SessionLocal()
            try:
                signal = Signal(
                    ticker=ticker,
                    exchange='WEBHOOK',
                    signal_type=direction,
                    confidence=min(confidence, 100),
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    target_price=target_price,
                    news_source=f"Webhook prediction: {webhook_data.get('source', 'Unknown')}",
                    reasoning=webhook_data.get('reasoning', 'Webhook-generated signal'),
                    materiality_score=8,  # Default high for webhook signals
                    status=SignalStatus.ANALYZED,
                    expires_at=datetime.now() + timedelta(hours=1)
                )
                
                db.add(signal)
                db.commit()
                
                logger.info(f"Generated signal from webhook for {ticker}: {direction} @ {confidence}%")
                return signal
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error generating signal from webhook: {str(e)}")
            return None