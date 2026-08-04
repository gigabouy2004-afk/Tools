#!/usr/bin/env python
"""
HTML output formatter for stock screener results.
Generates a web-ready dashboard with sortable tables.
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Any

from column_renderer import REPORT_COLUMNS, render_headers, render_row

CANDIDATE_STATE_ORDER = [
    "PRE_BULL_CROSSOVER",
    "PRE_BEAR_CROSSOVER",
    "BULL_EXTENDED",
    "BEAR_EXTENDED",
    "SETUP_CANDIDATE",
    "BULLISH_DIVERGENCE",
    "BEARISH_DIVERGENCE",
    "STATUS_QUO",
]

def _format_money(value: Any) -> str:
    if pd.isna(value):
        return "N/A"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if abs(number) >= 1_000_000_000:
        return f"${number / 1_000_000_000:.2f}B"
    if abs(number) >= 1_000_000:
        return f"${number / 1_000_000:.2f}M"
    return f"${number:,.2f}"

def _format_number(value: Any) -> str:
    if pd.isna(value):
        return "N/A"
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)

def _format_price(value: Any) -> str:
    if pd.isna(value):
        return "N/A"
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)

def _format_pct(value: Any) -> str:
    if pd.isna(value):
        return "N/A"
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return str(value)

def _format_decimal(value: Any, digits: int = 1) -> str:
    if pd.isna(value):
        return "N/A"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)

def _sort_by_state_score(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    sorted_df = df.copy()
    state_rank = {state: index for index, state in enumerate(CANDIDATE_STATE_ORDER)}
    state_series = sorted_df["CandidateState"] if "CandidateState" in sorted_df.columns else pd.Series([""] * len(sorted_df), index=sorted_df.index)
    score_series = sorted_df["WeightedScore"] if "WeightedScore" in sorted_df.columns else pd.Series([0] * len(sorted_df), index=sorted_df.index)
    symbol_series = sorted_df["Symbol"] if "Symbol" in sorted_df.columns else pd.Series([""] * len(sorted_df), index=sorted_df.index)
    sorted_df["_state_rank"] = state_series.map(state_rank).fillna(len(state_rank))
    sorted_df["_score_sort"] = pd.to_numeric(score_series, errors="coerce").fillna(0)
    sorted_df["_symbol_sort"] = symbol_series.astype(str)
    sorted_df = sorted_df.sort_values(
        by=["_state_rank", "_score_sort", "_symbol_sort"],
        ascending=[True, False, True],
        kind="mergesort",
    )
    return sorted_df.drop(columns=["_state_rank", "_score_sort", "_symbol_sort"])

def generate_html_report(rows: List[Dict[str, Any]], output_file: str, filter_conditions: str = "") -> str:
    """
    Generate an HTML report from screener results.
    
    Args:
        rows: list of result dictionaries
        output_file: path to save HTML file
    
    Returns:
        path to generated HTML file
    """
    df = pd.DataFrame(rows)
    if 'FilterPassed' in df.columns:
        df = df[df['FilterPassed'] == True]
    if 'CandidateState' in df.columns:
        df = df[df['CandidateState'] != 'NO_CANDIDATE']
    df = _sort_by_state_score(df)
    if not filter_conditions and 'AppliedFilters' in df.columns and len(df) > 0:
        filter_conditions = str(df.iloc[0].get('AppliedFilters', ''))
    
    # Group by CandidateState for summary
    state_summary = df['CandidateState'].value_counts().to_dict() if 'CandidateState' in df.columns else {}
    
    # Generate HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Screener Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            overflow: hidden;
        }}
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        header p {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
        }}
        .summary-card {{
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }}
        .summary-card h3 {{
            font-size: 24px;
            color: #667eea;
            margin-bottom: 5px;
        }}
        .summary-card p {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            font-size: 20px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
            color: #333;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        thead {{
            background: #f8f9fa;
            border-bottom: 2px solid #e0e0e0;
        }}
        th {{
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            font-size: 13px;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{
            background: #e8e9fa;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 13px;
        }}
        tbody tr:hover {{
            background: #f8f9fa;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            white-space: nowrap;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        .badge-info {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        .state-BULL_EXTENDED {{
            background: #ffe6e6;
            color: #c00;
        }}
        .state-BEAR_EXTENDED {{
            background: #ffd8d8;
            color: #8f1d1d;
        }}
        .state-PRE_BULL_CROSSOVER {{
            background: #e6ffe6;
            color: #060;
        }}
        .state-PRE_BEAR_CROSSOVER {{
            background: #ffe6f0;
            color: #903060;
        }}
        .state-SETUP_CANDIDATE {{
            background: #e6f0ff;
            color: #0060c0;
        }}
        .state-BEARISH_DIVERGENCE {{
            background: #fff0e6;
            color: #c06000;
        }}
        .state-BULLISH_DIVERGENCE {{
            background: #f0e6ff;
            color: #600c8f;
        }}
        .state-STATUS_QUO {{
            background: #e9ecef;
            color: #495057;
        }}
        .macd-bullish {{
            color: #0a8200;
            font-weight: 600;
        }}
        .macd-bearish {{
            color: #c00000;
            font-weight: 600;
        }}
        .rsi-high {{
            color: #c00000;
        }}
        .rsi-low {{
            color: #0a8200;
        }}
        footer {{
            background: #f8f9fa;
            padding: 20px 30px;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Stock Screener Results</h1>
            <p>MACD-based screening for Pre-Bull, Pre-Bear, and Bull Extended states</p>
            <p>Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>
        
        <div class="summary">
            <div class="summary-card">
                <h3>{len(df)}</h3>
                <p>Matched Symbols</p>
            </div>
"""
    
    # Add state summary
    for state, count in sorted(state_summary.items(), key=lambda x: x[1], reverse=True)[:3]:
        html_content += f"""
            <div class="summary-card">
                <h3>{count}</h3>
                <p>{state}</p>
            </div>
"""
    
    html_content += """
        </div>
        
        <div class="content">
"""
    html_content += f"""
            <div class="section">
                <h2>Filter Conditions</h2>
                <p>{filter_conditions or 'No explicit filters supplied; showing engine candidates only.'}</p>
            </div>
"""
    
    # Matched Results Section
    html_content += f"""
            <div class="section">
                <h2>Matched Results</h2>
                <table>
                    <thead>
                        <tr>{render_headers(REPORT_COLUMNS)}</tr>
                    </thead>
                    <tbody>
"""
    
    for _, row in df.iterrows():
        html_content += "                        " + render_row(row.to_dict(), REPORT_COLUMNS, use_display_format=True) + "\n"
    
    html_content += """
                    </tbody>
                </table>
            </div>
"""
    
    # Bull Extended candidates
    bull_extended = _sort_by_state_score(df[df.get('CandidateState') == 'BULL_EXTENDED']) if 'CandidateState' in df.columns else pd.DataFrame()
    if len(bull_extended) > 0:
        html_content += """
            <div class="section">
                <h2>🚀 Bull Extended (Overbought/Extended)</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>CompanyName</th>
                            <th>Price</th>
                            <th>Weighted Score</th>
                            <th>Lifetime High</th>
                            <th>To Lifetime</th>
                            <th>EMA52 High</th>
                            <th>To EMA52H</th>
                            <th>Ceiling Pattern</th>
                            <th>RSI 1D</th>
                            <th>MACD Base 1D</th>
                            <th>Base Regime</th>
                            <th>Bollinger %B</th>
                            <th>Position</th>
                            <th>Reason</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for _, row in bull_extended.iterrows():
            html_content += f"""
                        <tr>
                            <td><strong>{row['Symbol']}</strong></td>
                            <td>{row.get('CompanyName', 'N/A')}</td>
                            <td>{_format_price(row.get('LatestPrice'))}</td>
                            <td>{row.get('WeightedScore', 'N/A')}</td>
                            <td>{_format_price(row.get('LifetimeHigh'))}</td>
                            <td>{_format_pct(row.get('DistanceToLifetimeHighPct'))}</td>
                            <td>{_format_price(row.get('EMA52High'))}</td>
                            <td>{_format_pct(row.get('DistanceToEMA52HighPct'))}</td>
                            <td>{row.get('CeilingPattern', 'N/A')}</td>
                            <td class="rsi-high">{_format_decimal(row.get('RSI_1D'))}</td>
                            <td>{row.get('MACD_Baseline_1D_State', row.get('MACD_1D_State', 'N/A'))}</td>
                            <td>{row.get('MACD_Baseline_1D_Regime', 'N/A')}</td>
                            <td>{_format_pct(row.get('Bollinger_PctB'))}</td>
                            <td>{row.get('Bollinger_Position', 'N/A')}</td>
                            <td>{row.get('CandidateReason', 'N/A')}</td>
                        </tr>
"""
        html_content += """
                    </tbody>
                </table>
            </div>
"""
    
    # Crossover candidates
    crossovers = _sort_by_state_score(df[df['CandidateState'].isin(['PRE_BULL_CROSSOVER', 'PRE_BEAR_CROSSOVER'])]) if 'CandidateState' in df.columns else pd.DataFrame()
    if len(crossovers) > 0:
        html_content += """
            <div class="section">
                <h2>⚡ Crossover Candidates</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>CompanyName</th>
                            <th>State</th>
                            <th>Price</th>
                            <th>Weighted Score</th>
                            <th>Lifetime High</th>
                            <th>To Lifetime</th>
                            <th>EMA52 High</th>
                            <th>To EMA52H</th>
                            <th>Ceiling Pattern</th>
                            <th>Fast MACD 1D</th>
                            <th>Fast MACD 4H</th>
                            <th>Fast MACD 1H</th>
                            <th>Base Regime</th>
                            <th>1H Event</th>
                            <th>MACD Flow</th>
                            <th>RSI</th>
                            <th>Reason</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        for _, row in crossovers.iterrows():
            html_content += f"""
                        <tr>
                            <td><strong>{row['Symbol']}</strong></td>
                            <td>{row.get('CompanyName', 'N/A')}</td>
                            <td><span class="badge state-{row['CandidateState']}">{row['CandidateState']}</span></td>
                            <td>{_format_price(row.get('LatestPrice'))}</td>
                            <td>{row.get('WeightedScore', 'N/A')}</td>
                            <td>{_format_price(row.get('LifetimeHigh'))}</td>
                            <td>{_format_pct(row.get('DistanceToLifetimeHighPct'))}</td>
                            <td>{_format_price(row.get('EMA52High'))}</td>
                            <td>{_format_pct(row.get('DistanceToEMA52HighPct'))}</td>
                            <td>{row.get('CeilingPattern', 'N/A')}</td>
                            <td>{row.get('MACD_Fast_1D_State', row.get('MACD_1D_State', 'N/A'))}</td>
                            <td>{row.get('MACD_Fast_4H_State', row.get('MACD_4H_State', 'N/A'))}</td>
                            <td>{row.get('MACD_Fast_1H_State', row.get('MACD_1H_State', 'N/A'))}</td>
                            <td>{row.get('MACD_Baseline_1D_Regime', 'N/A')}</td>
                            <td>{row.get('MACD_1H_Crossover', 'N/A')}</td>
                            <td>{row.get('MACD_Flow_State', 'N/A')}</td>
                            <td>{_format_decimal(row.get('RSI_1D'))}</td>
                            <td>{row.get('CandidateReason', 'N/A')}</td>
                        </tr>
"""
        html_content += """
                    </tbody>
                </table>
            </div>
"""
    
    html_content += f"""
        </div>
        
        <footer>
            <p>Stock Screener v1.0 | Powered by MACD Technical Analysis</p>
            <p>Disclaimer: This screener is for informational purposes only. Always conduct your own research before trading.</p>
        </footer>
    </div>
</body>
</html>
"""
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_file
