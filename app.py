import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ------------------------------
# Helper: Normalize marketing CSVs
# ------------------------------
def norm(df, source_name):
    if df.empty:
        return df
    df = df.copy()

    # Standardize column names
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    df["channel"] = source_name
    df["date"] = pd.to_datetime(df["date"])

    # Normalize expected columns
    if "impressions" in df.columns:
        df["impression"] = df["impressions"]

    if "impression" not in df.columns:
        df["impression"] = 0
    if "clicks" not in df.columns:
        df["clicks"] = 0
    if "spend" not in df.columns:
        df["spend"] = 0
    if "attributed_revenue" not in df.columns:
        df["attributed_revenue"] = 0

    # Ensure numeric
    for n in ["impression", "clicks", "spend", "attributed_revenue"]:
        df[n] = pd.to_numeric(df[n], errors="coerce").fillna(0)

    return df


# ------------------------------
# Load Data
# ------------------------------
@st.cache_data
def load_data():
    try:
        fb = pd.read_csv("Facebook.csv")
        fb = norm(fb, "Facebook")
    except Exception as e:
        st.warning(f"⚠️ Could not load Facebook.csv: {e}")
        fb = pd.DataFrame()

    try:
        gg = pd.read_csv("data/Google.csv")
        gg = norm(gg, "Google")
    except Exception as e:
        st.warning(f"⚠️ Could not load Google.csv: {e}")
        gg = pd.DataFrame()

    try:
        tk = pd.read_csv("data/TikTok.csv")
        tk = norm(tk, "TikTok")
    except Exception as e:
        st.warning(f"⚠️ Could not load TikTok.csv: {e}")
        tk = pd.DataFrame()

    try:
        biz = pd.read_csv("business.csv")
        biz.columns = biz.columns.str.strip().str.lower().str.replace(" ", "_")
        biz["date"] = pd.to_datetime(biz["date"])
    except Exception as e:
        st.warning(f"⚠️ Could not load Business.csv: {e}")
        biz = pd.DataFrame()

    mkt = pd.concat([fb, gg, tk], ignore_index=True)
    return mkt, biz


mkt, biz = load_data()

# ------------------------------
# Aggregations
# ------------------------------
if not mkt.empty:
    mkt_day = (
        mkt.groupby(["date", "channel"], as_index=False)
        .agg(
            impression=("impression", "sum"),
            clicks=("clicks", "sum"),
            spend=("spend", "sum"),
            attributed_revenue=("attributed_revenue", "sum"),
        )
    )
else:
    mkt_day = pd.DataFrame()

# ------------------------------
# Streamlit Layout
# ------------------------------
st.set_page_config(page_title="Marketing & Business Dashboard", layout="wide")
st.title("📊 Marketing & Business Performance Dashboard")

# Date filter
if not mkt_day.empty:
    min_date = mkt_day["date"].min()
    max_date = mkt_day["date"].max()
    start, end = st.date_input("Select Date Range", [min_date, max_date])
    mask = (mkt_day["date"] >= pd.to_datetime(start)) & (mkt_day["date"] <= pd.to_datetime(end))
    mkt_day = mkt_day.loc[mask]
    if not biz.empty:
        biz = biz.loc[(biz["date"] >= pd.to_datetime(start)) & (biz["date"] <= pd.to_datetime(end))]

# KPIs
st.subheader("Key Metrics")
col1, col2, col3, col4 = st.columns(4)

if not mkt_day.empty:
    total_spend = mkt_day["spend"].sum()
    total_rev = mkt_day["attributed_revenue"].sum()
    total_clicks = mkt_day["clicks"].sum()
    impressions = mkt_day["impression"].sum()
else:
    total_spend = total_rev = total_clicks = impressions = 0

if not biz.empty:
    total_orders = biz["orders"].sum()
    total_customers = biz["new_customers"].sum()
else:
    total_orders = total_customers = 0

col1.metric("Total Spend", f"${total_spend:,.0f}")
col2.metric("Attributed Revenue", f"${total_rev:,.0f}")
col3.metric("Orders", f"{total_orders:,}")
col4.metric("New Customers", f"{total_customers:,}")

# Charts
st.subheader("Marketing Performance Over Time")
if not mkt_day.empty:
    fig = px.line(
        mkt_day,
        x="date",
        y="spend",
        color="channel",
        title="Daily Spend by Channel",
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.line(
        mkt_day,
        x="date",
        y="attributed_revenue",
        color="channel",
        title="Attributed Revenue by Channel",
    )
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Business Performance Over Time")
if not biz.empty:
    fig3 = px.line(
        biz,
        x="date",
        y="orders",
        title="Orders Over Time",
    )
    st.plotly_chart(fig3, use_container_width=True)

    fig4 = px.line(
        biz,
        x="date",
        y="gross_profit",
        title="Gross Profit Over Time",
    )
    st.plotly_chart(fig4, use_container_width=True)

st.subheader("Channel Efficiency")
if not mkt_day.empty:
    channel_perf = (
        mkt_day.groupby("channel", as_index=False)
        .agg(spend=("spend", "sum"), revenue=("attributed_revenue", "sum"))
        .assign(roas=lambda d: d["revenue"] / d["spend"].replace(0, pd.NA))
    )
    fig5 = px.bar(
        channel_perf,
        x="channel",
        y="roas",
        title="ROAS by Channel",
        text_auto=".2f",
    )
    st.plotly_chart(fig5, use_container_width=True)
