import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

st.set_page_config(
    page_title="泰倫戰術資本部署介面 (T.C.D.I.)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 顏色定義與常數 (V12 - 字體放大優化) ---
MAIN_COLOR = "#cf6955"    # 深珊瑚紅/鐵鏽紅 (核心主色，用於標題, 邊框)
ACCENT_COLOR = "#e9967a"  # 淺珊瑚紅/鮭魚色 (強調色，用於建議股數, 剩餘資本高亮)
TEXT_COLOR = "#ffffff"
LABEL_COLOR = "#b0b0b0"
DARK_BG = "#1a1a1a"
TILE_BG = "#1e2126" # 次級卡片/磁磚背景色
TCDI_TITLE_TEXT = "泰倫戰術資本部署介面 (T.C.D.I.)"

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

# --- 0. CSS 注入：字體加大與統一主題 (V12) ---

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

/* -------------------- 次級卡片 (Metric Tile) 樣式 V12 -------------------- */
/* 用於所有數據指標 (總覽與細項) 的標準背景磁磚 */
.sub-card-tile {{
    background: {TILE_BG}; 
    border-radius: 8px;
    padding: 1.2rem; /* 增加內邊距以適應大字體 */
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
    padding: 1.2rem; /* 增加內邊距以適應大字體 */
    height: 100%;
    margin-bottom: 1rem;
    
    /* 強調色邊框 */
    border: 2px solid {ACCENT_COLOR}; 
    /* 強調色陰影 */
    box-shadow: 0 0 15px rgba(233, 150, 122, 0.5); 
}}

/* -------------------- 文字與數值樣式 V12 - 字體加大 -------------------- */
.label-text {{
    font-size: 0.9em; /* 標籤字體略微加大 */
    color: {LABEL_COLOR};
    font-weight: 500;
    margin-bottom: 0.5rem;
    line-height: 1.2;
    text-transform: uppercase;
}}

/* 標準數值：用於總覽和非重點的細項 */
.value-text-regular {{
    color: {TEXT_COLOR};
    font-size: 1.8em; /* 從 1.5em 放大到 1.8em */
    font-weight: bold;
}}

/* 強調數值：用於建議股數 */
.value-text-highlight {{
    color: {ACCENT_COLOR}; 
    font-size: 2.5em; /* 從 2.0em 放大到 2.5em */
    font-weight: 900;
    text-shadow: 0 0 8px rgba(233, 150, 122, 0.5);
    line-height: 1; /* 調整行高以避免數值頂部被截斷 */
}}

/* 剩餘彈藥數值 (使用 regular 大小，但調整顏色) */
.value-text-remaining {{
    font-size: 1.8em; 
    font-weight: bold;
    line-height: 1.2;
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

/* --- 專門針對 st.number_input 的樣式優化 --- */
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
.stNumberInput input {{
    color: {ACCENT_COLOR} !important;
    font-weight: bold;
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

        for code, ticker in ticker_map.items():
            try:
                close_data = data['Close']

                if isinstance(close_data, pd.DataFrame):
                    if ticker in close_data.columns:
                        price_series = close_data[ticker]
                        valid_prices = price_series.dropna()
                        if not valid_prices.empty:
                            prices[code] = round(valid_prices.iloc[-1], 2)
                elif isinstance(close_data, pd.Series):
                    if ticker == tickers[0]:
                         valid_prices = close_data.dropna()
                         if not valid_prices.empty:
                             prices[code] = round(valid_prices.iloc[-1], 2)

            except Exception as e:
                prices[code] = 0.0

    except Exception as e:
        pass

    return prices, fetch_time

def calculate_investment(edited_df, total_budget, fee_rate, min_fee):
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
    """渲染總預算指標卡片 (3欄，使用 sub-card-tile 樣式)"""
    col1, col2, col3 = st.columns(3)
    
    # 計算剩餘資本
    remaining = total_budget - total_spent
    remaining_color = ACCENT_COLOR if remaining > 0 else MAIN_COLOR
    remaining_icon = "✅" if remaining > 0 else "⚠️"

    with col1:
        st.markdown(f"""
        <div class='sub-card-tile'>
            <div class='label-text'>💰 總分配資本 (Total Capital)</div>
            <div class='value-text-regular'>TWD {total_budget:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='sub-card-tile'>
            <div class='label-text'>📊 預估部署成本 (Estimated Cost)</div>
            <div class='value-text-regular'>TWD {total_spent:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class='sub-card-tile'>
            <div class='label-text'>{remaining_icon} 剩餘彈藥 (Remaining Budget)</div>
            <div class='value-text-remaining' style='color: {remaining_color};'>TWD {remaining:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 這裡無需手動 div 結束，因為每個 sub-card-tile 都是獨立的 div 結構

def render_ticker_results_and_breakdown(results_list):
    """渲染每檔股票的關鍵投資建議 (5 欄，使用 sub-card-tile/highlight-tile 樣式)"""

    for item in results_list:
        st.markdown(f"<div class='ticker-group-header-sc'>🛡️ 部署目標: {item['標的代號']} ({item['比例']})</div>", unsafe_allow_html=True)

        col1, col2, col3, col4, col5 = st.columns(5)
        
        # 定義 5 個指標的顯示配置
        metrics = [
            ("建議戰術股數 (Shares)", item['建議股數'], "highlight"),
            ("總部署成本 (Cost)", f"TWD {item['總成本']:,.2f}", "regular"),
            ("目標資本 (Target Capital)", f"TWD {item['分配金額']:,.0f}", "regular"),
            ("單價 (Unit Price)", f"TWD {item['價格']:,.2f}", "regular"),
            ("交易燃料費 (Broker Fee)", f"TWD {item['預估手續費']:,.0f}", "regular"),
        ]

        # 渲染 5 欄
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


def render_editable_input_panel(ticker_map, allocation_weights, prices_ready=True):
    """渲染可編輯的價格與比例面板，使用簡化的列分隔線風格。"""
    st.markdown("<div class='card-section-header'>⚙️ 戰術參數設定 (價格與比例)</div>", unsafe_allow_html=True)

    if not prices_ready:
        st.warning("⚠️ 警告：價格數據獲取失敗，所有價格已設為 0。請手動輸入價格以進行準確計算！")

    for i, code in enumerate(ticker_map.keys()):
        weight = allocation_weights[code]
        price_value = st.session_state.editable_prices.get(code, 0.01)
        
        # 設置行分隔線樣式
        row_style = "padding: 0.75rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1);"
        if i == len(ticker_map) - 1:
            row_style = "padding: 0.75rem 0;" # 最後一行不加底線

        with st.container():
            st.markdown(f"<div style='{row_style}'>", unsafe_allow_html=True) 
            
            col_code, col_weight, col_price = st.columns([1.5, 1, 2.5])

            with col_code:
                st.markdown(f"""
                    <div class='label-text' style='color: {MAIN_COLOR}; margin-bottom: 0;'>🎯 {code}</div>
                    <div class='value-text-regular' style='font-size: 0.85em; color: {LABEL_COLOR}; margin-top: 0.25rem; font-weight: normal;'>目標標的代號</div>
                """, unsafe_allow_html=True)

            with col_weight:
                st.markdown(f"""
                    <div class='label-text' style='margin-bottom: 0;'>比例</div>
                    <div class='value-text-regular' style='font-size: 1.2em; margin-top: 0.25rem;'>{weight*100:.0f}%</div>
                """, unsafe_allow_html=True)


            with col_price:
                st.markdown("<div class='label-text' style='margin-bottom: 0;'>部署單價 (TWD)</div>", unsafe_allow_html=True)

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

            st.markdown("</div>", unsafe_allow_html=True)


def check_allocation_sum(weights):
    """檢查分配比例總和是否為 1.0"""
    current_sum = sum(weights.values())
    return abs(current_sum - 1.0) < 1e-9

# ========== 頁面主體邏輯 ==========

st.title(TCDI_TITLE_TEXT)

# 獲取價格
prices_ready = True
with st.spinner('正在從 Terran 交易所獲取最新戰術報價 (Yahoo Finance)...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)
    if all(p == 0.0 for p in current_prices.values()):
        prices_ready = False

# --- NEW: 初始化 Session State 以管理可編輯價格 ---
if 'editable_prices' not in st.session_state:
    st.session_state.editable_prices = current_prices.copy()
else:
    for code, price in current_prices.items():
        if f"price_input_{code}" not in st.session_state:
             st.session_state.editable_prices[code] = price


# -------------------- Sidebar 參數設定 --------------------
st.sidebar.header("⚙️ 資源調度配置")
total_budget = st.sidebar.number_input(
    "每月資本調度預算 (TWD)",
    min_value=100,
    value=30000,
    step=1000,
    format="%d"
)
fee_rate = st.sidebar.number_input(
    "交易燃料費率 (0.xxxx)",
    min_value=0.000001,
    max_value=0.01,
    value=FEE_RATE_DEFAULT,
    step=0.000001,
    format="%.6f"
)
st.sidebar.caption(f"💡 最低燃料費為 **{MIN_FEE}** 元 / 筆。請使用 **小數** 格式輸入。")

# 比例總和檢查
if not check_allocation_sum(ALLOCATION_WEIGHTS):
    st.sidebar.error("❌ 警告：所有標的分配比例總和不等於 100%。請修正 `ALLOCATION_WEIGHTS` 變量。")
    safe_weights = {k: v / sum(ALLOCATION_WEIGHTS.values()) for k, v in ALLOCATION_WEIGHTS.items()}
else:
    safe_weights = ALLOCATION_WEIGHTS

# 1. 報價資訊
st.info(f"🌐 數據同步時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')} (戰術報價資料每 60 秒自動更新一次)")

# 2. 價格與比例輸入 (Setting)
render_editable_input_panel(TICKER_MAP, safe_weights, prices_ready)

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
st.markdown("<div class='card-section-header'>💰 資本部署總覽 (Budget Overview)</div>", unsafe_allow_html=True)
render_budget_metrics(total_budget, total_spent)

# 4. 建議買入與詳細明細 (Results)
st.markdown("<div class='card-section-header'>✨ 戰術部署建議 (Purchase Recommendation)</div>", unsafe_allow_html=True)
render_ticker_results_and_breakdown(results_list)

# 5. 邏輯說明
st.markdown(f"<div style='margin-top: 1.5rem; color: {LABEL_COLOR}; font-size: 0.9em; padding-left: 1rem;'>📌 T.C.D.I. 部署原則：優先確保買入股數最大化，且總成本 **嚴格不超過** 分配預算。交易燃料費最低 {MIN_FEE} 元計算。</div>", unsafe_allow_html=True)
