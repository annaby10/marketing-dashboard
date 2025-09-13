import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(layout="wide", page_title="Marketing → Business Dashboard")

# ----------- Load Data -----------
DATA_DIRS = [Path("data"), Path("/mnt/data")]

def load_csv_anywhere(name):
    for d in DATA_DIRS:
        p = d / name
        if p.exists():
            return pd.read_csv(p, parse_dates=["date"], dayfirst=False)
    return pd.DataFrame()

@st.cache_data
def load_all():
    fb = load_csv_anywhere("Facebook.csv")
    google = load_csv_anywhere("Google.csv")
    tiktok = load_csv_anywhere("TikTok.csv")
    biz = load_csv_anywhere("business.csv")

    # normalize columns
    def norm(df, source_name):
        if df.empty:
            return df
        df = df.copy()
        df.columns = df.columns.str.strip().str.lower()
        df["channel"] = source_name
        df["date"] = pd.to_datetime(df["date"])
        if "impressions" in df.columns:
            df["impression"] = df["impressions"]
        for n in ["impression", "clicks", "spend", "attributed_revenue"]:
            if n in df.columns:
                df[n] = pd.to_numeric(df[n], errors="coerce").fillna(0)
        return df

    fb = norm(fb, "Facebook")
    google = norm(google, "Google")
    tiktok = norm(tiktok, "TikTok")
    mkt = pd.concat([d for d in [fb, google, tiktok] if not d.empty], ignore_index=True)

    if not biz.empty:
        biz.columns = biz.columns.str.strip().str.lower()
        biz["date"] = pd.to_datetime(biz["date"])
    return mkt, biz

mkt, biz = load_all()

if mkt.empty and biz.empty:
    st.warning("No data found. Place CSVs in ./data/ and refresh.")
    st.stop()

# ----------- Aggregations -----------
mkt_day = mkt.groupby(["date", "channel"], as_index=False).agg(
    impression=("impression", "sum"),
    clicks=("clicks", "sum"),
    spend=("spend", "sum"),
    attributed_revenue=("attributed_revenue", "sum"),
)
mkt_day["ctr"] = mkt_day["clicks"] / mkt_day["impression"].replace({0: pd.NA})
mkt_day["cpc"] = mkt_day["spend"] / mkt_day["clicks"].replace({0: pd.NA})
mkt_day["roas"] = mkt_day["attributed_revenue"] / mkt_day["spend"].replace({0: pd.NA})

summary_by_date = mkt_day.groupby("date", as_index=False).agg(
    spend=("spend", "sum"),
    attributed_revenue=("attributed_revenue", "sum"),
    clicks=("clicks", "sum"),
    impression=("impression", "sum"),
)

if not biz.empty:
    biz_daily = biz.groupby("date", as_index=False).agg(
        orders=("orders", "sum") if "orders" in biz.columns else ("new_orders", "sum"),
        new_customers=("new_customers", "sum"),
        total_revenue=("total_revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
    )
    merged = summary_by_date.merge(biz_daily, on="date", how="left").fillna(0)
else:
    merged = summary_by_date

merged["cac"] = merged["spend"] / merged["new_customers"].replace({0: pd.NA})
merged["rev_per_order"] = merged["total_revenue"] / merged["orders"].replace({0: pd.NA})

# ----------- UI -----------
st.title("📊 Marketing → Business Dashboard")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Spend", f"${merged['spend'].sum():,.0f}")
c2.metric("Total Attributed Revenue", f"${merged['attributed_revenue'].sum():,.0f}")
c3.metric("ROAS", f"{(merged['attributed_revenue'].sum()/merged['spend'].sum()):.2f}" if merged['spend'].sum()>0 else "N/A")
c4.metric("New Customers", f"{int(merged['new_customers'].sum()) if 'new_customers' in merged.columns else 0}")

channels = ["All"] + sorted(mkt["channel"].dropna().unique().tolist())
sel_channel = st.selectbox("Channel", channels)

df_plot = merged.copy()
if sel_channel != "All":
    dates = mkt_day[mkt_day["channel"] == sel_channel].groupby("date", as_index=False).sum()
    df_plot = summary_by_date.merge(dates[["date", "spend", "attributed_revenue"]], on="date", how="inner")

fig = px.line(
    df_plot.sort_values("date"),
    x="date",
    y=["spend", "attributed_revenue", "total_revenue"] if "total_revenue" in df_plot.columns else ["spend", "attributed_revenue"],
    labels={"value": "Amount", "variable": "Metric"},
    title="Spend vs Revenue over time",
)
st.plotly_chart(fig, use_container_width=True)

ch_summary = mkt.groupby("channel", as_index=False).agg(spend=("spend", "sum"), attributed_revenue=("attributed_revenue", "sum"))
fig2 = px.bar(ch_summary, x="channel", y=["spend", "attributed_revenue"], title="Channel: Spend vs Attributed Revenue", barmode="group")
st.plotly_chart(fig2, use_container_width=True)

camp = mkt.groupby(["channel", "campaign"], as_index=False).agg(
    impression=("impression", "sum"),
    clicks=("clicks", "sum"),
    spend=("spend", "sum"),
    attributed_revenue=("attributed_revenue", "sum"),
)
camp["ctr"] = camp["clicks"] / camp["impression"].replace({0: pd.NA})
camp["roas"] = camp["attributed_revenue"] / camp["spend"].replace({0: pd.NA})
st.subheader("Campaign Performance")
st.dataframe(camp.sort_values("spend", ascending=False).reset_index(drop=True))
