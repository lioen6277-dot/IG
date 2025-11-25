import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

PRIMARY_COLOR = "#f08080"
ACCENT_COLOR = "#e9967a"

st.markdown(f"""
<style>
.stApp {{
    font-size: 1.2rem;
}}
h1, h2, h3 {{
    font-size: 1.5em !important;
    color: {PRIMARY_COLOR} !important;
}}
div[data-testid="stMetricValue"] {{
    color: {ACCENT_COLOR} !important;
    font-size: 1.8rem !important;
}}
.st-emotion-cache-1dpn6dr {{
    color: {PRIMARY_COLOR} !important;
}}
.st-emotion-cache-1c19gh9 {{
    background-color: {ACCENT_COLOR} !important;
    color: white !important;
}}
div[data-testid="stDataFrame"] {{
    font-size: 1.1rem;
}}
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="零股投資計算機 (即時報價)",
    layout="wide",
    initial_sidebar_state="expanded"
)

TICKER_MAP = {
    "009813": "009813.TW",
    "0050": "0050.TW",
    "00878": "00878.TW",
}
ALLOCATION_WEIGHTS = {
    "009813": 0.50,
    "0050": 0.30,
    "00878": 0.20
}
FEE_RATE_DEFAULT = 0.001425
MIN_FEE = 1

@st.cache_data(ttl=60)
def get_current_prices(ticker_map):
    prices = {}
    fetch_time = datetime.now()
    tickers = list(ticker_map.values())
    data = yf.download(tickers, period="1d", interval="1m", progress=False, timeout=5)
    
    for code, ticker in ticker_map.items():
        try:
            if not data.empty and ticker in data['Close']:
                price = data['Close'][ticker].iloc[-1]
                prices[code] = round(price, 2)
            else:
                prices[code] = 0.0
        except Exception:
            prices[code] = 0.0
    
    return prices, fetch_time

st.title("📈 Streamlit 零股投資分配計算機 (即時報價)")
st.markdown("---")

with st.spinner('正在從 Yahoo Finance 獲取最新報價...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)

st.info(f"報價更新時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')} (每 60 秒自動更新一次)")

st.sidebar.header("🎯 投資參數設定")
total_budget = st.sidebar.number_input(
    "每月投資總預算 (TWD)",
    min_value=1000,
    value=3000,
    step=1000,
    format="%d"
)
fee_rate = st.sidebar.number_input(
    "手續費率 (0.xxxx)",
    min_value=0.0001,
    max_value=0.01,
    value=FEE_RATE_DEFAULT,
    format="%.6f"
)
st.sidebar.caption(f"手續費最低 {MIN_FEE} 元 / 筆")

data_to_edit = {
    "標的代號": list(current_prices.keys()),
    "設定比例": [ALLOCATION_WEIGHTS[code] for code in current_prices.keys()],
    "當前價格 (自動獲取)": [current_prices[code] for code in current_prices.keys()]
}
input_df = pd.DataFrame(data_to_edit)

results_list = []
total_spent = 0.0

for _, row in input_df.iterrows():
    code = row["標的代號"]
    weight = row["設定比例"]
    price = row["當前價格 (自動獲取)"]
    allocated_budget = total_budget * weight
    
    if price > 0:
        shares_to_buy = int(allocated_budget / (price * (1 + fee_rate)))
        fee_calculated = price * shares_to_buy * fee_rate
        estimated_fee = max(MIN_FEE, round(fee_calculated))
        total_cost = (shares_to_buy * price) + estimated_fee
    else:
        shares_to_buy = 0
        estimated_fee = 0
        total_cost = 0.0
    
    total_spent += total_cost
    results_list.append({
        "標的代號": code,
        "比例": f"{weight*100:.0f}%",
        "價格": price,
        "分配金額": allocated_budget,
        "建議股數": shares_to_buy,
        "預估手續費": estimated_fee,
        "總成本": total_cost,
    })

results_df = pd.DataFrame(results_list)

st.divider()
st.header("💰 總投資預算")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="總投資預算", value=f"TWD {total_budget:,.0f}")
with col2:
    st.metric(label="預估總花費", value=f"TWD {total_spent:,.0f}")
with col3:
    st.metric(label="剩餘預算", value=f"TWD {total_budget - total_spent:,.0f}")

st.divider()
st.subheader("✅ 建議投資分配與結果")
st.header("✨ 建議買入股數概覽 (重點)")

for item in results_list:
    st.markdown(f"**--- {item['標的代號']} ({item['比例']}) ---**")
    
    label_cols = st.columns(4)
    with label_cols[0]:
        st.markdown("✅ 建議股數")
    with label_cols[1]:
        st.markdown("預估成本")
    with label_cols[2]:
        st.markdown("分配預算")
    with label_cols[3]:
        st.markdown("當前價格")
    
    value_cols = st.columns(4)
    with value_cols[0]:
        st.markdown(f"<div style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>{item['建議股數']}</div>", unsafe_allow_html=True)
    with value_cols[1]:
        st.markdown(f"<div style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>TWD {item['總成本']:,.0f}</div>", unsafe_allow_html=True)
    with value_cols[2]:
        st.markdown(f"<div style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>TWD {item['分配金額']:,.0f}</div>", unsafe_allow_html=True)
    with value_cols[3]:
        st.markdown(f"<div style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>TWD {item['價格']:,.2f}</div>", unsafe_allow_html=True)

st.markdown("---")

st.subheader("📊 詳細投資表")
st.dataframe(
    results_df,
    hide_index=True,
    column_config={
        "價格": st.column_config.NumberColumn(format="TWD %.2f"),
        "分配金額": st.column_config.NumberColumn(format="TWD %d"),
        "總成本": st.column_config.NumberColumn(format="TWD %d"),
    }
)
st.caption("計算邏輯依據：優先確保買入股數最大化，且總花費不超過預算；手續費最低 1 元計算。")

st.divider()
st.subheader("價格與比例輸入")
st.caption("報價為自動獲取，您仍可手動點擊價格欄位進行情境測試。")

edited_df = st.data_editor(
    input_df,
    hide_index=True,
    column_config={
        "當前價格 (自動獲取)": st.column_config.NumberColumn(
            "當前價格 (TWD)",
            min_value=0.01,
            format="%.2f"
        )
    },
    num_rows="fixed"
)

if edited_df['設定比例'].sum() != 1.0:
    st.error(f"⚠️ 錯誤：設定比例總和必須為 100% (目前為 {edited_df['設定比例'].sum()*100:.0f}%)，請調整。")
    st.stop()
    
