"""Regenerate the sample synthetic marketing dataset."""
from pathlib import Path
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
dates = pd.date_range("2026-08-01", "2026-10-29", freq="D")
channels = ["Google Ads", "Meta Ads", "LinkedIn Ads", "Email Marketing"]
regions = ["India", "US", "UK", "Australia"]
campaigns = ["Diwali Campaign", "Brand Awareness", "Lead Generation", "Product Launch", "Retargeting"]
rows = []
for date in dates:
    for channel in channels:
        for region in regions:
            for campaign in campaigns:
                impressions = int(rng.integers(5000, 30000))
                clicks = max(1, int(impressions * rng.uniform(0.015, 0.065)))
                spend = round(float(rng.uniform(250, 1800)), 2)
                conversions = max(0, int(clicks * rng.uniform(0.035, 0.12)))
                revenue = round(float(conversions * rng.uniform(900, 2600)), 2)
                if date >= pd.Timestamp("2026-10-20") and channel == "Google Ads":
                    spend, conversions, revenue = round(spend * 1.30, 2), int(conversions * 0.65), round(revenue * 0.65, 2)
                rows.append([date.date(), channel, region, campaign, impressions, clicks, spend, conversions, revenue])
out = Path(__file__).resolve().parents[1] / "data" / "marketing_performance.csv"
pd.DataFrame(rows, columns=["date","channel","region","campaign","impressions","clicks","spend","conversions","revenue"]).to_csv(out, index=False)
print(f"Created {out}")
