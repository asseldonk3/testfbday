# CLAUDE.md - Trading Dashboard Frontend

This file provides guidance to Claude Code when working with the trading dashboard frontend.

## Project Purpose

This frontend provides a comprehensive overview dashboard for monitoring all trading activities across different strategies. It serves as the central control panel for:
- Real-time trading performance monitoring
- Financial P&L tracking (wins/losses)
- Historical trade analysis
- Strategy performance comparison
- Risk exposure visualization

## Key Features

### Financial Overview
- **Daily P&L**: Real-time profit/loss tracking
- **Cumulative Performance**: Total wins vs losses
- **Win Rate**: Success percentage by strategy
- **Drawdown Tracking**: Maximum loss periods
- **ROI Metrics**: Return on invested capital

### Trading Activity Monitor
- **Active Positions**: Current open trades
- **Recent Executions**: Last 50 trades with outcomes
- **Signal Queue**: Pending signals awaiting execution
- **Strategy Performance**: Breakdown by strategy type
  - News-Based Trading results
  - Gap and Go performance
  - Momentum Scalping metrics

### Risk Dashboard
- **Exposure Meter**: Current risk vs limits
- **Daily Trade Count**: Trades used vs maximum
- **Loss Tracking**: Consecutive losses alert
- **Position Sizing**: Actual vs recommended sizes

## Technology Stack

```
Frontend Framework: React/Next.js or Streamlit
UI Components: Bootstrap or Tailwind CSS
Charts: Chart.js or Plotly
Real-time Updates: WebSockets
State Management: Redux or Context API
```

## Development Commands

```bash
# Install dependencies
npm install  # or yarn install

# Development server
npm run dev  # runs on http://localhost:3000

# Build for production
npm run build

# Run tests
npm test

# Lint code
npm run lint
```

## Dashboard Pages

### 1. Overview (Home)
- Today's P&L with color coding (green/red)
- Active positions with unrealized P&L
- Quick stats: Win rate, total trades, best/worst
- Strategy allocation pie chart

### 2. Performance Analytics
- Cumulative P&L chart over time
- Win/loss distribution histogram
- Strategy comparison table
- Hourly performance heatmap

### 3. Trade History
- Sortable/filterable trade table
- Columns: Time, Symbol, Strategy, Entry, Exit, P&L, Duration
- Export to CSV functionality
- Trade replay visualization

### 4. Risk Management
- Current exposure gauges
- Risk parameter settings
- Alert configuration
- Emergency stop controls

### 5. Live Feed
- Real-time news signals
- Social momentum indicators
- Webhook event stream
- System status monitors

## Data Sources

The frontend connects to multiple backend endpoints:
```javascript
// Backend APIs
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000'

// Endpoints
GET  /api/dashboard/summary     // Overview stats
GET  /api/trades/history        // Historical trades
GET  /api/positions/active      // Current positions
GET  /api/performance/daily     // Daily P&L data
WS   /ws/live-feed             // Real-time updates
```

## Key Metrics to Display

### Financial Metrics
- **Total P&L**: Lifetime profit/loss
- **Today's P&L**: Current day performance
- **Week/Month P&L**: Period comparisons
- **Average Trade**: Mean profit per trade
- **Best Trade**: Largest single win
- **Worst Trade**: Largest single loss
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough

### Operational Metrics
- **Total Trades**: Count across all strategies
- **Win Rate**: Winning trades percentage
- **Avg Hold Time**: Mean position duration
- **Trade Frequency**: Trades per day average
- **Strategy Distribution**: Trades by strategy type

## Color Coding Standards

```css
/* Profit/Loss Colors */
.profit { color: #10B981; }  /* Green */
.loss { color: #EF4444; }    /* Red */
.neutral { color: #6B7280; } /* Gray */

/* Status Indicators */
.active { background: #3B82F6; }  /* Blue */
.pending { background: #F59E0B; } /* Amber */
.closed { background: #6B7280; }  /* Gray */

/* Risk Levels */
.low-risk { background: #10B981; }    /* Green */
.medium-risk { background: #F59E0B; } /* Amber */
.high-risk { background: #EF4444; }   /* Red */
```

## Performance Requirements

- Page load time: <2 seconds
- Data refresh rate: 1-5 seconds for live data
- Chart rendering: <500ms
- WebSocket latency: <100ms
- Mobile responsive design

## Environment Variables

```env
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
REACT_APP_REFRESH_INTERVAL=5000
REACT_APP_CHART_POINTS=100
REACT_APP_TIMEZONE=America/New_York
```