import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Marketing & Business Dashboard", layout="wide")

def safe_read(path, source_name):
    """Read CSV safely, return DataFrame or empty with warning"""
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            return df
        except Exception as e:
            st.error(f"⚠️ Could not load {source_name}: {e}")
            return pd.DataFrame()
    else:
        st.warning(f"⚠️ File not found: {path}")
        return pd.DataFrame()

# ---------- Normalizer for Marketing ----------
def norm(df, source_name):
    """Normalize marketing data columns"""
    if df.empty:
        return df

    df = df.rename(columns={c: c.strip().lower() for c in df.columns})
    # Flexible mapping
    colmap = {
        "date": "date",
        "tactic": "tactic",
        "state": "state",
        "campaign": "campaign",
        "impressions": "impressions",
        "clicks": "clicks",
        "spend": "spend",
        "attributed revenue": "revenue",  # TikTok naming
        "revenue": "revenue"
    }

    df = df.rename(columns={k: v for k, v in colmap.items() if k in df.columns})
    df["source"] = source_name
    return df

# ---------- Load Data ----------
@st.cache_data
def load_data():
    fb = safe_read("Facebook.csv", "Facebook")
    gg = safe_read("data/Google.csv", "Google")
    tk = safe_read("data/TikTok.csv", "TikTok")
    biz = safe_read("business.csv", "Business")

    # Normalize marketing
    mkt = pd.concat(
        [norm(fb, "Facebook"), norm(gg, "Google"), norm(tk, "TikTok")],
        ignore_index=True
    )

    # Fix Business column names
    if not biz.empty:
        biz = biz.rename(columns={c: c.strip().lower() for c in biz.columns})
        biz = biz.rename(columns={
            "# of orders": "orders",
            "# or new orders": "new_orders",
            "new customers": "new_customers",
            "total revenue": "total_revenue",
            "gross profit": "gross_profit",
            "cogs": "cogs"
        })
        # Ensure date col
        if "date" in biz.columns:
            biz["date"] = pd.to_datetime(biz["date"])
    return mkt, biz

mkt, biz = load_data()

# ---------- Dashboard ----------
st.title("📊 Marketing & Business Performance Dashboard")

# Section 1: Overview
st.header("🔎 Business Overview")
if not biz.empty:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Orders", f"{biz['orders'].sum():,}")
    col2.metric("New Customers", f"{biz['new_customers'].sum():,}")
    col3.metric("Revenue", f"${biz['total_revenue'].sum():,.0f}")
    col4.metric("Gross Profit", f"${biz['gross_profit'].sum():,.0f}")
else:
    st.warning("No Business data available.")

# Section 2: Marketing Spend vs Revenue
st.header("💰 Marketing Efficiency")
if not mkt.empty:
    mkt["date"] = pd.to_datetime(mkt["date"])
    spend_by_source = mkt.groupby("source", as_index=False)["spend"].sum()
    rev_by_source = mkt.groupby("source", as_index=False)["revenue"].sum()

    fig1 = px.bar(spend_by_source, x="source", y="spend", title="Total Spend by Channel")
    fig2 = px.bar(rev_by_source, x="source", y="revenue", title="Total Attributed Revenue by Channel")

    col1, col2 = st.columns(2)
    col1.plotly_chart(fig1, use_container_width=True)
    col2.plotly_chart(fig2, use_container_width=True)
else:
    st.warning("No Marketing data available.")

# Section 3: Trend Lines
st.header("📈 Trends Over Time")
if not biz.empty:
    fig3 = px.line(
        biz,
        x="date",
        y="orders",
        title="Orders Over Time"
    )
    fig4 = px.line(
        biz,
        x="date",
        y="total_revenue",
        title="Revenue Over Time"
    )
    col1, col2 = st.columns(2)
    col1.plotly_chart(fig3, use_container_width=True)
    col2.plotly_chart(fig4, use_container_width=True)

if not mkt.empty:
    fig5 = px.line(
        mkt.groupby("date", as_index=False)[["spend", "revenue"]].sum(),
        x="date",
        y=["spend", "revenue"],
        title="Marketing Spend vs Attributed Revenue"
    )
    st.plotly_chart(fig5, use_container_width=True)

# Section 4: ROI
st.header("📌 ROI by Channel")
if not mkt.empty:
    roi = (
        mkt.groupby("source", as_index=False)
        .agg({"spend": "sum", "revenue": "sum"})
    )
    roi["ROI"] = (roi["revenue"] - roi["spend"]) / roi["spend"]
    fig6 = px.bar(
        roi,
        x="source",
        y="ROI",
        title="Return on Investment (ROI) by Channel",
        text="ROI"
    )
    st.plotly_chart(fig6, use_container_width=True)
