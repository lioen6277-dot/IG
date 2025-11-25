import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# --- 星海爭霸 - 泰倫風格命名 ---
TACC_TITLE_TEXT = "泰倫戰術指揮中心 (T.A.C.C.)"

# 資金/預算類
TOTAL_CAPITAL_LABEL = "💰 總戰備資金 (Total War Chest)"
ESTIMATED_COST_LABEL = "📊 預計軍備開支 (Estimated Expenditure)"
REMAINING_FUNDS_LABEL = "現存資金餘額 (Remaining Funds)"
RESOURCE_READINESS_HEADER = "💰 資源戰備總覽 (Resource Readiness)"
BUDGET_SIDEBAR_HEADER = "⚙️ 資源調度指揮站"
BUDGET_INPUT_LABEL = "每月行動預算 (TWD)"
FEE_RATE_INPUT_LABEL = "輸送燃料費率 (0.xxxx)"
MIN_FEE_CAPTION = "💡 最低燃料費為 **{MIN_FEE}** 元 / 筆。請使用 **小數** 格式輸入。"

# 部署/結果類
DEPLOYMENT_HEADER = "✨ 軍事單位部署指令 (Unit Deployment Order)"
RECOMMENDED_UNITS_LABEL = "建議生產單位數 (Recommended Units)"
TOTAL_DEPLOYMENT_COST_LABEL = "部署總開支 (Total Deployment Cost)"
TARGET_FUND_ALLOCATION_LABEL = "目標資金配給 (Target Fund Allocation)"
UNIT_COST_LABEL = "單位造價 (Unit Cost)"
LOGISTICS_FEE_LABEL = "輸送燃料費 (Logistics Fee)"
DEPLOYMENT_TARGET_LABEL = "🛡️ 部署目標: {code} ({ratio})"
DEPLOYMENT_PRINCIPLE_FOOTER = "📌 T.A.C.C. 部署原則：優先確保買入單位數最大化，且總成本 **嚴格不超過** 分配預算。交易燃料費最低 {MIN_FEE} 元計算。"

# 設定/數據類
CALIBRATION_HEADER = "⚙️ 戰術數據校準 (Calibration Data)"
TARGET_DESIGNATION_LABEL = "🎯 戰場目標代號"
STRATEGIC_RATIO_LABEL = "戰略配置比例"
DEFAULT_UNIT_COST_LABEL = "預設造價單價 (TWD)"
DATA_SYNC_SPINNER = '正在從聯邦情報網絡獲取最新戰術報價...'
DATA_SYNC_INFO = "🌐 數據鏈同步時間：{fetch_time} (戰術報價資訊每 60 秒自動刷新)"
DATA_FETCH_WARNING = "⚠️ 警告：戰術報價數據鏈中斷，所有價格已設為 0。請手動輸入造價以進行準確計算！"


st.set_page_config(
    page_title=TACC_TITLE_TEXT,
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 顏色定義與常數 (V17 - 泰倫風格) ---
MAIN_COLOR = "#cf6955"    # 深珊瑚紅/鐵鏽紅 (核心主色，用於標題, 邊框)
ACCENT_COLOR = "#e9967a"  # 淺珊瑚紅/鮭魚色 (強調色，用於建議股數, 剩餘資本高亮)
TEXT_COLOR = "#ffffff"
LABEL_COLOR = "#b0b0b0"
DARK_BG = "#1a1a1a"
TILE_BG = "#1e2126" # 次級卡片/磁磚背景色

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
FEE_RATE_DEFAULT = 0.001425
MIN_FEE = 1

# --- 0. CSS 注入：字體微調與統一主題 (V17) ---

st.markdown(f"""
<style>
/* -------------------- 應用程式全域設定 -------------------- */
.stApp {{
    font-size: 1.05rem;
    color: {TEXT_COLOR};
    background-color: #0e1117; 
}}

/* -------------------- 標題樣式 (新主色) -------------------- */
h1 {{
    font-size: 2.2em !important;
    color: {MAIN_COLOR} !important;
    font-weight: bold !important;
    margin-bottom: 0.5rem !important;
    text-shadow: 0 0 5px rgba(207, 105, 85, 0.5);
    padding-top: 1rem; 
}}

/* -------------------- 次級卡片 (Metric Tile) 樣式 -------------------- */
/* 用於所有數據指標 (總覽與細項) 的標準背景磁磚 */
.sub-card-tile {{
    background: {TILE_BG}; 
    border-radius: 8px;
    padding: 1.2rem; 
    height: 100%;
    margin-bottom: 1rem; 
    transition: all 0.2s ease-in-out;
    border: 1px solid rgba(255, 255, 255, 0.05); 
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2); 
}}

/* 建議股數 (Purchase Recommendation) 專用強調磁磚 */
.highlight-tile {{
    background: {TILE_BG}; 
    border-radius: 8px;
    padding: 1.2rem; 
    height: 100%;
    margin-bottom: 1rem;
    
    /* 強調色邊框 */
    border: 2px solid {ACCENT_COLOR}; 
    /* 強調色陰影 */
    box-shadow: 0 0 15px rgba(233, 150, 122, 0.5); 
}}

/* -------------------- 文字與數值樣式 V17 -------------------- */
.label-text {{
    font-size: 0.9em; 
    color: {LABEL_COLOR};
    font-weight: 500;
    margin-bottom: 0.5rem;
    line-height: 1.2;
    text-transform: uppercase;
}}

/* 標準數值：用於總覽和非重點的細項 */
.value-text-regular {{
    color: {TEXT_COLOR};
    font-size: 1.7em; 
    font-weight: bold;
}}

/* 強調數值：用於建議股數 */
.value-text-highlight {{
    color: {ACCENT_COLOR}; 
    font-size: 2.3em; 
    font-weight: 900;
    text-shadow: 0 0 8px rgba(233, 150, 122, 0.5);
    line-height: 1; 
}}

/* 剩餘彈藥數值 */
.value-text-remaining {{
    font-size: 1.7em; 
    font-weight: bold;
    line-height: 1.2;
}}

/* -------------------- 戰術參數設定卡片內數值 -------------------- */
.value-text-setting {{
    color: {TEXT_COLOR};
    font-size: 1.4em; 
    font-weight: 700;
    margin-top: 0.25rem;
}}

/* Section Header (主色風格標頭) */
.card-section-header {{
    color: {MAIN_COLOR};
    font-weight: bold;
    font-size: 1.4em;
    padding: 0.7rem 0 0.7rem 0.5rem; 
    margin-top: 1.5rem; 
    margin-bottom: 0.8rem;
    border-bottom: 2px solid {MAIN_COLOR};
    text-transform: uppercase;
}}

/* 標的組標頭 (Accent Color) */
.ticker-group-header-sc {{
    color: {ACCENT_COLOR};
    font-weight: 600;
    font-size: 1.1em;
    padding: 0.5rem 0 0.5rem 0.5rem;
    margin-top: 1.5rem; 
    margin-bottom: 0.8rem;
    border-bottom: 1px dashed rgba(233, 150, 122, 0.5);
}}

/* --- 專門針對 st.number_input 的樣式優化 V17 --- */
.stNumberInput > div > div {{
    background-color: #2e2e2e; 
    border: none;
    border-radius: 6px;
    padding: 0.5rem;
    transition: all 0.2s ease;
}}
.stNumberInput > div > div:focus-within {{
    background-color: #242424; 
    border: 1px solid {ACCENT_COLOR} !important;
    box-shadow: 0 0 7px rgba(233, 150, 122, 0.7); 
}}
/* 輸入欄位字體大小 */
.stNumberInput input {{
    color: {ACCENT_COLOR} !important;
    font-weight: bold;
    font-size: 1.3em; 
}}

/* -------------------- 其他微調 -------------------- */
div[role="alert"] {{
    background-color: rgba(207, 105, 85, 0.15) !important;
    border-left: 5px solid {MAIN_COLOR} !important;
    color: {TEXT_COLOR} !important;
    font-size: 1.0em !important;
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
    padding-left: 1rem; 
}}

/* Sidebar 優化 */
.stSidebar > div:first-child {{
    background-color: {DARK_BG};
    border-right: 2px solid {MAIN_COLOR};
}}
.stSidebar h2 {{
    color: {MAIN_COLOR} !important;
    border-bottom: 1px solid rgba(207, 105, 85, 0.5);
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
}}
.stSidebar .stNumberInput label p {{
    color: {LABEL_COLOR} !important;
    font-weight: 500;
}}
.stSidebar .stCaption {{
    color: {LABEL_COLOR} !important;
    font-size: 0.8em;
}}

</style>
""", unsafe_allow_html=True)


# --- 2. 核心函式 (無變動) ---

@st.cache_data(ttl=60)
def get_current_prices(ticker_map):
    prices = {}
    fetch_time = datetime.now()
    tickers = list(ticker_map.values())

    for code in ticker_map.keys():
        prices[code] = 0.0

    try:
        # 下載數據邏輯...
        data = yf.download(tickers, period="1d", interval="1m", progress=False, timeout=8)

        if data.empty:
             return prices, fetch_time

        for code in ticker_map.keys():
            ticker = ticker_map[code]
            try:
                close_data = data['Close']

                if isinstance(close_data, pd.DataFrame):
                    if ticker in close_data.columns:
                        price_series = close_data[ticker]
                        valid_prices = price_series.dropna()
                        if not valid_prices.empty:
                            prices[code] = round(valid_prices.iloc[-1], 2)
                elif isinstance(close_data, pd.Series):
                    if ticker == tickers[0] and len(tickers) == 1: # 處理單一標的下載
                         valid_prices = close_data.dropna()
                         if not valid_prices.empty:
                             prices[code] = round(valid_prices.iloc[-1], 2)

            except Exception:
                prices[code] = 0.0

    except Exception:
        pass

    return prices, fetch_time

def calculate_investment(edited_df, total_budget, fee_rate, min_fee):
    results_list = []
    total_spent = 0.0

    for _, row in edited_df.iterrows():
        # 變量名稱不變，但代表的含義已轉為星海風格
        code = row["標的代號"]
        weight = row["設定比例"]
        price = row["當前價格 (自動獲取)"] 
        allocated_budget = total_budget * weight

        shares_to_buy = 0
        estimated_fee = 0
        total_cost = 0.0

        if price <= 0.0001 or allocated_budget <= 0:
            results_list.append({
                "標的代號": code,
                "比例": f"{weight*100:.0f}%",
                "價格": price,
                "分配金額": allocated_budget,
                "建議股數": 0,
                "預估手續費": 0,
                "總成本": 0.0,
            })
            continue

        max_shares_theoretical = int(allocated_budget / price)
        shares = 0

        for s in range(max_shares_theoretical, -1, -1):
            if s == 0:
                shares = 0
                break

            trade_value = s * price
            fee_calculated = trade_value * fee_rate
            current_fee = max(min_fee, round(fee_calculated))
            current_cost = trade_value + current_fee

            if current_cost <= allocated_budget:
                shares = s
                estimated_fee = current_fee
                total_cost = current_cost
                break

        shares_to_buy = shares

        total_spent += total_cost
        results_list.append({
            "標的代號": code,
            "比例": f"{weight*100:.0f}%",
            "價格": price,
            "分配金額": allocated_budget,
            "建議股數": shares_to_buy,
            "預估手續費": estimated_fee,
            "總成本": round(total_cost, 2),
        })

    return results_list, round(total_spent, 2)

def render_budget_metrics(total_budget, total_spent):
    """渲染總預算指標卡片 (3欄，使用 sub-card-tile 樣式) - 泰倫風格 (V16: 移除小數點)"""
    global RESOURCE_READINESS_HEADER, TOTAL_CAPITAL_LABEL, ESTIMATED_COST_LABEL, REMAINING_FUNDS_LABEL, ACCENT_COLOR, MAIN_COLOR
    
    st.markdown(f"<div class='card-section-header'>{RESOURCE_READINESS_HEADER}</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    # 計算剩餘資金 (四捨五入到整數，用於顯示)
    remaining = total_budget - total_spent
    remaining_display = round(remaining) # 移除小數點
    total_spent_display = round(total_spent) # 移除小數點

    remaining_color = ACCENT_COLOR if remaining > 0 else MAIN_COLOR
    remaining_icon = "✅" if remaining > 0 else "⚠️"

    with col1:
        st.markdown(f"""
        <div class='sub-card-tile'>
            <div class='label-text'>{TOTAL_CAPITAL_LABEL}</div>
            <div class='value-text-regular'>TWD {total_budget:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='sub-card-tile'>
            <div class='label-text'>{ESTIMATED_COST_LABEL}</div>
            <div class='value-text-regular'>TWD {total_spent_display:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='sub-card-tile'>
            <div class='label-text'>{remaining_icon} {REMAINING_FUNDS_LABEL}</div>
            <div class='value-text-remaining' style='color: {remaining_color};'>TWD {remaining_display:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

def render_ticker_results_and_breakdown(results_list):
    """渲染每檔股票的關鍵投資建議 (5 欄) - 泰倫風格 (V17: 調整欄位順序)"""
    global DEPLOYMENT_HEADER, RECOMMENDED_UNITS_LABEL, TOTAL_DEPLOYMENT_COST_LABEL, TARGET_FUND_ALLOCATION_LABEL, UNIT_COST_LABEL, LOGISTICS_FEE_LABEL, DEPLOYMENT_TARGET_LABEL
    
    st.markdown(f"<div class='card-section-header'>{DEPLOYMENT_HEADER}</div>", unsafe_allow_html=True)

    for item in results_list:
        st.markdown(f"<div class='ticker-group-header-sc'>{DEPLOYMENT_TARGET_LABEL.format(code=item['標的代號'], ratio=item['比例'])}</div>", unsafe_allow_html=True)

        # 部署總開支 (Total Deployment Cost) 顯示回兩位小數 (因為單一項目比較精確)
        total_cost_display = item['總成本']

        # 定義 5 個指標的顯示配置 - V17 順序調整
        metrics = [
            # 1. 建議生產單位數
            (RECOMMENDED_UNITS_LABEL, item['建議股數'], "highlight"),
            # 2. 單位造價
            (UNIT_COST_LABEL, f"TWD {item['價格']:,.2f}", "regular"),
            # 3. 部署總開支 (單獨項目保留兩位小數)
            (TOTAL_DEPLOYMENT_COST_LABEL, f"TWD {total_cost_display:,.2f}", "regular"), 
            # 4. 目標資金配給 (分配金額保持整數或零位小數)
            (TARGET_FUND_ALLOCATION_LABEL, f"TWD {item['分配金額']:,.0f}", "regular"),
            # 5. 輸送燃料費
            (LOGISTICS_FEE_LABEL, f"TWD {item['預估手續費']:,.0f}", "regular"),
        ]

        # 渲染 5 欄
        col1, col2, col3, col4, col5 = st.columns(5)
        for i, (label, value, style_type) in enumerate(metrics):
            with [col1, col2, col3, col4, col5][i]:
                tile_class = 'highlight-tile' if style_type == 'highlight' else 'sub-card-tile'
                value_class = 'value-text-highlight' if style_type == 'highlight' else 'value-text-regular'
                
                st.markdown(f"""
                <div class='{tile_class}'>
                    <div class='label-text'>{label}</div>
                    <div class='{value_class}'>{value}</div>
                </div>
                """, unsafe_allow_html=True)


def render_ticker_settings(ticker_map, allocation_weights, prices_ready=True):
    """
    渲染可編輯的造價與比例面板 (卡片化) - 泰倫風格。
    """
    global CALIBRATION_HEADER, DATA_FETCH_WARNING, TARGET_DESIGNATION_LABEL, STRATEGIC_RATIO_LABEL, DEFAULT_UNIT_COST_LABEL, MAIN_COLOR
    
    st.markdown(f"<div class='card-section-header'>{CALIBRATION_HEADER}</div>", unsafe_allow_html=True)

    if not prices_ready:
        st.warning(DATA_FETCH_WARNING)

    for code in ticker_map.keys():
        weight = allocation_weights[code]
        price_value = st.session_state.editable_prices.get(code, 0.01)

        # Start of the card structure
        st.markdown("<div class='sub-card-tile'>", unsafe_allow_html=True)
        
        # 使用 columns inside the card for layout
        col_code, col_weight, col_price = st.columns([1.5, 1, 2.5])

        with col_code:
            # Ticker Code (Label + Value)
            st.markdown(f"""
                <div class='label-text' style='color: {MAIN_COLOR}; margin-bottom: 0;'>{TARGET_DESIGNATION_LABEL}</div>
                <div class='value-text-setting' style='margin-top: 0.25rem;'>{code}</div>
            """, unsafe_allow_html=True)

        with col_weight:
            # Weight (Fixed Value)
            st.markdown(f"""
                <div class='label-text' style='margin-bottom: 0;'>{STRATEGIC_RATIO_LABEL}</div>
                <div class='value-text-setting' style='margin-top: 0.25rem;'>{weight*100:.0f}%</div>
            """, unsafe_allow_html=True)

        with col_price:
            # Price Input (Interactive) - 標籤單獨顯示
            st.markdown(f"<div class='label-text' style='margin-bottom: 0;'>{DEFAULT_UNIT_COST_LABEL}</div>", unsafe_allow_html=True)

            new_price = st.number_input(
                label=f"Price_Input_{code}",
                min_value=0.0001,
                value=price_value,
                step=0.01,
                format="%.2f",
                key=f"price_input_{code}",
                label_visibility="collapsed"
            )
            st.session_state.editable_prices[code] = new_price

        # End of the card structure
        st.markdown("</div>", unsafe_allow_html=True)


def check_allocation_sum(weights):
    """檢查分配比例總和是否為 1.0"""
    current_sum = sum(weights.values())
    return abs(current_sum - 1.0) < 1e-9

# ========== 頁面主體邏輯 ==========

st.title(TACC_TITLE_TEXT)

# 獲取價格
prices_ready = True
with st.spinner(DATA_SYNC_SPINNER):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)
    if all(p == 0.0 for p in current_prices.values()):
        prices_ready = False

# --- 初始化 Session State 以管理可編輯造價 ---
if 'editable_prices' not in st.session_state:
    st.session_state.editable_prices = current_prices.copy()
else:
    # 確保新獲取的價格更新到 state 中，除非用戶已經手動編輯過
    for code, price in current_prices.items():
        if f"price_input_{code}" not in st.session_state and st.session_state.editable_prices[code] != price:
             st.session_state.editable_prices[code] = price


# -------------------- Sidebar 參數設定 - 泰倫風格 --------------------
st.sidebar.header(BUDGET_SIDEBAR_HEADER)
total_budget = st.sidebar.number_input(
    BUDGET_INPUT_LABEL,
    min_value=100,
    value=30000,
    step=1000,
    format="%d"
)
fee_rate = st.sidebar.number_input(
    FEE_RATE_INPUT_LABEL,
    min_value=0.000001,
    max_value=0.01,
    value=FEE_RATE_DEFAULT,
    step=0.000001,
    format="%.6f"
)
st.sidebar.caption(MIN_FEE_CAPTION.format(MIN_FEE=MIN_FEE))

# 比例總和檢查
if not check_allocation_sum(ALLOCATION_WEIGHTS):
    st.sidebar.error("❌ 警告：所有標的分配比例總和不等於 100%。請修正 `ALLOCATION_WEIGHTS` 變量。")
    safe_weights = {k: v / sum(ALLOCATION_WEIGHTS.values()) for k, v in ALLOCATION_WEIGHTS.items()}
else:
    safe_weights = ALLOCATION_WEIGHTS

# 1. 報價資訊
st.info(DATA_SYNC_INFO.format(fetch_time=fetch_time.strftime('%Y-%m-%d %H:%M:%S')))

# 2. 價格與比例輸入 (Setting)
render_ticker_settings(TICKER_MAP, safe_weights, prices_ready)

# ========== 構造 DataFrame for Calculation ==========
data_for_calc = {
    "標的代號": list(TICKER_MAP.keys()),
    "設定比例": [safe_weights[code] for code in TICKER_MAP.keys()],
    "當前價格 (自動獲取)": [st.session_state.editable_prices[code] for code in TICKER_MAP.keys()]
}
edited_df = pd.DataFrame(data_for_calc)

# ========== 計算（基於編輯後的數據）==========
results_list, total_spent = calculate_investment(edited_df, total_budget, fee_rate, MIN_FEE)

# 3. 總預算總覽 (Budget Metrics)
render_budget_metrics(total_budget, total_spent)

# 4. 建議買入與詳細明細 (Results)
render_ticker_results_and_breakdown(results_list)

# 5. 邏輯說明
st.markdown(f"<div style='margin-top: 1.5rem; color: {LABEL_COLOR}; font-size: 0.9em; padding-left: 1rem;'>{DEPLOYMENT_PRINCIPLE_FOOTER.format(MIN_FEE=MIN_FEE)}</div>", unsafe_allow_html=True)
