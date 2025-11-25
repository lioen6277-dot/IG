import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time 

# 設定頁面配置 (必須放在腳本最頂端)
st.set_page_config(
    page_title="零股投資分配模擬器",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 顏色定義與常數 (鮭魚色主題) ---
PRIMARY_COLOR = "#FA8072"   # 鮭魚粉 (主要標題/邊框)
ACCENT_COLOR = "#E9967A"    # 深鮭色 (建議股數/強調數據)
TEXT_COLOR = "#ffffff"      # 白色 (內容文字)
LABEL_COLOR = "#A9A9A9"     # 灰色 (標籤文字)
BACKGROUND_COLOR = "#1f2023" # 深灰 (應用主體背景)

# 投資標的與對應的 Yahoo Finance 代號
TICKER_MAP = {
    "009813": "009813.TW",
    "0050": "0050.TW",
    "00878": "00878.TW",
}
# 預設分配權重 (總和為 1.0)
ALLOCATION_WEIGHTS = {
    "009813": 0.50,
    "0050": 0.30,
    "00878": 0.20
}
FEE_RATE_DEFAULT = 0.001425 # 預設費率 (0.1425%)
MIN_FEE = 1                 # 最低手續費 (TWD)

# --- 0. CSS 注入：深色模式與客製化主題 ---

st.markdown(f"""
<style>
/* -------------------- 應用程式全域設定 -------------------- */

.stApp {{
    font-size: 1.05rem; 
    color: {TEXT_COLOR};
    background-color: #0e1117; 
}}

/* -------------------- 標題樣式 -------------------- */
h1 {{
    font-size: 2.0em !important;
    color: {PRIMARY_COLOR} !important;
    font-weight: bold !important;
    margin-bottom: 0.5rem !important;
}}

/* -------------------- 單一卡片排版的核心調整 -------------------- */

/* Main Card - 應用主體容器 */
.metric-card-main {{
    background: {BACKGROUND_COLOR}; 
    border: 2px solid {PRIMARY_COLOR}; 
    border-radius: 12px;
    padding: 1.5rem; 
    margin-top: 1rem;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
}}

/* Sub Card (總覽指標卡片) */
.metric-card-sub {{
    background: rgba(255, 255, 255, 0.05); 
    border-radius: 6px;
    padding: 1rem;
    height: 100%; 
    margin-bottom: 0.5rem;
    border-left: 3px solid {PRIMARY_COLOR};
}}

/* Detail Card (結果指標卡片) */
.metric-card-detail {{
    background: #2b2b2e; 
    border-radius: 4px;
    padding: 0.6rem; 
    margin-bottom: 0.3rem;
}}

/* Unit Card Container (單一標的物配置區塊) */
.unit-card-container {{
    margin-bottom: 1.5rem;
    padding: 1rem;
    border-radius: 8px;
    background: #252528; 
    border: 1px solid rgba(250, 128, 114, 0.3); /* Salmon Border */
}}


/* Label text */
.label-text {{
    font-size: 0.9em;
    color: {LABEL_COLOR};
    font-weight: 500;
    margin-bottom: 0.2rem;
    line-height: 1.2;
    text-transform: uppercase;
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

/* Value text - Highlighted style for Shares (建議股數) */
.value-text-highlight {{
    color: {ACCENT_COLOR}; 
    font-size: 1.8em; 
    font-weight: bold;
    text-shadow: 0 0 5px rgba(233, 150, 122, 0.5); /* 鮭魚色光暈 */
}}

/* Card Section Header (內部區塊標題) */
.card-section-header {{
    color: {PRIMARY_COLOR};
    font-weight: bold;
    font-size: 1.4em;
    padding: 0.5rem 0;
    margin-top: 2rem;
    margin-bottom: 0.5rem;
    border-bottom: 1px solid {PRIMARY_COLOR}; 
}}

/* --- st.number_input 的樣式優化 --- */

.stNumberInput label {{
    display: none !important;
}}

.stNumberInput > div > div {{
    background-color: #3f4045; 
    border: 1px solid {ACCENT_COLOR};
    border-radius: 4px;
}}

.stNumberInput {{
    margin-top: -5px; 
}}

/* -------------------- 其他微調 -------------------- */
div[role="alert"] {{
    background-color: rgba(250, 128, 114, 0.15) !important; /* Salmon Background */
    border-left: 5px solid {PRIMARY_COLOR} !important; 
    color: {TEXT_COLOR} !important;
    font-size: 1.0em !important; 
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
}}

.stDivider {{
    display: none; 
}}

/* 數字後綴單位 */
.unit-suffix {{
    font-size: 0.8em;
    color: {LABEL_COLOR};
    margin-left: 5px;
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
        # 嘗試下載數據
        data = yf.download(tickers, period="1d", interval="1m", progress=False, timeout=5)
        
        for code, ticker in ticker_map.items():
            try:
                if not data.empty and ticker in data['Close']:
                    price_series = data['Close'][ticker]
                    valid_prices = price_series.dropna()
                    if not valid_prices.empty:
                        # 取最新價格
                        price = valid_prices.iloc[-1]
                        prices[code] = round(price, 2)
                    else:
                        prices[code] = 0.0
                else:
                    prices[code] = 0.0
            except Exception:
                prices[code] = 0.0
    except Exception:
        # 如果下載失敗，設置所有價格為 0
        print("⚠️ 無法獲取行情數據，所有價格已設為 0。")
        for code in ticker_map.keys():
            prices[code] = 0.0
            
    return prices, fetch_time

def calculate_investment(edited_df, total_budget, fee_rate):
    """
    計算零股投資分配結果。
    """
    results_list = []
    total_spent = 0.0
    
    for _, row in edited_df.iterrows():
        code = row["標的代號"]
        weight = row["設定比例"]
        price = row["當前價格 (自動獲取)"] # 使用用戶輸入/即時價格
        allocated_budget = total_budget * weight
        
        shares_to_buy = 0
        estimated_fee = 0
        total_cost = 0.0
        
        if price > 0 and allocated_budget > 0:
            # 計算可買入的理論最大股數
            shares_to_buy = int(allocated_budget / (price * (1 + fee_rate)))
            
            if shares_to_buy < 0:
                shares_to_buy = 0
            
            if shares_to_buy > 0:
                # 計算該股數下的費用和總成本
                fee_calculated = price * shares_to_buy * fee_rate
                estimated_fee = max(MIN_FEE, round(fee_calculated))
                total_cost = (shares_to_buy * price) + estimated_fee
            
                # 健壯性檢查：如果總成本超過分配預算，則減少一股
                if total_cost > allocated_budget:
                    shares_to_buy -= 1
                    
                    if shares_to_buy > 0:
                        fee_recalculated = price * shares_to_buy * fee_rate
                        estimated_fee = max(MIN_FEE, round(fee_recalculated))
                        total_cost = (shares_to_buy * price) + estimated_fee
                    else:
                        # 股數歸零，成本和費用也歸零
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
    """渲染總預算指標卡片 (3欄) - 預算總覽"""
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
        remaining_color = ACCENT_COLOR if remaining < 0 else PRIMARY_COLOR
        st.markdown(f"""
        <div class='metric-card-sub'>
            <div class='label-text'>💵 剩餘預算</div>
            <div style='color: {remaining_color}; font-size: 1.5em; font-weight: bold;'>TWD {remaining:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

def render_investment_units(results_list, original_prices):
    """
    渲染單一標的物配置面板：融合來源報價、模擬輸入、分配預算與計算結果。
    """
    st.markdown("<div class='card-section-header'>🛒 投資標的配置與模擬</div>", unsafe_allow_html=True)
    st.caption("💬 請在 **模擬買入價格** 欄位調整價格，進行即時計算模擬。")
    
    for item in results_list:
        code = item['標的代號']
        original_price = original_prices.get(code, 0.0) # Yahoo Finance 獲取的原始價格
        testing_price = st.session_state.editable_prices.get(code, 0.01) # 用戶輸入或 Session State 中的價格
        
        # --- Unit Card Container ---
        st.markdown("<div class='unit-card-container'>", unsafe_allow_html=True)
        
        # Row 1: 輸入與配置 Context (4 Columns)
        input_cols = st.columns([1.5, 2, 2.5, 2]) 
        
        # Col 1: 標的代號與權重
        with input_cols[0]:
            st.markdown(f"""
            <div class='label-text'>標的代號 ({item['比例']})</div>
            <div class='value-text-main' style='color: {PRIMARY_COLOR}; font-size: 1.3em;'>{code}</div>
            """, unsafe_allow_html=True)

        # Col 2: 來源報價
        with input_cols[1]:
            st.markdown("<div class='label-text'>即時報價 (參考)</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='value-text-regular' style='color: {LABEL_COLOR};'>{original_price:,.2f} <span class='unit-suffix'>TWD</span></div>", unsafe_allow_html=True)

        # Col 3: 模擬價格輸入 (用戶可編輯)
        with input_cols[2]:
            st.markdown("<div class='label-text'>📝 模擬買入價格 (TWD)</div>", unsafe_allow_html=True)
            new_price = st.number_input(
                label=f"Price_Input_Test_{code}",
                min_value=0.01,
                value=testing_price, 
                step=0.01,
                format="%.2f",
                key=f"price_input_{code}",
                label_visibility="collapsed"
            )
            st.session_state.editable_prices[code] = new_price
        
        # Col 4: 分配預算
        with input_cols[3]:
            st.markdown("<div class='label-text'>💸 分配預算上限</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='value-text-regular'>TWD {item['分配金額']:,.0f}</div>", unsafe_allow_html=True)

            
        # --- 分隔線 ---
        st.markdown("<hr style='margin: 0.8rem 0; border-top: 1px dashed rgba(255, 255, 255, 0.1);'>", unsafe_allow_html=True)

        # Row 2: 結果指標 (4 Columns)
        result_cols = st.columns(4) 
        
        # Col 1: 建議股數 (高亮顯示)
        with result_cols[0]:
            st.markdown(f"""
            <div class='metric-card-detail' style='border-left: 3px solid {ACCENT_COLOR};'>
                <div class='label-text'>✅ 建議買入股數</div>
                <div class='value-text-highlight'>{item['建議股數']} <span class='unit-suffix' style='color: {ACCENT_COLOR};'>股</span></div>
            </div>
            """, unsafe_allow_html=True)
        
        # Col 2: 總成本
        with result_cols[1]:
            st.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>預估總成本 (TWD)</div>
                <div class='value-text-regular'>{item['總成本']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Col 3: 預估手續費
        with result_cols[2]:
            st.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>預估手續費 (TWD)</div>
                <div class='value-text-regular'>{item['預估手續費']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Col 4: 計算使用的價格
        with result_cols[3]:
            st.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>實際計算價格</div>
                <div class='value-text-regular'>{testing_price:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        # --- Unit Card Container 結束 ---
        st.markdown("</div>", unsafe_allow_html=True)

# ========== 頁面主體邏輯 ==========

st.title("📊 零股投資分配模擬器")

# 獲取價格
with st.spinner('正在獲取最新報價數據...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)

# --- 初始化 Session State (確保可編輯價格存在) ---
if 'editable_prices' not in st.session_state:
    st.session_state.editable_prices = current_prices.copy()

# -------------------- Sidebar 參數設定 --------------------
st.sidebar.header("⚙️ 投資參數設定")
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
    # 使用 session state 中的 "模擬價格" 進行計算
    "當前價格 (自動獲取)": [st.session_state.editable_prices[code] for code in TICKER_MAP.keys()]
}
edited_df = pd.DataFrame(data_for_calc)

# ========== 計算（基於編輯後的數據）==========
results_list, total_spent = calculate_investment(edited_df, total_budget, fee_rate)

# 2. 總預算總覽
st.markdown("<div class='card-section-header'>💰 投資預算總覽</div>", unsafe_allow_html=True)
render_budget_metrics(total_budget, total_spent)

# 3. 單位部署面板
# 將 Yahoo Finance 獲取的原始價格傳入，用於對比顯示
render_investment_units(results_list, current_prices)

# 4. 邏輯說明
st.markdown(f"<div style='margin-top: 1.5rem; color: {LABEL_COLOR}; font-size: 0.9em;'>📌 計算邏輯：優先確保買入股數最大化，且總花費不超過分配預算；手續費最低 {MIN_FEE} 元計算。</div>", unsafe_allow_html=True)

# --- 應用程式主體：單一卡片結束 ---
st.markdown("</div>", unsafe_allow_html=True)
