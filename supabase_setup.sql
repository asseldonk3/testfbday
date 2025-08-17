-- Supabase Database Setup for Trading System
-- Run this in Supabase SQL Editor after creating your project

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Weekly Watchlist Table
CREATE TABLE IF NOT EXISTS watchlist (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    week VARCHAR(10) NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    score INTEGER DEFAULT 0,
    reason TEXT,
    selected_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    UNIQUE(week, symbol)
);

-- Trading Signals Table
CREATE TABLE IF NOT EXISTS signals (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    signal_type VARCHAR(20) NOT NULL, -- 'BUY', 'SELL', 'HOLD'
    confidence DECIMAL(3,2), -- 0.00 to 1.00
    reason TEXT,
    news_source TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    executed BOOLEAN DEFAULT false
);

-- Trades Table
CREATE TABLE IF NOT EXISTS trades (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    signal_id UUID REFERENCES signals(id),
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(10) NOT NULL, -- 'BUY', 'SELL'
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2),
    total_value DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'PENDING', -- 'PENDING', 'EXECUTED', 'CANCELLED'
    executed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- News Monitoring Table
CREATE TABLE IF NOT EXISTS news_items (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,
    sentiment VARCHAR(20), -- 'BULLISH', 'BEARISH', 'NEUTRAL'
    impact_score DECIMAL(3,2), -- 0.00 to 1.00
    published_at TIMESTAMP,
    processed_at TIMESTAMP DEFAULT NOW()
);

-- Portfolio Performance Table
CREATE TABLE IF NOT EXISTS portfolio (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    date DATE NOT NULL,
    total_value DECIMAL(10,2),
    daily_pnl DECIMAL(10,2),
    daily_pnl_percent DECIMAL(5,2),
    win_rate DECIMAL(5,2),
    total_trades INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date)
);

-- Create indexes for better performance
CREATE INDEX idx_watchlist_week ON watchlist(week);
CREATE INDEX idx_watchlist_symbol ON watchlist(symbol);
CREATE INDEX idx_signals_symbol ON signals(symbol);
CREATE INDEX idx_signals_created ON signals(created_at);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_news_symbol ON news_items(symbol);
CREATE INDEX idx_news_published ON news_items(published_at);

-- Create views for easy querying
CREATE OR REPLACE VIEW active_watchlist AS
SELECT * FROM watchlist 
WHERE is_active = true 
AND week = TO_CHAR(NOW(), 'YYYY-"W"IW');

CREATE OR REPLACE VIEW recent_signals AS
SELECT * FROM signals 
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

CREATE OR REPLACE VIEW today_trades AS
SELECT * FROM trades 
WHERE DATE(created_at) = CURRENT_DATE
ORDER BY created_at DESC;

-- Row Level Security (RLS) - Optional but recommended
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio ENABLE ROW LEVEL SECURITY;

-- Create a simple RLS policy (update based on your auth needs)
CREATE POLICY "Enable all access for now" ON watchlist FOR ALL USING (true);
CREATE POLICY "Enable all access for now" ON signals FOR ALL USING (true);
CREATE POLICY "Enable all access for now" ON trades FOR ALL USING (true);
CREATE POLICY "Enable all access for now" ON news_items FOR ALL USING (true);
CREATE POLICY "Enable all access for now" ON portfolio FOR ALL USING (true);