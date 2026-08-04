import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


VARIANT_LABELS = {
    "STANDARD_12_26_9": "MACD 12/26/9",
    "FIBONACCI_8_21_5": "MACD 8/21/5",
}


def macd_frame(close, fast, slow, signal):
    fast_ema = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    slow_ema = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    line = fast_ema - slow_ema
    signal_line = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return line, signal_line


def main():
    parser = argparse.ArgumentParser(description="Plot dual-MACD comparison evidence")
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    charts_dir = run_dir / "charts"
    charts_dir.mkdir(exist_ok=True)
    experiment = json.loads(
        (run_dir / "inputs" / "V8_MACD_Foundation_Comparison_Expanded_Config.json").read_text(
            encoding="utf-8"
        )
    )
    summary = pd.read_csv(run_dir / "outputs" / "selection_summary.csv")

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    for row_index, stage in enumerate(["FOUNDATION", "HEALTH_QUALIFIED"]):
        for column_index, horizon in enumerate([1, 3]):
            axis = axes[row_index, column_index]
            scoped = summary.loc[summary["Stage"] == stage].copy()
            labels = []
            values = []
            colors = []
            for sector in ["ALL", "Technology", "Industrials"]:
                for variant in ["STANDARD_12_26_9", "FIBONACCI_8_21_5"]:
                    row = scoped.loc[
                        (scoped["Sector"] == sector) & (scoped["MACD_Variant"] == variant)
                    ].iloc[0]
                    labels.append(f"{sector}\n{VARIANT_LABELS[variant].replace('MACD ', '')}")
                    values.append(float(row[f"D{horizon}_False_Positive_Rate_Pct"]))
                    colors.append("#4472C4" if variant == "STANDARD_12_26_9" else "#ED7D31")
            bars = axis.bar(range(len(values)), values, color=colors)
            axis.set_xticks(range(len(labels)), labels, fontsize=8)
            axis.set_ylim(0, max(60, max(values) + 8))
            axis.set_ylabel("False-positive rate (%)")
            axis.set_title(f"{stage.replace('_', ' ').title()} — D+{horizon}")
            axis.grid(axis="y", alpha=0.25)
            for bar, value in zip(bars, values):
                axis.text(bar.get_x() + bar.get_width() / 2, value + 1, f"{value:.1f}%", ha="center", fontsize=8)
    fig.suptitle("MACD Foundation Comparison: Selected Signals With Non-Positive Forward Return", fontsize=15)
    false_positive_path = charts_dir / "false_positive_rate_comparison.png"
    fig.savefig(false_positive_path, dpi=160)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    for axis, stage in zip(axes, ["FOUNDATION", "HEALTH_QUALIFIED"]):
        scoped = summary.loc[(summary["Stage"] == stage) & (summary["Sector"] != "ALL")]
        labels, values, colors = [], [], []
        for sector in ["Technology", "Industrials"]:
            for variant in ["STANDARD_12_26_9", "FIBONACCI_8_21_5"]:
                row = scoped.loc[
                    (scoped["Sector"] == sector) & (scoped["MACD_Variant"] == variant)
                ].iloc[0]
                labels.append(f"{sector}\n{VARIANT_LABELS[variant].replace('MACD ', '')}")
                values.append(int(row["Selected"]))
                colors.append("#4472C4" if variant == "STANDARD_12_26_9" else "#ED7D31")
        bars = axis.bar(range(len(values)), values, color=colors)
        axis.set_xticks(range(len(labels)), labels)
        axis.set_ylabel("Selected stock-date observations")
        axis.set_title(stage.replace("_", " ").title())
        axis.grid(axis="y", alpha=0.25)
        for bar, value in zip(bars, values):
            axis.text(bar.get_x() + bar.get_width() / 2, value + 3, str(value), ha="center")
    fig.suptitle("Selection Count: MACD 12/26/9 vs 8/21/5", fontsize=15)
    count_path = charts_dir / "selection_count_comparison.png"
    fig.savefig(count_path, dpi=160)
    plt.close(fig)

    transitions = pd.read_csv(run_dir / "outputs" / "transition_rows.csv")
    foundation = transitions.loc[transitions["Stage"] == "FOUNDATION"].copy()
    examples = []
    for sector in ["Technology", "Industrials"]:
        for transition in ["STANDARD_ONLY", "FIBONACCI_ONLY"]:
            candidates = foundation.loc[
                (foundation["Sector"] == sector) & (foundation["Transition"] == transition)
            ].sort_values(["As_Of_Date", "Ticker"])
            if not candidates.empty:
                examples.append(candidates.iloc[0])
    fig, axes = plt.subplots(2, 2, figsize=(15, 9), constrained_layout=True)
    axes = axes.ravel()
    chart_examples = []
    lookback = int(experiment["Chart_Lookback_Sessions"])
    for axis, example in zip(axes, examples):
        ticker = example["Ticker"]
        signal_date = pd.Timestamp(example["As_Of_Date"])
        prices = pd.read_csv(run_dir / "inputs" / "prices" / f"{ticker}.csv", parse_dates=["Date"]).set_index("Date")
        prefix = prices.loc[prices.index <= signal_date]
        standard_line, standard_signal = macd_frame(prefix["Close"], 12, 26, 9)
        fibonacci_line, fibonacci_signal = macd_frame(prefix["Close"], 8, 21, 5)
        visible = prefix.index[-lookback:]
        axis.plot(visible, standard_line.loc[visible], color="#4472C4", label="12/26/9 line")
        axis.plot(visible, standard_signal.loc[visible], color="#4472C4", linestyle="--", label="12/26/9 signal")
        axis.plot(visible, fibonacci_line.loc[visible], color="#ED7D31", label="8/21/5 line")
        axis.plot(visible, fibonacci_signal.loc[visible], color="#ED7D31", linestyle="--", label="8/21/5 signal")
        axis.axhline(0, color="black", linewidth=0.8, alpha=0.5)
        axis.axvline(signal_date, color="black", linewidth=0.8, alpha=0.5)
        axis.set_title(f"{example['Sector']} — {ticker} — {signal_date.date()}\n{example['Transition']}")
        axis.grid(alpha=0.2)
        axis.legend(fontsize=7, ncol=2)
        chart_examples.append(
            {
                "Sector": example["Sector"],
                "Ticker": ticker,
                "As_Of_Date": signal_date.date().isoformat(),
                "Transition": example["Transition"],
            }
        )
    for axis in axes[len(examples) :]:
        axis.axis("off")
    fig.suptitle("MACD Line and Signal Examples Where Foundation Variants Disagree", fontsize=15)
    line_path = charts_dir / "macd_line_signal_disagreement_examples.png"
    fig.savefig(line_path, dpi=160)
    plt.close(fig)

    manifest = {
        "Charts": [false_positive_path.name, count_path.name, line_path.name],
        "MACD_Example_Selection": "First chronological ticker/date for each sector and disagreement direction; outcomes were not used",
        "MACD_Examples": chart_examples,
    }
    (charts_dir / "chart_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
