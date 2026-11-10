import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Marketing Monitoring Agent", page_icon="📊", layout="wide")
st.title("Marketing Performance Dashboard")
st.caption("POC | Synthetic data | Intelligent KPI monitoring | Future Databricks Genie integration")

ANOMALY_START = pd.Timestamp("2026-10-20")

@st.cache_data
def load_data():
    path = Path(__file__).resolve().parents[1] / "data" / "marketing_performance.csv"
    return pd.read_csv(path, parse_dates=["date"])

df = load_data()

with st.sidebar:
    st.header("Dashboard filters")
    min_date, max_date = df.date.min().date(), df.date.max().date()
    date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    regions = st.multiselect("Region", sorted(df.region.unique()), default=sorted(df.region.unique()))
    channels = st.multiselect("Channel", sorted(df.channel.unique()), default=sorted(df.channel.unique()))
    campaigns = st.multiselect("Campaign", sorted(df.campaign.unique()), default=sorted(df.campaign.unique()))

start_date, end_date = date_range if len(date_range) == 2 else (min_date, max_date)
filtered = df[
    df.date.dt.date.between(start_date, end_date)
    & df.region.isin(regions) & df.channel.isin(channels) & df.campaign.isin(campaigns)
].copy()

if filtered.empty:
    st.warning("No data matches the selected filters. Please change your filters.")
    st.stop()

spend, revenue = filtered.spend.sum(), filtered.revenue.sum()
conversions, clicks = filtered.conversions.sum(), filtered.clicks.sum()
roas = revenue / spend if spend else 0
cvr = conversions / clicks * 100 if clicks else 0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Spend", f"₹{spend:,.0f}")
c2.metric("Total Revenue", f"₹{revenue:,.0f}")
c3.metric("Conversions", f"{conversions:,.0f}")
c4.metric("ROAS", f"{roas:.2f}x")
st.caption(f"Conversion rate: {cvr:.2f}% | Records: {len(filtered):,}")

daily = filtered.groupby("date", as_index=False).agg(
    spend=("spend", "sum"), revenue=("revenue", "sum"),
    conversions=("conversions", "sum"), clicks=("clicks", "sum")
)
daily["roas"] = daily.revenue / daily.spend.where(daily.spend != 0)

left, right = st.columns(2)
with left:
    st.subheader("Revenue and spend trend")
    trend = daily.melt(id_vars="date", value_vars=["revenue", "spend"], var_name="metric", value_name="amount")
    fig = px.line(trend, x="date", y="amount", color="metric", markers=True)
    fig.update_layout(legend_title_text="", yaxis_title="Amount (₹)", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("ROAS trend")
    fig = px.line(daily, x="date", y="roas", markers=True)
    if pd.Timestamp(start_date) <= ANOMALY_START <= pd.Timestamp(end_date):
        fig.add_vline(x=ANOMALY_START, line_dash="dash", annotation_text="Monitoring event starts")
    fig.update_layout(yaxis_title="ROAS", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Channel performance")
channel_perf = filtered.groupby("channel", as_index=False).agg(
    spend=("spend", "sum"), revenue=("revenue", "sum"),
    conversions=("conversions", "sum"), clicks=("clicks", "sum")
)
channel_perf["ROAS"] = channel_perf.revenue / channel_perf.spend.replace(0, pd.NA)
channel_perf["Conversion rate (%)"] = channel_perf.conversions / channel_perf.clicks.replace(0, pd.NA) * 100
st.dataframe(channel_perf.sort_values("ROAS", ascending=False).round(2), use_container_width=True, hide_index=True)

st.subheader("Intelligent anomaly monitoring")
# Compare average daily spend and conversions so periods of different lengths are fair.
baseline_daily = filtered[filtered.date < ANOMALY_START].groupby(["channel", "date"], as_index=False).agg(
    spend=("spend", "sum"), revenue=("revenue", "sum"), conversions=("conversions", "sum")
)
recent_daily = filtered[filtered.date >= ANOMALY_START].groupby(["channel", "date"], as_index=False).agg(
    spend=("spend", "sum"), revenue=("revenue", "sum"), conversions=("conversions", "sum")
)
baseline = baseline_daily.groupby("channel", as_index=False).agg(
    baseline_daily_spend=("spend", "mean"),
    baseline_daily_conversions=("conversions", "mean"),
    baseline_revenue=("revenue", "sum"), baseline_spend_total=("spend", "sum")
)
recent = recent_daily.groupby("channel", as_index=False).agg(
    recent_daily_spend=("spend", "mean"),
    recent_daily_conversions=("conversions", "mean"),
    recent_revenue=("revenue", "sum"), recent_spend_total=("spend", "sum")
)
