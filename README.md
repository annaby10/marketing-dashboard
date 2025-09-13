# 📊 Marketing → Business Dashboard

This is an interactive BI dashboard built with **Streamlit** to analyze how marketing campaigns (Facebook, Google, TikTok) connect with overall e-commerce business performance.

## 1.Features
- Merges marketing & business CSVs into one unified dashboard
- KPIs: Spend, Revenue, ROAS, CAC, New Customers
- Visuals: Time series, Channel breakdown, Campaign table
- Filters: by channel

## 2.Data
Place your CSVs in `data/` with these names:
- `Facebook.csv`
- `Google.csv`
- `TikTok.csv`
- `business.csv`

Columns expected:
- Marketing: `date, campaign, state, impression(s), clicks, spend, attributed_revenue`
- Business: `date, orders, new_orders, new_customers, total_revenue, gross_profit, COGS`

## 3.Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
