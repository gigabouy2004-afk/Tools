import csv
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd


DEFAULT_BETA_WINDOW = 252
DEFAULT_MIN_BETA_OBSERVATIONS = 200
DEFAULT_RESIDUAL_WINDOWS = (63, 126)
DEFAULT_WEAK_FIT_R2 = 0.10
DEFAULT_MESSAGE_MAP = Path(__file__).resolve().parent / "config" / "V8_Post_Processor_Message_Map.csv"


def _finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _completed_close(df):
    if df is None or df.empty or "Close" not in df.columns:
        return pd.Series(dtype="float64")

    close = pd.to_numeric(df["Close"], errors="coerce")
    if "Regular_Session_Close" in df.columns:
        regular_close = pd.to_numeric(df["Regular_Session_Close"], errors="coerce")
        close = regular_close.combine_first(close)
    close = close.copy()
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    return close[~close.index.duplicated(keep="last")].sort_index()


def _compounded_return(returns):
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return float("nan")
    return ((1.0 + clean).prod() - 1.0) * 100.0


def _beta_band(beta):
    if beta < 0.75:
        return "DEFENSIVE"
    if beta <= 1.25:
        return "BALANCED"
    if beta <= 1.75:
        return "HIGH_SENSITIVITY"
    return "VERY_HIGH_SENSITIVITY"


def empty_beta_context(benchmark_ticker, status, detail=""):
    return {
        "Beta_Status": status,
        "Beta_Status_Detail": detail or status.replace("_", " ").lower(),
        "Beta_Benchmark": benchmark_ticker,
        "Beta_252D": float("nan"),
        "Beta_Alpha_Daily": float("nan"),
        "Beta_R2_252D": float("nan"),
        "Beta_Observations": 0,
        "Beta_Window_Start": "",
        "Beta_Window_End": "",
        "Beta_Risk_Band": "UNAVAILABLE",
        "Residual_Momentum_63D_Pct": float("nan"),
        "Residual_Momentum_126D_Pct": float("nan"),
        "Beta_Adjusted_RS_126D_Pct": float("nan"),
        "Beta_Message_Rule_Code": "BETA_UNAVAILABLE",
    }


def calculate_beta_context(
    stock_df,
    benchmark_df,
    benchmark_ticker,
    window=DEFAULT_BETA_WINDOW,
    min_observations=DEFAULT_MIN_BETA_OBSERVATIONS,
    weak_fit_r2=DEFAULT_WEAK_FIT_R2,
):
    context = empty_beta_context(benchmark_ticker, "UNAVAILABLE")
    stock_close = _completed_close(stock_df)
    benchmark_close = _completed_close(benchmark_df)
    if stock_close.empty or benchmark_close.empty:
        context["Beta_Status"] = "NO_PRICE_DATA"
        context["Beta_Status_Detail"] = "completed stock or benchmark prices unavailable"
        return context

    aligned_close = pd.concat(
        [stock_close.rename("Stock_Close"), benchmark_close.rename("Benchmark_Close")],
        axis=1,
        join="inner",
    ).dropna()
    returns = aligned_close.pct_change(fill_method=None).dropna().tail(window)
    observations = len(returns)
    context["Beta_Observations"] = observations
    if observations:
        context["Beta_Window_Start"] = returns.index[0].date().isoformat()
        context["Beta_Window_End"] = returns.index[-1].date().isoformat()
    if observations < min_observations:
        context["Beta_Status"] = "INSUFFICIENT_HISTORY"
        context["Beta_Status_Detail"] = f"{observations} aligned returns; {min_observations} required"
        return context

    stock_returns = returns["Stock_Close"]
    benchmark_returns = returns["Benchmark_Close"]
    benchmark_variance = benchmark_returns.var(ddof=1)
    if pd.isna(benchmark_variance) or benchmark_variance <= 0:
        context["Beta_Status"] = "INVALID_BENCHMARK_VARIANCE"
        context["Beta_Status_Detail"] = "benchmark return variance is not positive"
        return context

    beta = stock_returns.cov(benchmark_returns) / benchmark_variance
    alpha = stock_returns.mean() - beta * benchmark_returns.mean()
    fitted = alpha + beta * benchmark_returns
    residual = stock_returns - fitted
    total_sum_squares = ((stock_returns - stock_returns.mean()) ** 2).sum()
    residual_sum_squares = (residual ** 2).sum()
    r_squared = 1.0 - (residual_sum_squares / total_sum_squares) if total_sum_squares > 0 else float("nan")

    beta = _finite_number(beta)
    alpha = _finite_number(alpha)
    r_squared = _finite_number(r_squared)
    if beta is None or alpha is None or r_squared is None:
        context["Beta_Status"] = "INVALID_CALCULATION"
        context["Beta_Status_Detail"] = "beta regression produced a non-finite result"
        return context

    context.update(
        {
            "Beta_Status": "OK",
            "Beta_Status_Detail": "",
            "Beta_252D": beta,
            "Beta_Alpha_Daily": alpha,
            "Beta_R2_252D": max(0.0, min(1.0, r_squared)),
            "Beta_Risk_Band": _beta_band(beta),
        }
    )

    for residual_window in DEFAULT_RESIDUAL_WINDOWS:
        key = f"Residual_Momentum_{residual_window}D_Pct"
        if len(residual) >= residual_window:
            context[key] = _compounded_return(residual.tail(residual_window))

    if len(returns) >= 126:
        stock_return_126 = _compounded_return(stock_returns.tail(126))
        benchmark_return_126 = _compounded_return(benchmark_returns.tail(126))
        context["Beta_Adjusted_RS_126D_Pct"] = stock_return_126 - beta * benchmark_return_126

    if context["Beta_R2_252D"] < weak_fit_r2:
        rule_code = "BETA_WEAK_FIT"
    else:
        rule_code = f"BETA_{context['Beta_Risk_Band']}"
    context["Beta_Message_Rule_Code"] = rule_code
    return context


@lru_cache(maxsize=8)
def load_message_templates(message_map_path=str(DEFAULT_MESSAGE_MAP)):
    templates = {}
    with open(message_map_path, "r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if str(row.get("Enabled", "")).strip().upper() not in {"1", "TRUE", "YES", "Y"}:
                continue
            rule_code = str(row.get("Rule_Code", "")).strip()
            if rule_code:
                templates[rule_code] = str(row.get("Template", "")).strip()
    return templates


def _format_number(value, decimals=2, signed=False):
    number = _finite_number(value)
    if number is None:
        return "N/A"
    prefix = "+" if signed and number >= 0 else ""
    return f"{prefix}{number:.{decimals}f}"


def build_beta_message(context, message_map_path=DEFAULT_MESSAGE_MAP):
    templates = load_message_templates(str(Path(message_map_path).resolve()))
    rule_code = context.get("Beta_Message_Rule_Code", "BETA_UNAVAILABLE")
    template = templates.get(rule_code) or templates.get("BETA_UNAVAILABLE")
    if not template:
        return "Active momentum confirmed. Beta context unavailable."

    values = {
        "benchmark": context.get("Beta_Benchmark", "benchmark"),
        "beta": _format_number(context.get("Beta_252D")),
        "r2": _format_number(context.get("Beta_R2_252D")),
        "band": str(context.get("Beta_Risk_Band", "UNAVAILABLE")).replace("_", " ").lower(),
        "observations": context.get("Beta_Observations", 0),
        "residual_63d": _format_number(context.get("Residual_Momentum_63D_Pct"), signed=True),
        "residual_126d": _format_number(context.get("Residual_Momentum_126D_Pct"), signed=True),
        "status_detail": context.get("Beta_Status_Detail", "beta context unavailable"),
    }
    return template.format_map(values)


def is_beta_postprocessor_eligible(output, active_threshold):
    score = _finite_number((output or {}).get("Score"))
    return (
        (output or {}).get("Final_Decision") == "MOMENTUM_ACTIVE"
        and score is not None
        and score >= float(active_threshold)
    )


def apply_beta_postprocessor(
    output,
    stock_df,
    benchmark_df,
    benchmark_ticker,
    active_threshold,
    message_map_path=DEFAULT_MESSAGE_MAP,
):
    if not is_beta_postprocessor_eligible(output, active_threshold):
        return None

    try:
        context = calculate_beta_context(stock_df, benchmark_df, benchmark_ticker)
        output["Score_Message"] = build_beta_message(context, message_map_path)
        return context
    except Exception as exc:
        context = empty_beta_context(benchmark_ticker, "PROCESSOR_ERROR", str(exc))
        output["Score_Message"] = build_beta_message(context, message_map_path)
        return context
