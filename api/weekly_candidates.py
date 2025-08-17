"""
Vercel Function for selecting weekly trading candidates
Trigger this endpoint manually or via a cron service
"""
import os
import json
from datetime import datetime
import random

def handler(request):
    """
    Vercel function to select 10-25 weekly trading candidates
    Access via: https://your-app.vercel.app/api/weekly_candidates
    """
    
    """
    Handle CORS and process request
    """
    # Handle CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Content-Type': 'application/json'
    }
    
    # Handle preflight requests
    if request.method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # Sample stock universe (in production, this would come from market data)
        stock_universe = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B',
            'JPM', 'V', 'JNJ', 'WMT', 'PG', 'MA', 'HD', 'DIS', 'BAC', 'ADBE',
            'NFLX', 'CRM', 'PFE', 'ABBV', 'KO', 'NKE', 'MRK', 'PEP', 'TMO',
            'COST', 'CVX', 'WFC', 'MS', 'UPS', 'INTC', 'AMD', 'QCOM', 'TXN'
        ]
        
        # Selection criteria (simplified for demo)
        criteria = {
            'min_volume': 1000000,
            'min_price': 10,
            'max_price': 500,
            'sectors': ['Technology', 'Healthcare', 'Finance', 'Consumer']
        }
        
        # Select 10-25 random stocks (in production, use AI analysis)
        num_stocks = random.randint(10, 25)
        selected_stocks = random.sample(stock_universe, min(num_stocks, len(stock_universe)))
        
        # Create watchlist
        watchlist = {
            'week': datetime.now().strftime('%Y-W%U'),
            'created_at': datetime.now().isoformat(),
            'stocks': selected_stocks,
            'count': len(selected_stocks),
            'criteria': criteria,
            'status': 'active'
        }
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'message': f'Selected {len(selected_stocks)} stocks for weekly monitoring',
                'watchlist': watchlist
            })
        }
    except Exception as e:
        # Return error response
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }