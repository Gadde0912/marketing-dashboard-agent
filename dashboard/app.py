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

if pd.Timestamp(start_date) < ANOMALY_START and pd.Timestamp(end_date) >= ANOMALY_START:
    comparison = baseline.merge(recent, on="channel", how="inner")
    if comparison.empty:
        st.info("Not enough data to compare the baseline and monitoring periods.")
    else:
        comparison["baseline_roas"] = comparison.baseline_revenue / comparison.baseline_spend_total.replace(0, pd.NA)
        comparison["recent_roas"] = comparison.recent_revenue / comparison.recent_spend_total.replace(0, pd.NA)

        def pct_change(new, old):
            return (new - old) / old * 100 if pd.notna(old) and old != 0 else 0.0

        comparison["Spend change (%)"] = comparison.apply(lambda r: pct_change(r.recent_daily_spend, r.baseline_daily_spend), axis=1)
        comparison["Conversion change (%)"] = comparison.apply(lambda r: pct_change(r.recent_daily_conversions, r.baseline_daily_conversions), axis=1)
        comparison["ROAS change (%)"] = comparison.apply(lambda r: pct_change(r.recent_roas, r.baseline_roas), axis=1)

        alerts = comparison[
            (comparison["Spend change (%)"] >= 20)
            | (comparison["Conversion change (%)"] <= -20)
            | (comparison["ROAS change (%)"] <= -15)
        ]
        if alerts.empty:
            st.success("No channel crossed the current POC alert thresholds.")
        else:
            for _, alert in alerts.iterrows():
                st.error(
                    f"{alert['channel']} alert: Spend {alert['Spend change (%)']:+.1f}% | "
                    f"Conversions {alert['Conversion change (%)']:+.1f}% | "
                    f"ROAS {alert['ROAS change (%)']:+.1f}%"
                )
                if alert["Spend change (%)"] >= 20 and alert["Conversion change (%)"] <= -20:
                    st.write("Suggested action: Review campaign targeting, bidding strategy, landing-page experience and recent creative changes.")
                elif alert["ROAS change (%)"] <= -15:
                    st.write("Suggested action: Check audience quality, conversion tracking and campaign cost efficiency.")

        st.caption("Comparison: selected dates before 20 October vs selected dates from 20 October onward.")
        st.dataframe(comparison[["channel", "Spend change (%)", "Conversion change (%)", "ROAS change (%)"]].round(2), use_container_width=True, hide_index=True)
else:
    st.info("Select a date range containing dates before 20 October 2026 and dates from 20 October onward to compare periods.")

st.subheader("Ask the Marketing Agent")
question = st.text_input("Ask a question about the displayed marketing metrics", placeholder="Example: Which channel has a ROAS decline?")
if question:
    st.info("This POC currently uses rule-based monitoring over synthetic data. Databricks Genie will be connected in a later phase.")
    if "roas" in question.lower() or "return" in question.lower():
        st.write(f"Current filtered ROAS is **{roas:.2f}x**. Use the channel comparison above to identify the source of the change.")
    elif "spend" in question.lower():
        st.write(f"Current filtered spend is **₹{spend:,.0f}**.")
    elif "conversion" in question.lower():
        st.write(f"Current filtered conversions are **{conversions:,.0f}**.")
    else:
        st.write(f"The selected data contains **{len(filtered):,} records**, with **₹{spend:,.0f}** spend and **₹{revenue:,.0f}** revenue.")

st.divider()
st.caption("Prototype only. All data is synthetic. Alert thresholds are illustrative and require business validation before production use.")
