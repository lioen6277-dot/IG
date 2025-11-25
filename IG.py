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
/* 優化數值顯示區域的間距 */
.value-display {{
    text-align: center;
    padding: 0.5rem 0;
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
    """從 Yahoo Finance 獲取即時價格"""
    prices = {}
    fetch_time = datetime.now()
    tickers = list(ticker_map.values())
    
    try:
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
    except Exception as e:
        st.warning(f"無法獲取行情數據，請檢查網絡連接。錯誤: {str(e)}")
        for code in ticker_map.keys():
            prices[code] = 0.0
    
    return prices, fetch_time

def calculate_investment(edited_df, total_budget, fee_rate):
    """計算投資分配結果"""
    results_list = []
    total_spent = 0.0
    
    for _, row in edited_df.iterrows():
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
    
    return results_list, total_spent

# 頁面標題
st.title("📈 Streamlit 零股投資分配計算機 (即時報價)")
st.markdown("---")

# 獲取價格
with st.spinner('正在從 Yahoo Finance 獲取最新報價...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)

st.info(f"報價更新時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')} (每 60 秒自動更新一次)")

# Sidebar 參數設定
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

# 初始化數據編輯框
data_to_edit = {
    "標的代號": list(current_prices.keys()),
    "設定比例": [ALLOCATION_WEIGHTS[code] for code in current_prices.keys()],
    "當前價格 (自動獲取)": [current_prices[code] for code in current_prices.keys()]
}
input_df = pd.DataFrame(data_to_edit)

# ========== 顯示區域 (稍後由下方編輯框控制) ==========

st.divider()
st.header("💰 總投資預算")

# 預算區塊的 container（用於後續更新）
budget_container = st.container()

st.divider()
st.subheader("✅ 建議投資分配與結果")
st.header("✨ 建議買入股數概覽 (重點)")

# 投資分配區塊的 container
results_container = st.container()

st.markdown("---")
st.subheader("📊 詳細投資表")

# 詳細表格區塊的 container
table_container = st.container()
st.caption("計算邏輯依據：優先確保買入股數最大化，且總花費不超過預算；手續費最低 1 元計算。")

# ========== 價格與比例輸入區塊（在下方） ==========
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
    num_rows="fixed",
    key="data_editor_key"
)

# 檢查比例合計
weight_sum = edited_df['設定比例'].sum()
if abs(weight_sum - 1.0) > 0.01:
    st.error(f"⚠️ 錯誤：設定比例總和必須為 100% (目前為 {weight_sum*100:.0f}%)，請調整。")
    st.stop()

# ========== 計算（基於編輯後的數據）==========
results_list, total_spent = calculate_investment(edited_df, total_budget, fee_rate)
results_df = pd.DataFrame(results_list)

# ========== 更新顯示區域 ==========

# 更新預算區塊
with budget_container:
    label_cols = st.columns(3)
    with label_cols[0]:
        st.markdown("**總投資預算**")
    with label_cols[1]:
        st.markdown("**預估總花費**")
    with label_cols[2]:
        st.markdown("**剩餘預算**")
    
    value_cols = st.columns(3)
    with value_cols[0]:
        st.markdown(f"<div class='value-display' style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>TWD {total_budget:,.0f}</div>", unsafe_allow_html=True)
    with value_cols[1]:
        st.markdown(f"<div class='value-display' style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>TWD {total_spent:,.0f}</div>", unsafe_allow_html=True)
    with value_cols[2]:
        st.markdown(f"<div class='value-display' style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>TWD {total_budget - total_spent:,.0f}</div>", unsafe_allow_html=True)

# 更新投資分配區塊
with results_container:
    for item in results_list:
        st.markdown(f"**--- {item['標的代號']} ({item['比例']}) ---**")
        
        # 標籤行
        label_cols = st.columns(4)
        with label_cols[0]:
            st.markdown("✅ 建議股數")
        with label_cols[1]:
            st.markdown("預估成本")
        with label_cols[2]:
            st.markdown("分配預算")
        with label_cols[3]:
            st.markdown("當前價格")
        
        # 數值行
        value_cols = st.columns(4)
        with value_cols[0]:
            st.markdown(f"<div class='value-display' style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>{item['建議股數']}</div>", unsafe_allow_html=True)
        with value_cols[1]:
            st.markdown(f"<div class='value-display' style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>TWD {item['總成本']:,.0f}</div>", unsafe_allow_html=True)
        with value_cols[2]:
            st.markdown(f"<div class='value-display' style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>TWD {item['分配金額']:,.0f}</div>", unsafe_allow_html=True)
        with value_cols[3]:
            st.markdown(f"<div class='value-display' style='color: {ACCENT_COLOR}; font-size: 1.8em; font-weight: bold;'>TWD {item['價格']:,.2f}</div>", unsafe_allow_html=True)

# 更新表格區塊
with table_container:
    st.dataframe(
        results_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "價格": st.column_config.NumberColumn(format="TWD %.2f"),
            "分配金額": st.column_config.NumberColumn(format="TWD %.0f"),
            "預估手續費": st.column_config.NumberColumn(format="TWD %.0f"),
            "總成本": st.column_config.NumberColumn(format="TWD %.0f"),
        }
    )
