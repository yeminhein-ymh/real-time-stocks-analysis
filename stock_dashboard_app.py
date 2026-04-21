"""
Real-time-ish stock analysis dashboard for:
Google, Amazon, Nvidia, Nebius, Sandisk, and Palantir.

Run:
  pip install streamlit yfinance pandas numpy plotly
  streamlit run stock_dashboard_app.py

Notes:
  - Data comes from Yahoo Finance through yfinance. Free market data can be
    delayed and occasionally rate-limited.
  - Signals are educational only, not financial advice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


STOCKS = {
    "Google": "GOOGL",
    "Amazon": "AMZN",
    "Nvidia": "NVDA",
    "Nebius": "NBIS",
    "Sandisk": "SNDK",
    "Palantir": "PLTR",
}

TIMEFRAMES = {
    "1 Day": {"period": "1d", "interval": "1m", "days": 1},
    "3 Days": {"period": "5d", "interval": "5m", "days": 3},
    "7 Days": {"period": "10d", "interval": "15m", "days": 7},
}


@dataclass
class StockSummary:
    name: str
    ticker: str
    last_price: float
    start_price: float
    change: float
    change_pct: float
    high: float
    low: float
    volume: int
    rsi: float
    trend: str
    signal: str
    score: int


def flatten_columns(data: pd.DataFrame) -> pd.DataFrame:
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] if isinstance(col, tuple) else col for col in data.columns]
    return data


@st.cache_data(ttl=60, show_spinner=False)
def fetch_stock_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    data = yf.download(
        tickers=ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=True,
        prepost=True,
        threads=False,
    )
    data = flatten_columns(data)
    if data.empty:
        return data

    data = data.dropna(subset=["Close"]).copy()
    data.index = pd.to_datetime(data.index)
    if data.index.tz is None:
        data.index = data.index.tz_localize("UTC")
    return data


def filter_recent_days(data: pd.DataFrame, days: int) -> pd.DataFrame:
    if data.empty:
        return data
    latest = data.index.max()
    cutoff = latest - timedelta(days=days)
    filtered = data[data.index >= cutoff].copy()
    return filtered if not filtered.empty else data


def add_indicators(data: pd.DataFrame) -> pd.DataFrame:
    data = data.copy()
    data["SMA_20"] = data["Close"].rolling(window=20, min_periods=3).mean()
    data["EMA_20"] = data["Close"].ewm(span=20, adjust=False).mean()

    typical_price = (data["High"] + data["Low"] + data["Close"]) / 3
    volume = data["Volume"].replace(0, np.nan)
    data["VWAP"] = (typical_price * volume).cumsum() / volume.cumsum()

    delta = data["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14, min_periods=5).mean()
    avg_loss = loss.rolling(window=14, min_periods=5).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    data["RSI_14"] = 100 - (100 / (1 + rs))
    data["RSI_14"] = data["RSI_14"].fillna(50)
    return data


def build_summary(name: str, ticker: str, data: pd.DataFrame) -> StockSummary | None:
    if data.empty:
        return None

    first_close = float(data["Close"].iloc[0])
    last_close = float(data["Close"].iloc[-1])
    change = last_close - first_close
    change_pct = (change / first_close) * 100 if first_close else 0
    high = float(data["High"].max())
    low = float(data["Low"].min())
    volume = int(data["Volume"].sum())
    rsi = float(data["RSI_14"].iloc[-1])
    sma = float(data["SMA_20"].iloc[-1]) if not pd.isna(data["SMA_20"].iloc[-1]) else last_close
    ema = float(data["EMA_20"].iloc[-1]) if not pd.isna(data["EMA_20"].iloc[-1]) else last_close
    vwap = float(data["VWAP"].iloc[-1]) if not pd.isna(data["VWAP"].iloc[-1]) else last_close

    score = 0
    score += 1 if change_pct > 0 else -1
    score += 1 if last_close > sma else -1
    score += 1 if ema >= sma else -1
    score += 1 if last_close > vwap else -1
    score += 1 if 45 <= rsi <= 70 else -1 if rsi > 75 or rsi < 30 else 0

    if score >= 3:
        signal = "Bullish / Watch for long setup"
    elif score <= -3:
        signal = "Bearish / Be careful"
    else:
        signal = "Neutral / Wait"

    if last_close > sma and ema >= sma:
        trend = "Uptrend"
    elif last_close < sma and ema < sma:
        trend = "Downtrend"
    else:
        trend = "Sideways"

    return StockSummary(
        name=name,
        ticker=ticker,
        last_price=last_close,
        start_price=first_close,
        change=change,
        change_pct=change_pct,
        high=high,
        low=low,
        volume=volume,
        rsi=rsi,
        trend=trend,
        signal=signal,
        score=score,
    )


def make_price_chart(name: str, ticker: str, data: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["Open"],
            high=data["High"],
            low=data["Low"],
            close=data["Close"],
            name="Price",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["SMA_20"],
            mode="lines",
            line=dict(width=1.4, color="#0072B2"),
            name="SMA 20",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["VWAP"],
            mode="lines",
            line=dict(width=1.4, color="#D55E00"),
            name="VWAP",
        )
    )
    fig.update_layout(
        title=f"{name} ({ticker}) Price",
        height=460,
        margin=dict(l=10, r=10, t=45, b=10),
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        legend=dict(orientation="h", y=1.02, x=0),
    )
    return fig


def make_rsi_chart(name: str, ticker: str, data: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["RSI_14"],
            mode="lines",
            line=dict(width=1.8, color="#009E73"),
            name="RSI 14",
        )
    )
    fig.add_hline(y=70, line_dash="dash", line_color="#D55E00")
    fig.add_hline(y=30, line_dash="dash", line_color="#0072B2")
    fig.update_layout(
        title=f"{name} ({ticker}) RSI",
        height=260,
        margin=dict(l=10, r=10, t=45, b=10),
        template="plotly_white",
        yaxis=dict(range=[0, 100]),
    )
    return fig


def format_money(value: float) -> str:
    return f"${value:,.2f}"


def format_pct(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def summary_to_frame(summaries: list[StockSummary]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Stock": item.name,
                "Ticker": item.ticker,
                "Last Price": format_money(item.last_price),
                "Change": format_money(item.change),
                "Change %": format_pct(item.change_pct),
                "High": format_money(item.high),
                "Low": format_money(item.low),
                "Volume": f"{item.volume:,}",
                "RSI": f"{item.rsi:.1f}",
                "Trend": item.trend,
                "Signal": item.signal,
                "Score": item.score,
            }
            for item in summaries
        ]
    )


def render_stock_cards(summaries: list[StockSummary]) -> None:
    cols = st.columns(3)
    for index, item in enumerate(summaries):
        with cols[index % 3]:
            st.metric(
                label=f"{item.name} ({item.ticker})",
                value=format_money(item.last_price),
                delta=format_pct(item.change_pct),
            )
            st.caption(f"{item.trend} | RSI {item.rsi:.1f} | {item.signal}")


def main() -> None:
    st.set_page_config(
        page_title="Real-Time Stocks Analysis",
        page_icon="chart",
        layout="wide",
    )

    st.title("Real-Time Stocks Analysis")
    st.caption(
        "Google, Amazon, Nvidia, Nebius, Sandisk, and Palantir. "
        "Data refreshes every 60 seconds when you reload or interact with the app."
    )

    with st.sidebar:
        st.header("Settings")
        selected_names = st.multiselect(
            "Stocks",
            options=list(STOCKS.keys()),
            default=list(STOCKS.keys()),
        )
        selected_timeframe = st.radio(
            "Analysis timeframe",
            options=list(TIMEFRAMES.keys()),
            index=0,
        )
        st.info("This is for analysis and education only, not financial advice.")

    config = TIMEFRAMES[selected_timeframe]
    all_results: dict[str, pd.DataFrame] = {}
    summaries: list[StockSummary] = []

    with st.spinner("Fetching latest market data..."):
        for name in selected_names:
            ticker = STOCKS[name]
            raw = fetch_stock_data(ticker, config["period"], config["interval"])
            recent = filter_recent_days(raw, config["days"])
            analyzed = add_indicators(recent) if not recent.empty else recent
            all_results[name] = analyzed
            summary = build_summary(name, ticker, analyzed)
            if summary is not None:
                summaries.append(summary)

    if not summaries:
        st.error("No market data returned. Try again later or check your internet connection.")
        return

    updated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    st.caption(f"Last app refresh: {updated_at}")

    render_stock_cards(summaries)

    st.subheader(f"{selected_timeframe} Comparison")
    table = summary_to_frame(summaries)
    st.dataframe(table, use_container_width=True, hide_index=True)

    best = max(summaries, key=lambda item: item.change_pct)
    weakest = min(summaries, key=lambda item: item.change_pct)
    st.write(
        f"Strongest in this timeframe: **{best.name} ({best.ticker})** "
        f"at **{format_pct(best.change_pct)}**. "
        f"Weakest: **{weakest.name} ({weakest.ticker})** "
        f"at **{format_pct(weakest.change_pct)}**."
    )

    st.subheader("Charts")
    for item in summaries:
        data = all_results[item.name]
        with st.expander(f"{item.name} ({item.ticker})", expanded=item.name == summaries[0].name):
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Last", format_money(item.last_price))
            col_b.metric("Change", format_money(item.change), format_pct(item.change_pct))
            col_c.metric("High / Low", f"{format_money(item.high)} / {format_money(item.low)}")
            col_d.metric("Signal Score", str(item.score), item.trend)
            st.plotly_chart(make_price_chart(item.name, item.ticker, data), use_container_width=True)
            st.plotly_chart(make_rsi_chart(item.name, item.ticker, data), use_container_width=True)


if __name__ == "__main__":
    main()
