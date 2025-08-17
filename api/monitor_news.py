"""
Vercel Serverless Function - News Monitoring
Monitors news for selected candidates
"""
import os
import json
from datetime import datetime
import requests

def handler(request):
    """
    Monitor news for watchlist stocks
    Can be triggered by Vercel Cron or external services
    """
    
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'application/json'
    }
    
    # Get watchlist from request or storage
    body = json.loads(request.body) if request.body else {}
    watchlist = body.get('watchlist', ['AAPL', 'TSLA', 'NVDA'])  # Default symbols
    
    # Marketaux API for news
    api_key = os.environ.get('MARKETAUX_API_KEY')
    
    all_news = []
    for symbol in watchlist:
        try:
            # Fetch news from Marketaux
            url = f"https://api.marketaux.com/v1/news/all"
            params = {
                'symbols': symbol,
                'filter_entities': 'true',
                'limit': 3,
                'api_token': api_key
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                for article in data.get('data', []):
                    all_news.append({
                        'symbol': symbol,
                        'title': article.get('title'),
                        'description': article.get('description'),
                        'url': article.get('url'),
                        'published_at': article.get('published_at'),
                        'sentiment': analyze_sentiment(article.get('title', '') + ' ' + article.get('description', ''))
                    })
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
    
    # Filter for high-impact news
    high_impact = [n for n in all_news if n['sentiment']['score'] > 0.7]
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'total_news': len(all_news),
            'high_impact_count': len(high_impact),
            'news': all_news[:10],  # Return top 10
            'alerts': high_impact
        })
    }

def analyze_sentiment(text):
    """Simple sentiment analysis (in production, use AI)"""
    positive_words = ['surge', 'gain', 'profit', 'beat', 'upgrade', 'bullish', 'record', 'breakthrough']
    negative_words = ['loss', 'decline', 'fall', 'miss', 'downgrade', 'bearish', 'crash', 'concern']
    
    text_lower = text.lower()
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)
    
    score = (pos_count - neg_count) / max(1, pos_count + neg_count)
    
    return {
        'score': abs(score),
        'direction': 'bullish' if score > 0 else 'bearish' if score < 0 else 'neutral'
    }