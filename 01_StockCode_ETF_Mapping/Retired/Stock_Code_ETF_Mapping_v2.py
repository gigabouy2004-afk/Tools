import pandas as pd
import numpy as np

def run_backtest(ticker_symbol="SPY"):
    """
    A fully automated, self-contained backtesting framework that generates 
    synthetic historical data, implements a Simple Moving Average (SMA) 
    crossover strategy, simulates execution, and calculates performance metrics.
    """
    # 1. Generate Historical Data (Simulated daily data for 5 years)
    np.random.seed(42)
    date_range = pd.date_range(start="2021-01-01", periods=1250, freq="B")
    daily_returns = np.random.normal(0.0005, 0.012, len(date_range))
    price_series = 100 * np.exp(np.cumsum(daily_returns))
    
    df = pd.DataFrame(index=date_range)
    df['Close'] = price_series
    df['Asset_Returns'] = df['Close'].pct_change()

    # 2. Define Strategy Rules (SMA Crossover Strategy)
    short_window = 50
    long_window = 200
    
    df['SMA_Short'] = df['Close'].rolling(window=short_window).mean()
    df['SMA_Long'] = df['Close'].rolling(window=long_window).mean()
    
    # Generate signals: 1 when short SMA > long SMA (Buy), else 0 (Cash/Out)
    df['Signal'] = 0.0
    df.loc[df['SMA_Short'] > df['SMA_Long'], 'Signal'] = 1.0
    
    # Shift signals by 1 day to prevent look-ahead bias (execute on next open/close)
    df['Position'] = df['Signal'].shift(1)

    # 3. Execution Simulation
    df['Strategy_Returns'] = df['Asset_Returns'] * df['Position']
    
    # Calculate Cumulative Returns
    df['Cum_Asset_Returns'] = (1 + df['Asset_Returns'].fillna(0)).cumprod() - 1
    df['Cum_Strategy_Returns'] = (1 + df['Strategy_Returns'].fillna(0)).cumprod() - 1

    # 4. Compute Performance Metrics
    total_strategy_return = df['Cum_Strategy_Returns'].iloc[-1]
    total_asset_return = df['Cum_Asset_Returns'].iloc[-1]
    
    # Annualized Sharpe Ratio (assuming risk-free rate = 0)
    ann_factor = 252
    strat_std = df['Strategy_Returns'].std()
    sharpe_ratio = (df['Strategy_Returns'].mean() / strat_std) * np.sqrt(ann_factor) if strat_std != 0 else 0
    
    # Maximum Drawdown calculation
    cum_roll_max = (df['Cum_Strategy_Returns'] + 1).cummax()
    drawdown = ((df['Cum_Strategy_Returns'] + 1) / cum_roll_max) - 1
    max_drawdown = drawdown.min()

    # Print summary metrics directly to the console
    print(f"=== BACKTEST PERFORMANCE REPORT: {ticker_symbol} ===")
    print(f"Strategy Total Return: {total_strategy_return * 100:.2f}%")
    print(f"Benchmark Asset Return: {total_asset_return * 100:.2f}%")
    print(f"Annualized Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Maximum Peak-to-Trough Drawdown: {max_drawdown * 100:.2f}%")
    print("==================================================")
    
    return df

if __name__ == "__main__":
    backtest_results = run_backtest()