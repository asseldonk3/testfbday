from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime
import random

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Sample stock universe
        stock_universe = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
            'JPM', 'V', 'JNJ', 'WMT', 'PG', 'MA', 'HD', 'DIS', 'BAC',
            'NFLX', 'CRM', 'PFE', 'ABBV', 'KO', 'NKE', 'MRK', 'PEP',
            'COST', 'CVX', 'WFC', 'MS', 'UPS', 'INTC', 'AMD', 'QCOM'
        ]
        
        # Select 10-25 random stocks
        num_stocks = random.randint(10, 25)
        selected_stocks = random.sample(stock_universe, min(num_stocks, len(stock_universe)))
        
        # Create response with scores
        candidates = []
        for stock in selected_stocks:
            candidates.append({
                'symbol': stock,
                'score': random.randint(70, 95),
                'reason': f"Selected for {random.choice(['high volume', 'news catalyst', 'momentum', 'volatility'])}"
            })
        
        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        response = {
            'success': True,
            'message': f'Selected {len(candidates)} stocks for weekly monitoring',
            'candidates': candidates,
            'total_selected': len(candidates),
            'week': datetime.now().strftime('%Y-W%U'),
            'timestamp': datetime.now().isoformat()
        }
        
        self.wfile.write(json.dumps(response).encode())
        return
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return