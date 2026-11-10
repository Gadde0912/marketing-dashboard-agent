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
    csv_path = Path(__file__).resolve().parents[1] / "data" / "marketing_performance.csv"
    data = pd.read_csv(csv_path)
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    for col in ["spend", "revenue", "conversions", "clicks", "impressions"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)
    data = data.dropna(subset=["date"])
    return data

df = load_data()

with st.sidebar:
    st.header("Dashboard filters")
    min_date, max_date = df["date"].min().date(), df["date"].max().date()
    selected_dates = st.date_input(
        "Date range", value=(min_date, max_date),
        min_value=min_date, max_value=max_date
    )
    regions = st.multiselect("Region", sorted(df["region"].dropna().unique()), default=sorted(df["region"].dropna().unique()))
    channels = st.multiselect("Channel", sorted(df["channel"].dropna().unique()), default=sorted(df["channel"].dropna().unique()))
    campaigns = st.multiselect("Campaign", sorted(df["campaign"].dropna().unique()), default=sorted(df["campaign"].dropna().unique()))

if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date, end_date = min_date, max_date

filtered = df[
    df["date"].dt.date.between(start_date, end_date)
    & df["region"].isin(regions)
    & df["channel"].isin(channels)
    & df["campaign"].isin(campaigns)
].copy()

if filtered.empty:
    st.warning("No data matches the selected filters. Please change your filters.")
    st.stop()

spend = filtered["spend"].sum()
revenue = filtered["revenue"].sum()
conversions = filtered["conversions"].sum()
clicks = filtered["clicks"].sum()
roas = revenue / spend if spend else 0
conversion_rate = conversions / clicks * 100 if clicks else 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Spend", f"₹{spend:,.0f}")
k2.metric("Total Revenue", f"₹{revenue:,.0f}")
k3.metric("Conversions", f"{conversions:,.0f}")
k4.metric("ROAS", f"{roas:.2f}x")
st.caption(f"Conversion rate: {conversion_rate:.2f}% | Records: {len(filtered):,}")

daily = filtered.groupby("date", as_index=False).agg(
    spend=("spend", "sum"), revenue=("revenue", "sum"),
    conversions=("conversions", "sum"), clicks=("clicks", "sum")
)
daily["roas"] = daily["revenue"].div(daily["spend"].replace(0, pd.NA))

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
channel_perf["ROAS"] = channel_perf["revenue"].div(channel_perf["spend"].replace(0, pd.NA))
channel_perf["Conversion rate (%)"] = (
    channel_perf["conversions"].div(channel_perf["clicks"].replace(0, pd.NA)) * 100
)
st.dataframe(channel_perf.sort_values("ROAS", ascending=False).round(2), use_container_width=True, hide_index=True)

# Anomaly monitoring: always render period counts and comparison output.
st.subheader("Intelligent anomaly monitoring")
st.write("The POC compares average daily channel performance before and after 20 October 2026.")

before = filtered[filtered["date"] < ANOMALY_START].copy()
after = filtered[filtered["date"] >= ANOMALY_START].copy()

m1, m2, m3 = st.columns(3)
m1.metric("Baseline records", f"{len(before):,}")
m2.metric("Monitoring-period records", f"{len(after):,}")
m3.metric("Monitoring start", "20 Oct 2026")

if before.empty or after.empty:
    st.warning("The selected filters do not contain records on both sides of 20 October 2026. Select a date range covering both periods.")
else:
    before_daily = before.groupby(["channel", "date"], as_index=False).agg(
        spend=("spend", "sum"), revenue=("revenue", "sum"), conversions=("conversions", "sum")
    )
    after_daily = after.groupby(["channel", "date"], as_index=False).agg(
        spend=("spend", "sum"), revenue=("revenue", "sum"), conversions=("conversions", "sum")
    )

    b = before_daily.groupby("channel", as_index=False).agg(
        baseline_spend_per_day=("spend", "mean"),
        baseline_conversions_per_day=("conversions", "mean"),
        baseline_roas=("revenue", "sum")
    )
    b_spend_total = before_daily.groupby("channel")["spend"].sum()
    b["baseline_roas"] = b["baseline_roas"] / b["channel"].map(b_spend_total)

    a = after_daily.groupby("channel", as_index=False).agg(
        recent_spend_per_day=("spend", "mean"),
        recent_conversions_per_day=("conversions", "mean"),
        recent_roas=("revenue", "sum")
    )
    a_spend_total = after_daily.groupby("channel")["spend"].sum()
    a["recent_roas"] = a["recent_roas"] / a["channel"].map(a_spend_total)

    comparison = b.merge(a, on="channel", how="inner")

    def safe_percent_change(new_value, old_value):
        if pd.isna(old_value) or old_value == 0:
            return 0.0
        return (new_value - old_value) / old_value * 100

    comparison["Spend change (%)"] = comparison.apply(
        lambda row: safe_percent_change(row["recent_spend_per_day"], row["baseline_spend_per_day"]), axis=1
    )
    comparison["Conversion change (%)"] = comparison.apply(
        lambda row: safe_percent_change(row["recent_conversions_per_day"], row["baseline_conversions_per_day"]), axis=1
    )
    comparison["ROAS change (%)"] = comparison.apply(
        lambda row: safe_percent_change(row["recent_roas"], row["baseline_roas"]), axis=1
    )

    display = comparison[["channel", "Spend change (%)", "Conversion change (%)", "ROAS change (%)"]].copy()
    st.dataframe(display.round(2), use_container_width=True, hide_index=True)

    alerts = comparison[
        (comparison["Spend change (%)"] >= 20)
        | (comparison["Conversion change (%)"] <= -20)
        | (comparison["ROAS change (%)"] <= -15)
    ]

    if alerts.empty:
        st.success("No channel crossed the configured POC alert thresholds.")
    else:
        st.markdown("#### Detected alerts")
        for _, row in alerts.iterrows():
            st.error(
                f"{row['channel']}: Spend {row['Spend change (%)']:+.1f}% | "
                f"Conversions {row['Conversion change (%)']:+.1f}% | "
                f"ROAS {row['ROAS change (%)']:+.1f}%"
            )
            if row["Spend change (%)"] >= 20 and row["Conversion change (%)"] <= -20:
                st.write("Suggested action: Review targeting, bids, campaign creative, landing-page experience and conversion tracking.")
            elif row["ROAS change (%)"] <= -15:
                st.write("Suggested action: Review audience quality, campaign cost efficiency and conversion tracking.")

st.subheader("Ask the Marketing Agent")
question = st.text_input(
    "Ask a question about the displayed marketing metrics",
    placeholder="Example: Why did Google Ads ROAS decline?"
)
if question:
    q = question.lower()
    st.info("This version uses rule-based analysis on synthetic data. Databricks Genie integration is a later POC phase.")
    if "google" in q and ("roas" in q or "decline" in q or "drop" in q):
        google_row = channel_perf[channel_perf["channel"].str.lower() == "google ads"]
        if not google_row.empty:
            st.write(f"Google Ads current filtered ROAS is **{google_row.iloc[0]['ROAS']:.2f}x**.")
        google_alert = comparison[comparison["channel"].str.lower() == "google ads"] if "comparison" in locals() else pd.DataFrame()
        if not google_alert.empty:
            row = google_alert.iloc[0]
            st.write(
                f"Compared with the baseline, Google Ads spend per day changed by **{row['Spend change (%)']:+.1f}%**, "
                f"conversions per day changed by **{row['Conversion change (%)']:+.1f}%**, "
                f"and ROAS changed by **{row['ROAS change (%)']:+.1f}%**."
            )
    elif "spend" in q:
        st.write(f"Current filtered spend is **₹{spend:,.0f}**.")
    elif "conversion" in q:
        st.write(f"Current filtered conversions are **{conversions:,.0f}**.")
    else:
        st.write(f"The selected data contains **{len(filtered):,} records**, with **₹{spend:,.0f}** spend and **₹{revenue:,.0f}** revenue.")

st.divider()
st.caption("Prototype only. All data is synthetic. Alert thresholds are illustrative and need business validation before production use.")
