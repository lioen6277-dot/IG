import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time 

# 設定頁面配置必須在 CSS 注入前 (必須放在腳本最頂端)
st.set_page_config(
    page_title="零股投資計算機 (第100次極致優化版)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 顏色定義與常數 ---
PRIMARY_COLOR = "#f08080"   # 珊瑚紅 (主要標題/邊框)
ACCENT_COLOR = "#e9967a"    # 淺鮭色 (建議股數/強調數據)
TEXT_COLOR = "#ffffff"      # 白色 (內容文字)
LABEL_COLOR = "#b0b0b0"     # 淡灰 (標籤文字)

# 投資標的與對應的 Yahoo Finance 代號
TICKER_MAP = {
    "009813": "009813.TW",
    "0050": "0050.TW",
    "00878": "00878.TW",
}
# 預設分配權重 (必須總和為 1.0)
ALLOCATION_WEIGHTS = {
    "009813": 0.50,
    "0050": 0.30,
    "00878": 0.20
}
FEE_RATE_DEFAULT = 0.001425 # 預設費率
MIN_FEE = 1                 # 最低手續費 (TWD)

# --- 0. CSS 注入：深色模式與客製化主題 (全面指標卡片化) ---

st.markdown(f"""
<style>
/* -------------------- 應用程式全域設定 -------------------- */

.stApp {{
    font-size: 1.05rem; 
    color: {TEXT_COLOR};
    background-color: #0e1117; 
}}

h1 {{
    font-size: 2.0em !important;
    color: {PRIMARY_COLOR} !important;
    font-weight: bold !important;
    margin-bottom: 0.5rem !important;
}}

/* -------------------- 單一卡片排版的核心調整 (極致整合) -------------------- */

/* Main Card - THE ENTIRE APP CONTAINER */
.metric-card-main {{
    background: #1a1a1a; 
    border: 1px solid rgba(240, 128, 128, 0.3); 
    border-radius: 12px;
    padding: 1.5rem; 
    margin-top: 1rem;
}}

/* Sub Card (For Budget Metrics) */
.metric-card-sub {{
    background: rgba(255, 255, 255, 0.05); 
    border-radius: 8px;
    padding: 1rem;
    height: 100%; 
    margin-bottom: 0.5rem;
}}

/* Detail Card (For Ticker Results) */
.metric-card-detail {{
    background: #252525; /* 略淺於主卡，增加層次 */
    border-radius: 6px;
    padding: 0.8rem;
    margin-bottom: 0.3rem;
}}

/* Ticker Header - Input/Result Row */
.ticker-row-container {{
    margin-bottom: 1.5rem;
    padding: 1rem;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.03); /* 每個標的獨立的微卡片背景 */
    border-left: 3px solid {PRIMARY_COLOR};
}}

/* Label text - used everywhere */
.label-text {{
    font-size: 0.9em;
    color: {LABEL_COLOR};
    font-weight: 500;
    margin-bottom: 0.2rem;
    line-height: 1.2;
}}

/* Value text - Main Budget style */
.value-text-main {{
    color: {TEXT_COLOR};
    font-size: 1.5em; 
    font-weight: bold;
}}

/* Value text - Regular style for Cost, Budget, Price */
.value-text-regular {{
    color: {TEXT_COLOR};
    font-size: 1.1em; 
    font-weight: bold;
}}

/* Value text - Highlighted style for Shares (最大化強調) */
.value-text-highlight {{
    color: {ACCENT_COLOR}; 
    font-size: 1.7em; 
    font-weight: bold;
}}

/* Card Section Header (Internal H2 replacement) */
.card-section-header {{
    color: {PRIMARY_COLOR};
    font-weight: bold;
    font-size: 1.4em;
    padding: 0.5rem 0;
    margin-top: 2rem;
    margin-bottom: 0.5rem;
    border-bottom: 1px dashed rgba(240, 128, 128, 0.5); 
}}

/* --- 專門針對 st.number_input 的樣式優化 (使其融入卡片) --- */

.stNumberInput label {{
    display: none !important;
}}

.stNumberInput > div > div {{
    background-color: rgba(0, 0, 0, 0.2); 
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
}}

.stNumberInput {{
    margin-top: -5px; 
}}

/* -------------------- 其他微調 -------------------- */
div[role="alert"] {{
    background-color: rgba(240, 128, 128, 0.15) !important; 
    border-left: 5px solid {PRIMARY_COLOR} !important; 
    color: {TEXT_COLOR} !important;
    font-size: 1.0em !important; 
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
}}

.stDivider {{
    display: none; 
}}

</style>
""", unsafe_allow_html=True)


# --- 2. 核心函式 ---

@st.cache_data(ttl=60)
def get_current_prices(ticker_map):
    """
    從 Yahoo Finance 獲取即時價格 (60秒快取)。
    """
    prices = {}
    fetch_time = datetime.now()
    tickers = list(ticker_map.values())
    
    try:
        data = yf.download(tickers, period="1d", interval="1m", progress=False, timeout=5)
        
        for code, ticker in ticker_map.items():
            try:
                if not data.empty and ticker in data['Close']:
                    price_series = data['Close'][ticker]
                    valid_prices = price_series.dropna()
                    if not valid_prices.empty:
                        price = valid_prices.iloc[-1]
                        prices[code] = round(price, 2)
                    else:
                        prices[code] = 0.0
                else:
                    prices[code] = 0.0
            except Exception:
                prices[code] = 0.0
    except Exception:
        print("⚠️ 無法獲取行情數據，所有價格已設為 0。")
        for code in ticker_map.keys():
            prices[code] = 0.0
            
    return prices, fetch_time

def calculate_investment(edited_df, total_budget, fee_rate):
    """
    計算投資分配結果。
    """
    results_list = []
    total_spent = 0.0
    
    for _, row in edited_df.iterrows():
        code = row["標的代號"]
        weight = row["設定比例"]
        price = row["當前價格 (自動獲取)"]
        allocated_budget = total_budget * weight
        
        shares_to_buy = 0
        estimated_fee = 0
        total_cost = 0.0
        
        if price > 0 and allocated_budget > 0:
            # 股數 = 預算 / (價格 * (1 + 費率))
            shares_to_buy = int(allocated_budget / (price * (1 + fee_rate)))
            
            if shares_to_buy < 0:
                shares_to_buy = 0
            
            if shares_to_buy > 0:
                fee_calculated = price * shares_to_buy * fee_rate
                estimated_fee = max(MIN_FEE, round(fee_calculated))
                total_cost = (shares_to_buy * price) + estimated_fee
            
                # 健壯性檢查：如果最低手續費導致總成本超支，則減少一股
                if total_cost > allocated_budget:
                    shares_to_buy -= 1
                    
                    if shares_to_buy > 0:
                        fee_recalculated = price * shares_to_buy * fee_rate
                        estimated_fee = max(MIN_FEE, round(fee_recalculated))
                        total_cost = (shares_to_buy * price) + estimated_fee
                    else:
                        estimated_fee = 0
                        total_cost = 0.0

        if total_cost > allocated_budget:
             total_cost = allocated_budget 

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

def render_budget_metrics(total_budget, total_spent):
    """渲染總預算指標卡片 (3欄) - 使用 sub-card 樣式"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card-sub'> 
            <div class='label-text'>💰 總投資預算</div>
            <div class='value-text-main'>TWD {total_budget:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card-sub'>
            <div class='label-text'>📊 預估總花費</div>
            <div class='value-text-main'>TWD {total_spent:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        remaining = total_budget - total_spent
        remaining_color = ACCENT_COLOR if remaining < 0 else TEXT_COLOR
        st.markdown(f"""
        <div class='metric-card-sub'>
            <div class='label-text'>💵 剩餘預算</div>
            <div style='color: {remaining_color}; font-size: 1.5em; font-weight: bold;'>TWD {remaining:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

def render_unified_ticker_panel(results_list):
    """
    渲染單一整合面板：將價格輸入、核心結果和詳細明細融合在一起。
    """
    st.markdown("<div class='card-section-header'>🔥 標的物 - 價格設定與買入建議</div>", unsafe_allow_html=True)
    st.caption("💬 請在 **價格 (TWD)** 欄位輸入您想測試的數字。結果會即時更新。")
    
    for item in results_list:
        code = item['標的代號']
        
        # --- Ticker Row Container (微卡片) ---
        st.markdown("<div class='ticker-row-container'>", unsafe_allow_html=True)
        
        # 1. 頂部：標的/比例/價格輸入 (3欄)
        input_cols = st.columns(3)
        
        # Col 1: Ticker Value & Weight
        with input_cols[0]:
            st.markdown(f"""
            <div class='label-text'>標的代號 ({item['比例']})</div>
            <div class='value-text-main' style='color: {PRIMARY_COLOR}; font-size: 1.3em;'>{code}</div>
            """, unsafe_allow_html=True)

        # Col 2: Current Price
        with input_cols[1]:
            st.markdown("<div class='label-text'>當前價格 (TWD)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='value-text-regular' style='color: {LABEL_COLOR};'>{item['價格']:,.2f}</div>", unsafe_allow_html=True)

        # Col 3: Editable Price Input (Testing)
        with input_cols[2]:
            st.markdown("<div class='label-text'>測試價格 (TWD)</div>", unsafe_allow_html=True)
            # 從 session state 讀取可編輯價格
            price_value = st.session_state.editable_prices.get(code, 0.01)
            new_price = st.number_input(
                label=f"Price_Input_Test_{code}",
                min_value=0.01,
                value=price_value,
                step=0.01,
                format="%.2f",
                key=f"price_input_{code}",
                label_visibility="collapsed"
            )
            # 更新 session state
            st.session_state.editable_prices[code] = new_price
            
        # --- 分隔線 ---
        st.markdown("<hr style='margin: 0.8rem 0; border-top: 1px dashed rgba(255, 255, 255, 0.1);'>", unsafe_allow_html=True)

        # 2. 底部：建議結果與詳細明細 (5欄)
        result_cols = st.columns(5) 
        
        # Col 1: 建議股數 (結果核心)
        with result_cols[0]:
            st.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>建議股數</div>
                <div class='value-text-highlight'>{item['建議股數']}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Col 2: 總成本
        with result_cols[1]:
            st.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>總成本</div>
                <div class='value-text-regular'>TWD {item['總成本']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Col 3: 分配預算
        with result_cols[2]:
            st.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>分配預算</div>
                <div class='value-text-regular'>TWD {item['分配金額']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Col 4: 預估手續費
        with result_cols[3]:
            st.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>手續費</div>
                <div class='value-text-regular'>TWD {item['預估手續費']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Col 5: 實際價格 (來自輸入/session state)
        with result_cols[4]:
            st.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>計算價格</div>
                <div class='value-text-regular'>TWD {st.session_state.editable_prices.get(code, 0.01):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        # --- Ticker Row Container 結束 ---
        st.markdown("</div>", unsafe_allow_html=True)

# ========== 頁面主體邏輯 ==========

st.title("📈 零股投資分配計算機 (第100次極致優化版)")

# 獲取價格
with st.spinner('正在從 Yahoo Finance 獲取最新報價...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)

# --- NEW: 初始化 Session State 以管理可編輯價格 ---
if 'editable_prices' not in st.session_state:
    st.session_state.editable_prices = current_prices.copy()

# -------------------- Sidebar 參數設定 --------------------
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
    step=0.000001,
    format="%.6f"
)
st.sidebar.caption(f"💡 手續費最低 {MIN_FEE} 元 / 筆。請使用 **小數** 格式輸入。")

# --- 應用程式主體：單一卡片開始 ---
st.markdown("<div class='metric-card-main'>", unsafe_allow_html=True)

# 1. 報價資訊
st.info(f"📍 報價更新時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')} (價格資料每 60 秒自動更新一次)")

# ========== 構造 DataFrame for Calculation (從 Session State 讀取數據) ==========
data_for_calc = {
    "標的代號": list(TICKER_MAP.keys()),
    "設定比例": [ALLOCATION_WEIGHTS[code] for code in TICKER_MAP.keys()],
    "當前價格 (自動獲取)": [st.session_state.editable_prices[code] for code in TICKER_MAP.keys()]
}
edited_df = pd.DataFrame(data_for_calc)

# ========== 計算（基於編輯後的數據）==========
results_list, total_spent = calculate_investment(edited_df, total_budget, fee_rate)

# 2. 總預算總覽 (Budget Metrics)
st.markdown("<div class='card-section-header'>💰 投資預算總覽</div>", unsafe_allow_html=True)
render_budget_metrics(total_budget, total_spent)

# 3. 統一結果面板 (Input + Results + Details)
render_unified_ticker_panel(results_list)

# 4. 邏輯說明
st.markdown(f"<div style='margin-top: 1.5rem; color: {LABEL_COLOR}; font-size: 0.9em;'>📌 計算邏輯：優先確保買入股數最大化，且總花費不超過分配預算；手續費最低 {MIN_FEE} 元計算。</div>", unsafe_allow_html=True)

# --- 應用程式主體：單一卡片結束 ---
st.markdown("</div>", unsafe_allow_html=True)
