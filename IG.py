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
SUCCESS_COLOR = "#32CD32"   # 成功綠 (剩餘預算 > 0)
TEXT_COLOR = "#ffffff"      # 白色 (內容文字)
LABEL_COLOR = "#A9A9A9"     # 灰色 (標籤文字)
BACKGROUND_COLOR = "#1f2023" # 深灰 (應用主體背景)

# 投資標的與對應的 Yahoo Finance 代號
TICKER_MAP = {
    "009813": "009813.TW",
    "0050": "0050.TW",
    "00878": "00878.TW",
}
# 預設分配權重 (用於初始化 session state)
DEFAULT_WEIGHTS = {
    "009813": 50,
    "0050": 30,
    "00878": 20
}
FEE_RATE_DEFAULT = 0.001425 # 預設費率 (0.1425%)
MIN_FEE = 1                 # 最低手續費 (TWD)

# --- 0. CSS 注入：深色模式與客製化主題 (優化對齊和顏色) ---

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

/* Unit Card Container (單一標的物配置區塊) - R9 視覺強化 */
.unit-card-container {{
    margin-bottom: 1.5rem;
    padding: 1rem;
    border-radius: 8px;
    background: #252528; 
    border: 2px solid rgba(250, 128, 114, 0.6); /* 強化邊框 */
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

/* R4 - 剩餘預算顏色類別 */
.value-text-positive {{
    color: {SUCCESS_COLOR}; /* 成功綠 */
    font-size: 1.5em; 
    font-weight: bold;
}}
.value-text-negative {{
    color: {ACCENT_COLOR}; /* 超支警告色 */
    font-size: 1.5em; 
    font-weight: bold;
}}
.value-text-zero {{
    color: {PRIMARY_COLOR}; /* 完美匹配色 */
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

/* --- st.number_input 的樣式優化 (R7: 對齊修正) --- */

.stNumberInput label {{
    display: none !important;
}}

.stNumberInput > div > div {{
    background-color: #3f4045; 
    border: 1px solid {ACCENT_COLOR}; /* 強調邊框 */
    border-radius: 4px;
}}

/* R7 核心對齊修正 */
.stNumberInput {{
    margin-top: -5px; 
    /* 確保輸入框與同一行的文字元素垂直對齊 */
}}
.stSidebar .stNumberInput {{
    margin-top: 0px; /* 側邊欄不需要 -5px 修正 */
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

/* R2: 動態權重輸入框視覺修正 */
.stSidebar .stSlider label, .stSidebar .stNumberInput label {{
    color: {TEXT_COLOR} !important;
    font-size: 1.0em !important;
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
        # R5: 確保錯誤發生時所有價格都是 0，並在主介面提示
        print("⚠️ 無法獲取行情數據，所有價格已設為 0。")
        for code in ticker_map.keys():
            prices[code] = 0.0
            
    return prices, fetch_time

def calculate_investment(weights, total_budget, fee_rate):
    """
    計算零股投資分配結果。
    R1/R8 邏輯修正: 僅處理計算，將格式化留給渲染層。
    """
    results_list = []
    total_spent = 0.0
    
    # R2: 使用動態權重
    codes = list(weights.keys())
    
    for code in codes:
        # 權重必須轉換為小數比例 (e.g., 50 -> 0.5)
        weight = weights[code] / 100.0
        price = st.session_state.editable_prices.get(code, 0.01) # 使用用戶輸入/模擬價格
        allocated_budget = total_budget * weight
        
        shares_to_buy = 0
        estimated_fee = 0
        total_cost = 0.0
        
        if price > 0 and allocated_budget > 0:
            # 1. 計算可買入的理論最大股數
            shares_to_buy = int(allocated_budget / (price * (1 + fee_rate)))
            
            if shares_to_buy <= 0:
                shares_to_buy = 0
            
            if shares_to_buy > 0:
                # 2. 計算該股數下的費用和總成本
                fee_calculated = price * shares_to_buy * fee_rate
                estimated_fee = max(MIN_FEE, round(fee_calculated))
                total_cost = (shares_to_buy * price) + estimated_fee
            
                # 3. 健壯性檢查：如果總成本超過分配預算，則減少一股
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

        # R1 修正：移除 if total_cost > allocated_budget: total_cost = allocated_budget
        
        total_spent += total_cost
        results_list.append({
            "標的代號": code,
            "比例_raw": weights[code], # R8: 傳遞原始百分比數值
            "價格": price, 
            "分配金額": allocated_budget,
            "建議股數": shares_to_buy,
            "預估手續費": estimated_fee,
            "總成本": total_cost,
        })
        
    return results_list, total_spent

def _render_metric_box(label, value, value_class="value-text-regular", unit="", border_color=""):
    """R6: 輔助函式，渲染單個結果指標卡片"""
    border_style = f"border-left: 3px solid {border_color};" if border_color else ""
    return f"""
    <div class='metric-card-detail' style='{border_style}'>
        <div class='label-text'>{label}</div>
        <div class='{value_class}'>{value:,} <span class='unit-suffix'>{unit}</span></div>
    </div>
    """

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
        
        # R4: 剩餘預算顏色判斷
        if remaining > 0:
            remaining_class = "value-text-positive"
        elif remaining < 0:
            remaining_class = "value-text-negative"
        else:
            remaining_class = "value-text-zero"

        st.markdown(f"""
        <div class='metric-card-sub'>
            <div class='label-text'>💵 剩餘預算</div>
            <div class='{remaining_class}'>TWD {remaining:,.0f}</div>
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
        original_price = original_prices.get(code, 0.0)
        testing_price = item['價格']
        
        # --- Unit Card Container (R9: 視覺強化) ---
        st.markdown("<div class='unit-card-container'>", unsafe_allow_html=True)
        
        # Row 1: 輸入與配置 Context (4 Columns)
        input_cols = st.columns([1.5, 2, 2.5, 2]) 
        
        # Col 1: 標的代號與權重
        with input_cols[0]:
            st.markdown(f"""
            <div class='label-text' style='color: {PRIMARY_COLOR};'>標的代號 ({item['比例_raw']}%)</div>
            <div class='value-text-main' style='color: {TEXT_COLOR}; font-size: 1.3em;'>{code}</div>
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
            st.markdown(_render_metric_box(
                label="✅ 建議買入股數",
                value=item['建議股數'],
                value_class="value-text-highlight",
                unit="股",
                border_color=ACCENT_COLOR
            ), unsafe_allow_html=True)
        
        # Col 2: 總成本
        with result_cols[1]:
            st.markdown(_render_metric_box(
                label="預估總成本",
                value=item['總成本'],
                unit="TWD"
            ), unsafe_allow_html=True)
        
        # Col 3: 預估手續費
        with result_cols[2]:
            st.markdown(_render_metric_box(
                label="預估手續費",
                value=item['預估手續費'],
                unit="TWD"
            ), unsafe_allow_html=True)
        
        # Col 4: 計算使用的價格
        with result_cols[3]:
            st.markdown(_render_metric_box(
                label="實際計算價格",
                value=testing_price,
                unit="TWD"
            ), unsafe_allow_html=True)

        # --- Unit Card Container 結束 ---
        st.markdown("</div>", unsafe_allow_html=True)

# ========== 頁面主體邏輯 ==========

st.title("📊 零股投資分配模擬器")

# 獲取價格
with st.spinner('正在獲取最新報價數據...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)

# --- 初始化 Session State (R2: 動態權重 / R3: 可編輯價格) ---
if 'editable_prices' not in st.session_state:
    st.session_state.editable_prices = current_prices.copy()
if 'allocation_weights' not in st.session_state:
    st.session_state.allocation_weights = DEFAULT_WEIGHTS.copy()


# -------------------- Sidebar 參數設定 --------------------
st.sidebar.header("⚙️ 投資參數設定")

# R2: 動態權重配置
st.sidebar.subheader("⚖️ 分配權重設定 (%)")
codes = list(TICKER_MAP.keys())
total_input_weight = 0
weight_inputs = {}

# 1. 允許使用者調整 N-1 個權重
for i, code in enumerate(codes[:-1]):
    weight = st.sidebar.number_input(
        f"[{code}] 權重 (%)",
        min_value=0,
        max_value=100,
        value=st.session_state.allocation_weights.get(code, DEFAULT_WEIGHTS[code]),
        step=5,
        key=f"weight_input_{code}"
    )
    weight_inputs[code] = weight
    total_input_weight += weight

# 2. 自動計算最後一個權重
last_code = codes[-1]
remaining_weight = max(0, 100 - total_input_weight)
weight_inputs[last_code] = remaining_weight

st.sidebar.markdown(f"""
<div style='background-color: #3f4045; border: 1px solid {PRIMARY_COLOR}; padding: 10px; border-radius: 4px; margin-bottom: 10px;'>
    <div style='color: {LABEL_COLOR}; font-size: 0.9em; margin-bottom: 5px;'>[{last_code}] 剩餘權重 (%)</div>
    <div style='color: {PRIMARY_COLOR}; font-size: 1.2em; font-weight: bold;'>{remaining_weight}%</div>
</div>
""", unsafe_allow_html=True)
st.session_state.allocation_weights = weight_inputs # 更新 Session State

# --- 主要預算與費率 ---
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

# 1. 報價資訊 (R5: API 錯誤處理)
prices_ok = all(price > 0 for price in current_prices.values())
if not prices_ok:
    st.error("⚠️ 價格獲取失敗！所有報價已設為 0。計算結果將僅基於您手動輸入的「模擬買入價格」。")
    st.info(f"📍 報價上次更新時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')}")
else:
    st.info(f"📍 報價更新時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')} (價格資料每 60 秒自動更新一次)")

# 2. 模擬功能按鈕 (R3: 價格重設)
def reset_prices():
    """將模擬價格重設為即時價格"""
    st.session_state.editable_prices = current_prices.copy()

if st.button("🔄 重設模擬價格為即時報價", help="將下方所有模擬買入價格還原為目前即時獲取的報價"):
    reset_prices()
    st.rerun()

# ========== 計算（基於編輯後的數據）==========
# R2: 使用動態權重
results_list, total_spent = calculate_investment(
    st.session_state.allocation_weights,
    total_budget, 
    fee_rate
)

# 3. 總預算總覽
st.markdown("<div class='card-section-header'>💰 投資預算總覽</div>", unsafe_allow_html=True)
render_budget_metrics(total_budget, total_spent)

# 4. 單位部署面板
# 將 Yahoo Finance 獲取的原始價格傳入，用於對比顯示
render_investment_units(results_list, current_prices)

# 5. 邏輯說明
st.markdown(f"<div style='margin-top: 1.5rem; color: {LABEL_COLOR}; font-size: 0.9em;'>📌 計算邏輯：優先確保買入股數最大化，**且總花費準確反映股數與費用**（R1 修正）；手續費最低 {MIN_FEE} 元計算。</div>", unsafe_allow_html=True)

# --- 應用程式主體：單一卡片結束 ---
st.markdown("</div>", unsafe_allow_html=True)
