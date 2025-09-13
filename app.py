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
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    df["channel"] = source_name
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

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

    for n in ["impression", "clicks", "spend", "attributed_revenue"]:
        df[n] = pd.to_numeric(df[n], errors="coerce").fillna(0)

    return df

# ------------------------------
# Load Data
# ------------------------------
@st.cache_data
def load_data():
    def safe_read(path, source_name=None):
        try:
            df = pd.read_csv(path)
            if source_name:
                return norm(df, source_name)
            else:
                df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                return df
        except:
            return pd.DataFrame()

    # Load marketing files (case-insensitive)
    fb = safe_read("Facebook.csv", "Facebook")
    if fb.empty:
        fb = safe_read("facebook.csv", "Facebook")

    gg = safe_read("data/Google.csv", "Google")
    if gg.empty:
        gg = safe_read("data/google.csv", "Google")

    tk = safe_read("data/TikTok.csv", "TikTok")
    if tk.empty:
        tk = safe_read("data/tiktok.csv", "TikTok")

    # Load business file (case-insensitive)
    biz = safe_read("Business.csv")
    if biz.empty:
        biz = safe_read("business.csv")

    mkt = pd.concat([fb, gg, tk], ignore_index=True)
    return mkt, biz

# ------------------------------
# Derive Metrics
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

    mkt_day["ctr"] = mkt_day["clicks"] / mkt_day["impression"].replace(0, pd.NA)
    mkt_day["cpc"] = mkt_day["spend"] / mkt_day["clicks"].replace(0, pd.NA)
    mkt_day["roas"] = mkt_day["attributed_revenue"] / mkt_day["spend"].replace(0, pd.NA)
else:
    mkt_day = pd.DataFrame()

if not biz.empty:
    # normalize column names (# of orders → of_orders, etc.)
    if "of_orders" in biz.columns:
        biz["orders"] = biz["of_orders"]
    if "or_new_orders" in biz.columns:
        biz["new_orders"] = biz["or_new_orders"]

    biz["gross_margin_pct"] = biz["gross_profit"] / biz["total_revenue"].replace(0, pd.NA)
else:
    biz = pd.DataFrame()

# ------------------------------
# Streamlit Layout
# ------------------------------
st.set_page_config(page_title="Executive BI Dashboard", layout="wide")
st.title("📊 Marketing & Business Executive Dashboard")

# Date filter
if not mkt_day.empty:
    min_date, max_date = mkt_day["date"].min(), mkt_day["date"].max()
    start, end = st.date_input("Select Date Range", [min_date, max_date])
    mask = (mkt_day["date"] >= pd.to_datetime(start)) & (mkt_day["date"] <= pd.to_datetime(end))
    mkt_day = mkt_day.loc[mask]
    if not biz.empty:
        biz = biz.loc[(biz["date"] >= pd.to_datetime(start)) & (biz["date"] <= pd.to_datetime(end))]

# ------------------------------
# KPIs
# ------------------------------
st.subheader("Key Metrics")

col1, col2, col3, col4, col5, col6 = st.columns(6)

if not mkt_day.empty:
    total_spend = mkt_day["spend"].sum()
    total_rev = mkt_day["attributed_revenue"].sum()
    total_clicks = mkt_day["clicks"].sum()
    roas = total_rev / total_spend if total_spend > 0 else 0
else:
    total_spend = total_rev = total_clicks = roas = 0

if not biz.empty:
    total_orders = biz["orders"].sum() if "orders" in biz.columns else 0
    total_new_orders = biz["new_orders"].sum() if "new_orders" in biz.columns else 0
    gross_margin = biz["gross_margin_pct"].mean() if "gross_margin_pct" in biz.columns else 0
    cac = total_spend / total_new_orders if total_new_orders > 0 else 0
else:
    total_orders = total_new_orders = gross_margin = cac = 0

col1.metric("Spend", f"${total_spend:,.0f}")
col2.metric("Revenue", f"${total_rev:,.0f}")
col3.metric("ROAS", f"{roas:.2f}x")
col4.metric("CAC", f"${cac:,.2f}")
col5.metric("Orders", f"{total_orders:,}")
col6.metric("Gross Margin %", f"{gross_margin:.1%}")

# ------------------------------
# Trends
# ------------------------------
st.subheader("Trends Over Time")

if not mkt_day.empty:
    spend_rev = (
        mkt_day.groupby("date", as_index=False)
        .agg(spend=("spend", "sum"), revenue=("attributed_revenue", "sum"))
    )
    fig = px.line(spend_rev, x="date", y=["spend", "revenue"], title="Spend vs Revenue Over Time")
    st.plotly_chart(fig, use_container_width=True)

if not biz.empty and "orders" in biz.columns:
    fig2 = px.line(biz, x="date", y="orders", title="Orders Over Time")
    st.plotly_chart(fig2, use_container_width=True)

if not biz.empty and "gross_profit" in biz.columns:
    fig3 = px.line(biz, x="date", y="gross_profit", title="Gross Profit Over Time")
    st.plotly_chart(fig3, use_container_width=True)

# ------------------------------
# Channel Efficiency
# ------------------------------
st.subheader("Channel Efficiency")

if not mkt_day.empty:
    channel_perf = (
        mkt_day.groupby("channel", as_index=False)
        .agg(
            spend=("spend", "sum"),
            revenue=("attributed_revenue", "sum"),
            clicks=("clicks", "sum"),
            impression=("impression", "sum"),
        )
    )
    channel_perf["roas"] = channel_perf["revenue"] / channel_perf["spend"].replace(0, pd.NA)
    channel_perf["cpc"] = channel_perf["spend"] / channel_perf["clicks"].replace(0, pd.NA)
    channel_perf["ctr"] = channel_perf["clicks"] / channel_perf["impression"].replace(0, pd.NA)

    col1, col2, col3 = st.columns(3)
    with col1:
        fig4 = px.bar(channel_perf, x="channel", y="roas", title="ROAS by Channel", text_auto=".2f")
        st.plotly_chart(fig4, use_container_width=True)
    with col2:
        fig5 = px.bar(channel_perf, x="channel", y="cpc", title="CPC by Channel", text_auto=".2f")
        st.plotly_chart(fig5, use_container_width=True)
    with col3:
        fig6 = px.bar(channel_perf, x="channel", y="ctr", title="CTR by Channel", text_auto=".2%")
        st.plotly_chart(fig6, use_container_width=True)

# ------------------------------
# Insights Panel
# ------------------------------
st.subheader("📌 Key Insights")

insights = []
if not mkt_day.empty:
    if roas > 2:
        insights.append(f"High efficiency: Overall ROAS is {roas:.2f}x, strong return on marketing spend.")
    elif roas < 1:
        insights.append("⚠️ Marketing spend is higher than attributed revenue → reconsider budget allocation.")

    if cac > 0:
        insights.append(f"CAC is ${cac:.2f}. Compare this to customer LTV (if available) to evaluate sustainability.")

if not biz.empty:
    if total_orders > 0 and total_new_orders / total_orders > 0.5:
        insights.append("Strong growth: A large share of orders are from new customers.")
    if gross_margin < 0.3:
        insights.append("⚠️ Gross margin is below 30% → profitability pressure.")

if insights:
    for i in insights:
        st.markdown(f"- {i}")
else:
    st.write("No major insights for this period.")
