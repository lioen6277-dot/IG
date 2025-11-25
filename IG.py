import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# --- 1. 固定參數與配置 ---

# 設定頁面標題和佈局
st.set_page_config(
    page_title="零股投資計算機 (即時報價)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 台灣股市代碼對應 Yahoo Finance Ticker
TICKER_MAP = {
    "009813": "009813.TW",  # **注意: 009813.TW 可能為無效代碼，請自行檢查。**
    "0050": "0050.TW",
    "00878": "00878.TW",
}
# 預設比例
ALLOCATION_WEIGHTS = {
    "009813": 0.50, 
    "0050": 0.30, 
    "00878": 0.20
}

FEE_RATE_DEFAULT: float = 0.001425  # 0.1425%
MIN_FEE: int = 1  # 零股手續費最低 1 元

# --- 2. 價格獲取函式 (使用 Streamlit 快取) ---

@st.cache_data(ttl=60) # 設定快取時間為 60 秒 (每 60 秒才會重新向 Yahoo Finance 請求一次資料)
def get_current_prices(ticker_map):
    """從 Yahoo Finance 獲取即時價格"""
    prices = {}
    fetch_time = datetime.now()
    
    # 使用 yf.download 批量獲取數據
    tickers = list(ticker_map.values())
    data = yf.download(tickers, period="1d", interval="1m", progress=False)

    for code, ticker in ticker_map.items():
        try:
            # 嘗試取得最新收盤價 (Close)
            if not data.empty and ticker in data['Close']:
                price = data['Close'][ticker].iloc[-1]
                prices[code] = round(price, 2)
            else:
                st.warning(f"⚠️ 無法獲取 {code} ({ticker}) 最新價格，將使用預設值或 0。")
                prices[code] = 0.0
        except Exception:
            prices[code] = 0.0
            
    return prices, fetch_time


# --- 3. Streamlit 應用程式開始 ---

st.title("📈 Streamlit 零股投資分配計算機 (即時報價)")
st.markdown("---")

# 獲取價格
with st.spinner('正在從 Yahoo Finance 獲取最新報價...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)

st.info(f"報價更新時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')} (每 60 秒自動更新一次)")


# --- 4. 側邊欄輸入區 (Sidebar Inputs) ---

st.sidebar.header("🎯 投資參數設定")

total_budget = st.sidebar.number_input(
    "每月投資總預算 (TWD)",
    min_value=1000,
    value=20000,
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


# --- 5. 數據準備與輸入區 ---

# 建立用於顯示和調整的 DataFrame
data_to_edit = {
    "標的代號": list(current_prices.keys()),
    "設定比例": [ALLOCATION_WEIGHTS[code] for code in current_prices.keys()],
    "當前價格 (自動獲取)": [current_prices[code] for code in current_prices.keys()]
}
input_df = pd.DataFrame(data_to_edit)

st.subheader("價格與比例輸入 (可手動修改價格進行情境測試)")

# 使用 data_editor 顯示價格，並允許使用者手動修改
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

# 檢查輸入比例總和
if edited_df['設定比例'].sum() != 1.0:
    st.error(f"⚠️ 錯誤：設定比例總和必須為 100% (目前為 {edited_df['設定比例'].sum()*100:.0f}%)，請調整。")
    st.stop()


# --- 6. 計算核心邏輯 ---

results_list = []
total_spent = 0.0

for index, row in edited_df.iterrows():
    code = row["標的代號"]
    weight = row["設定比例"]
    price = row["當前價格 (自動獲取)"] # 使用使用者可能調整過的新價格

    # 1. 分配金額 (D欄)
    allocated_budget = total_budget * weight

    shares_to_buy = 0
    estimated_fee = 0
    total_cost = 0.0

    if price > 0:
        # 2. 建議買入股數 (E欄)
        shares_to_buy = int(allocated_budget / (price * (1 + fee_rate)))

        # 3. 預估手續費 (F欄)
        fee_calculated = price * shares_to_buy * fee_rate
        estimated_fee = max(MIN_FEE, round(fee_calculated))

        # 4. 總成本
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

# --- 7. 輸出結果 ---

results_df = pd.DataFrame(results_list)

st.subheader("✅ 建議投資分配與結果")
st.dataframe(
    results_df,
    hide_index=True,
    column_config={
        "價格": st.column_config.NumberColumn(format="TWD %.2f"),
        "分配金額": st.column_config.NumberColumn(format="TWD %d"),
        "總成本": st.column_config.NumberColumn(format="TWD %d"),
    }
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="💰 總投資預算", value=f"TWD {total_budget:,.0f}")

with col2:
    st.metric(label="💸 預估總花費", value=f"TWD {total_spent:,.0f}")

with col3:
    st.metric(label="🎁 剩餘預算", value=f"TWD {total_budget - total_spent:,.0f}")
    
