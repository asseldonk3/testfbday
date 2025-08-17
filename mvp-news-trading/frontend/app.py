from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import requests
import json
from datetime import datetime
import os
from threading import Thread
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
socketio = SocketIO(app, cors_allowed_origins="*")

# Backend API configuration
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000')

# Pipeline stages for visualization
PIPELINE_STAGES = [
    {'id': 'news', 'name': 'News Sources', 'icon': '📰', 'status': 'idle'},
    {'id': 'scout', 'name': 'Scout Agent', 'icon': '🔍', 'status': 'idle'},
    {'id': 'analyst', 'name': 'Analyst Agent', 'icon': '📊', 'status': 'idle'},
    {'id': 'risk', 'name': 'Risk Manager', 'icon': '⚖️', 'status': 'idle'},
    {'id': 'executor', 'name': 'Executor', 'icon': '🎯', 'status': 'idle'},
    {'id': 'alpaca', 'name': 'Alpaca', 'icon': '🦙', 'status': 'idle'}
]

# Cache for latest data
cache = {
    'pipeline_status': PIPELINE_STAGES.copy(),
    'recent_trades': [],
    'active_signals': [],
    'portfolio_stats': {
        'total_value': 100000,
        'daily_pnl': 0,
        'daily_pnl_percent': 0,
        'open_positions': 0,
        'today_trades': 0,
        'win_rate': 0
    },
    'webhook_logs': []
}

@app.route('/')
def index():
    """Main dashboard with pipeline visualization"""
    return render_template('dashboard.html')

@app.route('/trades')
def trades():
    """Trade history page"""
    return render_template('trades.html')

@app.route('/signals')
def signals():
    """Active signals page"""
    return render_template('signals.html')

@app.route('/watchlist')
def watchlist():
    """Watchlist management page"""
    return render_template('watchlist.html')

@app.route('/settings')
def settings():
    """Settings and configuration page"""
    return render_template('settings.html')

# Pipeline stage detail pages
@app.route('/pipeline/watchlist')
def pipeline_watchlist():
    """Watchlist stage details"""
    return render_template('watchlist.html')  # Reuse existing watchlist page

@app.route('/pipeline/news')
def pipeline_news():
    """News sources stage details"""
    return render_template('pipeline/news.html')

@app.route('/pipeline/scout')
def pipeline_scout():
    """Scout agent stage details"""
    # For now, redirect to news page (they're related)
    return render_template('pipeline/news.html')

@app.route('/pipeline/analyst')
def pipeline_analyst():
    """Analyst agent stage details"""
    return render_template('pipeline/analyst.html')

@app.route('/pipeline/risk')
def pipeline_risk():
    """Risk manager stage details"""
    # Create a simple page for now
    return render_template('pipeline/analyst.html')  # Temporary

@app.route('/pipeline/executor')
def pipeline_executor():
    """Executor stage details"""
    return render_template('trades.html')  # Show trades page

@app.route('/pipeline/alpaca')
def pipeline_alpaca():
    """Alpaca integration details"""
    return render_template('trades.html')  # Show trades page

# API Routes
@app.route('/api/pipeline-status')
def get_pipeline_status():
    """Get current pipeline stage statuses"""
    return jsonify(cache['pipeline_status'])

@app.route('/api/portfolio-stats')
def get_portfolio_stats():
    """Get portfolio statistics"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            cache['portfolio_stats'].update({
                'total_value': data.get('portfolio', {}).get('equity', 100000),
                'daily_pnl': data.get('portfolio', {}).get('daily_pnl', 0),
                'today_trades': len(data.get('todays_trades', [])),
                'open_positions': len(data.get('open_positions', []))
            })
    except:
        pass
    return jsonify(cache['portfolio_stats'])

@app.route('/api/recent-trades')
def get_recent_trades():
    """Get recent trades"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/trades", timeout=5)
        if response.status_code == 200:
            cache['recent_trades'] = response.json()[:10]  # Last 10 trades
    except:
        pass
    return jsonify(cache['recent_trades'])

@app.route('/api/active-signals')
def get_active_signals():
    """Get active trading signals"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/signals", timeout=5)
        if response.status_code == 200:
            signals = response.json()
            cache['active_signals'] = [s for s in signals if s.get('status') in ['pending', 'analyzed', 'approved']]
    except:
        pass
    return jsonify(cache['active_signals'])

@app.route('/api/webhook-logs')
def get_webhook_logs():
    """Get recent webhook events"""
    try:
        response = requests.get(f"{BACKEND_URL}/webhook/logs", timeout=5)
        if response.status_code == 200:
            cache['webhook_logs'] = response.json()[:20]  # Last 20 events
    except:
        pass
    return jsonify(cache['webhook_logs'])

@app.route('/api/test-webhook', methods=['POST'])
def test_webhook():
    """Send test webhook to backend"""
    data = request.json
    try:
        response = requests.post(
            f"{BACKEND_URL}/webhook/prediction",
            json=data,
            timeout=10
        )
        return jsonify({
            'success': response.status_code == 200,
            'response': response.json() if response.status_code == 200 else response.text
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Watchlist API proxy routes
@app.route('/api/watchlist/current')
def get_current_watchlist():
    """Get current watchlist from backend"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/watchlist/current", timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch watchlist'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlist/universe')
def get_stock_universe():
    """Get stock universe from backend"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/watchlist/universe", timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch universe'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlist/update', methods=['POST'])
def update_watchlist():
    """Update watchlist in backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/watchlist/update",
            json=request.json,
            timeout=10
        )
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to update watchlist'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/watchlist/suggestions')
def get_watchlist_suggestions():
    """Get watchlist suggestions from backend"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/watchlist/suggestions", timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to fetch suggestions'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'data': 'Connected to trading dashboard'})
    # Send initial data
    emit('pipeline_update', cache['pipeline_status'])
    emit('portfolio_update', cache['portfolio_stats'])

@socketio.on('request_update')
def handle_update_request(data):
    """Handle update requests from client"""
    update_type = data.get('type', 'all')
    if update_type == 'pipeline':
        emit('pipeline_update', cache['pipeline_status'])
    elif update_type == 'portfolio':
        emit('portfolio_update', cache['portfolio_stats'])
    elif update_type == 'trades':
        emit('trades_update', cache['recent_trades'])
    else:
        # Send all updates
        emit('pipeline_update', cache['pipeline_status'])
        emit('portfolio_update', cache['portfolio_stats'])
        emit('trades_update', cache['recent_trades'])

def update_pipeline_stage(stage_id, status, message=None):
    """Update pipeline stage status and notify clients"""
    for stage in cache['pipeline_status']:
        if stage['id'] == stage_id:
            stage['status'] = status
            stage['last_update'] = datetime.now().isoformat()
            if message:
                stage['message'] = message
            break
    
    # Broadcast update to all connected clients
    socketio.emit('pipeline_update', cache['pipeline_status'])

def background_updater():
    """Background thread to fetch updates from backend"""
    while True:
        try:
            # Fetch portfolio stats
            response = requests.get(f"{BACKEND_URL}/api/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                old_stats = cache['portfolio_stats'].copy()
                cache['portfolio_stats'].update({
                    'total_value': data.get('portfolio', {}).get('equity', 100000),
                    'daily_pnl': data.get('portfolio', {}).get('daily_pnl', 0),
                    'today_trades': len(data.get('todays_trades', [])),
                    'open_positions': len(data.get('open_positions', []))
                })
                
                # Notify if changed
                if old_stats != cache['portfolio_stats']:
                    socketio.emit('portfolio_update', cache['portfolio_stats'])
            
            # Check for new trades
            response = requests.get(f"{BACKEND_URL}/api/trades", timeout=5)
            if response.status_code == 200:
                new_trades = response.json()[:10]
                if new_trades != cache['recent_trades']:
                    cache['recent_trades'] = new_trades
                    socketio.emit('trades_update', cache['recent_trades'])
                    
        except Exception as e:
            print(f"Background updater error: {e}")
        
        time.sleep(5)  # Update every 5 seconds

# Start background updater thread
updater_thread = Thread(target=background_updater, daemon=True)
updater_thread.start()

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)