import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Marketing Monitoring Agent", page_icon="📊", layout="wide")
st.title("Marketing Performance Dashboard")
st.caption("POC | Synthetic data | Designed for future Databricks Genie integration")

@st.cache_data
def load_data():
    path = Path(__file__).resolve().parents[1] / "data" / "marketing_performance.csv"
    data = pd.read_csv(path, parse_dates=["date"])
    return data

df = load_data()

with st.sidebar:
    st.header("Dashboard filters")
    min_date, max_date = df.date.min().date(), df.date.max().date()
    date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    regions = st.multiselect("Region", sorted(df.region.unique()), default=sorted(df.region.unique()))
    channels = st.multiselect("Channel", sorted(df.channel.unique()), default=sorted(df.channel.unique()))
    campaigns = st.multiselect("Campaign", sorted(df.campaign.unique()), default=sorted(df.campaign.unique()))

if len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

filtered = df[
    df.date.dt.date.between(start_date, end_date)
    & df.region.isin(regions)
    & df.channel.isin(channels)
    & df.campaign.isin(campaigns)
].copy()

if filtered.empty:
    st.warning("No data matches the selected filters. Please change your filters.")
    st.stop()

spend = filtered.spend.sum()
revenue = filtered.revenue.sum()
conversions = filtered.conversions.sum()
clicks = filtered.clicks.sum()
roas = revenue / spend if spend else 0
cvr = conversions / clicks * 100 if clicks else 0

c1,c2,c3,c4 = st.columns(4)
c1.metric("Total Spend", f"₹{spend:,.0f}")
c2.metric("Total Revenue", f"₹{revenue:,.0f}")
c3.metric("Conversions", f"{conversions:,.0f}")
c4.metric("ROAS", f"{roas:.2f}x")
st.caption(f"Conversion rate: {cvr:.2f}%  |  Records: {len(filtered):,}")

daily = filtered.groupby("date", as_index=False).agg(spend=("spend","sum"), revenue=("revenue","sum"))
daily["roas"] = daily.revenue / daily.spend.replace(0, pd.NA)

left, right = st.columns(2)
with left:
    st.subheader("Revenue and spend trend")
    trend = daily.melt(id_vars="date", value_vars=["revenue","spend"], var_name="metric", value_name="amount")
    fig = px.line(trend, x="date", y="amount", color="metric", markers=True)
    fig.update_layout(legend_title_text="", yaxis_title="Amount (₹)", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader("ROAS trend")
    fig = px.line(daily, x="date", y="roas", markers=True)
    fig.add_vline(x="2026-10-20", line_dash="dash", annotation_text="Synthetic anomaly begins")
    fig.update_layout(yaxis_title="ROAS", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Channel performance")
channel_perf = filtered.groupby("channel", as_index=False).agg(
    spend=("spend","sum"), revenue=("revenue","sum"),
    conversions=("conversions","sum"), clicks=("clicks","sum")
)
channel_perf["ROAS"] = channel_perf.revenue / channel_perf.spend
channel_perf["Conversion rate (%)"] = channel_perf.conversions / channel_perf.clicks * 100
st.dataframe(channel_perf.sort_values("ROAS", ascending=False).round(2), use_container_width=True, hide_index=True)

st.subheader("Monitoring alerts")
baseline = df[(df.date < pd.Timestamp("2026-10-20")) & df.channel.isin(channels) & df.region.isin(regions) & df.campaign.isin(campaigns)]
recent = filtered[filtered.date >= pd.Timestamp("2026-10-20")]
if not baseline.empty and not recent.empty:
    base_roas = baseline.revenue.sum() / baseline.spend.sum() if baseline.spend.sum() else 0
    recent_roas = recent.revenue.sum() / recent.spend.sum() if recent.spend.sum() else 0
    change = ((recent_roas - base_roas) / base_roas * 100) if base_roas else 0
    if change < -10:
        st.error(f"ROAS has decreased by {abs(change):.1f}% compared with the pre-20 October baseline. Review channel mix, campaign targeting, and conversion performance.")
    else:
        st.success(f"No major ROAS drop detected against the selected baseline. ROAS change: {change:+.1f}%.")
else:
    st.info("Select a date range that includes both the baseline period and 20 October onward to compare monitoring results.")

st.subheader("Ask the Marketing Agent")
question = st.text_input("Example: Why did ROAS decrease after 20 October?", placeholder="Ask a question about the displayed marketing metrics")
if question:
    st.info("POC response: This dashboard currently uses rule-based analysis over synthetic data. Databricks Genie conversational answers will be connected in a later phase.")
    if "roas" in question.lower() or "return" in question.lower():
        st.write(f"Current filtered ROAS is **{roas:.2f}x**. Compare channel-level ROAS and the monitoring alert above to identify where performance changed.")
    else:
        st.write(f"The selected data contains **{len(filtered):,} records**, with **₹{spend:,.0f}** spend and **₹{revenue:,.0f}** revenue.")

st.divider()
st.caption("Prototype only. All records and insights are synthetic and must not be treated as client or production data.")
