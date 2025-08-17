-- Initialize database with default portfolio
INSERT INTO portfolio (
    current_balance,
    initial_balance,
    total_pnl,
    total_pnl_percentage,
    open_positions,
    total_exposure,
    total_trades,
    winning_trades,
    losing_trades,
    win_rate,
    max_drawdown,
    current_drawdown
) VALUES (
    5000.0,  -- Starting with €5000
    5000.0,
    0.0,
    0.0,
    0,
    0.0,
    0,
    0,
    0,
    0.0,
    0.0,
    0.0
) ON CONFLICT DO NOTHING;