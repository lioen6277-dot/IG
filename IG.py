import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# --- 0. CSS 注入：字體放大與配色方案 ---
PRIMARY_COLOR = "#f08080"  # 珊瑚紅/淡紅
ACCENT_COLOR = "#e9967a"   # 淺鮭色/深橙色

st.markdown(f"""
<style>
/* -------------------- 全域字體與排版優化 -------------------- */
.stApp {{
    font-size: 1.2rem;
}}
h1, h2, h3 {{
    font-size: 1.5em !important;
}}

/* -------------------- 配色方案應用 -------------------- */

/* 標題顏色使用主色 */
h1, h2, h3 {{
    color: {PRIMARY_COLOR} !important;
}}

/* Metric (關鍵數字) 的值使用強調色 */
div[data-testid="stMetricValue"] {{
    color: {ACCENT_COLOR} !important;
    font-size: 1.8rem !important;
}}

/* 側邊欄標題顏色 */
.st-emotion-cache-1dpn6dr {{ /* Targeting specific sidebar headers */
    color: {PRIMARY_COLOR} !important;
}}

/* 模擬表格標題的配色 (應用在 data_editor 的 header) */
/* 這是 Streamlit 內部較難直接命中的元素，使用最接近的選擇器來設定背景 */
.st-emotion-cache-1c19gh9 {{ 
    background-color: {ACCENT_COLOR} !important;
    color: white !important; /* 確保文字可讀 */
}}

/* 調整表格內的文字大小 */
div[data-testid="stDataFrame"] {{
    font-size: 1.1rem;
}}

</style>
""", unsafe_allow_html=True)


# --- 1. 固定參數與配置 ---

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

FEE_RATE_DEFAULT: float = 0.001425
MIN_FEE: int = 1

# --- 2. 價格獲取函式 (使用 Streamlit 快取) ---

@st.cache_data(ttl=60) # 設定快取時間為 60 秒
def get_current_prices(ticker_map):
    """從 Yahoo Finance 獲取即時價格"""
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


# --- 3. Streamlit 應用程式開始 ---

st.title("📈 Streamlit 零股投資分配計算機 (即時報價)")
st.markdown("---")

with st.spinner('正在從 Yahoo Finance 獲取最新報價...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)

st.info(f"報價更新時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')} (每 60 秒自動更新一次)")


# --- 4. 側邊欄輸入區 (Sidebar Inputs) ---

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


# --- 5. 數據準備與輸入區 (價格與比例輸入) ---

data_to_edit = {
    "標的代號": list(current_prices.keys()),
    "設定比例": [ALLOCATION_WEIGHTS[code] for code in current_prices.keys()],
    "當前價格 (自動獲取)": [current_prices[code] for code in current_prices.keys()]
}
input_df = pd.DataFrame(data_to_edit)

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


# --- 6. 計算核心邏輯 ---

results_list = []
total_spent = 0.0

for index, row in edited_df.iterrows():
    code = row["標的代號"]
    weight = row["設定比例"]
    price = row["當前價格 (自動獲取)"] 

    allocated_budget = total_budget * weight

    shares_to_buy = 0
    estimated_fee = 0
    total_cost = 0.0

    if price > 0:
        shares_to_buy = int(allocated_budget / (price * (1 + fee_rate)))
        fee_calculated = price * shares_to_buy * fee_rate
        estimated_fee = max(MIN_FEE, round(fee_calculated))
        total_cost = (shares_to_buy * price) + estimated_fee

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

# --- 7. 輸出區 ---

# 輸出 1: 總投資預算 (Summary Metrics)
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

# 輸出 2: 建議投資分配與結果 (Highlight & Detailed Table)
st.subheader("✅ 建議投資分配與結果")

st.header("✨ 建議買入股數概覽 (重點)")
# 使用 st.metric 凸顯每個標的的股數
for item in results_list:
    st.markdown(f"**--- {item['標的代號']} ({item['比例']}) ---**")
    cols = st.columns(4)
    cols[0].metric(label="✅ 建議股數", value=item['建議股數'])
    cols[1].metric(label="預估成本", value=f"TWD {item['總成本']:,.0f}")
    cols[2].metric(label="分配預算", value=f"TWD {item['分配金額']:,.0f}")
    cols[3].metric(label="當前價格", value=f"TWD {item['價格']:,.2f}")
st.markdown("---")


# 詳細表格
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
