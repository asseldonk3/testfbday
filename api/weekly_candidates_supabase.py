from http.server import BaseHTTPRequestHandler
import json
import os
from datetime import datetime
import random
import requests

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Get weekly candidates and save to Supabase"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Get Supabase credentials from environment
        supabase_url = os.environ.get('SUPABASE_URL', '')
        supabase_key = os.environ.get('SUPABASE_ANON_KEY', '')
        
        # Sample stock universe with real trading favorites
        stock_universe = [
            # Mega caps (high liquidity)
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
            # Popular day trading stocks
            'SPY', 'QQQ', 'AMD', 'SOFI', 'PLTR', 'NIO', 'RIVN',
            # High volatility stocks
            'COIN', 'MARA', 'RIOT', 'GME', 'AMC', 'BBBY',
            # Banking/Finance
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C',
            # Energy sector
            'XOM', 'CVX', 'OXY', 'SLB',
            # Biotech (news-driven)
            'MRNA', 'BNTX', 'PFE', 'JNJ'
        ]
        
        # Select 10-25 stocks with scoring
        num_stocks = random.randint(10, 25)
        selected_stocks = random.sample(stock_universe, min(num_stocks, len(stock_universe)))
        
        # Create candidates with analysis
        candidates = []
        week = datetime.now().strftime('%Y-W%U')
        
        for stock in selected_stocks:
            candidate = {
                'symbol': stock,
                'score': random.randint(70, 95),
                'reason': self._generate_reason(stock),
                'week': week
            }
            candidates.append(candidate)
        
        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # Save to Supabase if configured
        saved_to_db = False
        if supabase_url and supabase_key:
            saved_to_db = self._save_to_supabase(
                supabase_url, supabase_key, candidates, week
            )
        
        # Return response
        response = {
            'success': True,
            'message': f'Selected {len(candidates)} stocks for week {week}',
            'candidates': candidates,
            'total_selected': len(candidates),
            'week': week,
            'timestamp': datetime.now().isoformat(),
            'saved_to_database': saved_to_db
        }
        
        self.wfile.write(json.dumps(response).encode())
        return
    
    def _generate_reason(self, symbol):
        """Generate realistic selection reasons"""
        reasons = {
            'NVDA': 'AI sector momentum, high options volume',
            'TSLA': 'EV catalyst events, high volatility',
            'SPY': 'Market index, excellent liquidity',
            'AMD': 'Semiconductor sector rotation',
            'COIN': 'Crypto correlation play',
            'GME': 'Retail interest, squeeze potential',
            'AAPL': 'Tech giant, product launches',
            'SOFI': 'Fintech growth, high retail interest',
            'NIO': 'China EV play, news catalyst',
            'META': 'Social media earnings play'
        }
        
        return reasons.get(symbol, f"Selected for {random.choice(['high volume', 'news catalyst', 'technical setup', 'momentum play', 'sector rotation'])}")
    
    def _save_to_supabase(self, url, key, candidates, week):
        """Save candidates to Supabase database"""
        try:
            # First, deactivate old watchlist
            deactivate_url = f"{url}/rest/v1/watchlist"
            headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=minimal'
            }
            
            # Update old entries to inactive
            requests.patch(
                deactivate_url,
                headers=headers,
                params={'is_active': 'eq.true'},
                json={'is_active': False}
            )
            
            # Insert new watchlist
            insert_data = []
            for candidate in candidates:
                insert_data.append({
                    'week': week,
                    'symbol': candidate['symbol'],
                    'score': candidate['score'],
                    'reason': candidate['reason'],
                    'is_active': True
                })
            
            response = requests.post(
                deactivate_url,
                headers=headers,
                json=insert_data
            )
            
            return response.status_code in [200, 201, 204]
        except Exception as e:
            print(f"Supabase error: {e}")
            return False
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return