import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# 應用程式主要標題 (泰倫風格)
APP_TITLE_TEXT = "泰倫聯邦：星區資源部署系統 (T.C.R.D.S.)"

# --- 基礎設定與常數 (星海/繁中風格 - V37 更新命名) ---
TOTAL_CAPITAL_LABEL = "C-14 總備用晶礦"
ESTIMATED_COST_LABEL = "預計軍火消耗"
REMAINING_FUNDS_LABEL = "剩餘能源庫存"
RESOURCE_READINESS_HEADER = "礦物/瓦斯戰情總覽"
BUDGET_SIDEBAR_HEADER = "⚙️ 戰術部隊參數設定"
BUDGET_INPUT_LABEL = "每月戰術部署上限 (TWD)" 
FEE_RATE_INPUT_LABEL = "物流運輸淨損耗率 (0.xxxxxx)" 
MIN_FEE_CAPTION = "💡 零股 (<1000股) 適用 **{MIN_FEE}** 元最低協議物流費用；整股 (≥1000股) 最低收費為 **20** 元。"

# --- 部署指令與結果 (V37 命名更新) ---
DEPLOYMENT_HEADER = "✨ 作戰部隊分配建議"
RECOMMENDED_UNITS_LABEL = "部署單位數量" 
TOTAL_DEPLOYMENT_COST_LABEL = "最終戰損開支" 
TARGET_FUND_ALLOCATION_LABEL = "目標戰區晶礦配給"
UNIT_COST_LABEL = "戰術單位招募單價 (含議價)" 
LOGISTICS_FEE_LABEL = "預估物流補給費" 
DEPLOYMENT_TARGET_LABEL = "🎯 戰區目標: {code} ({ratio})"
DEPLOYMENT_PRINCIPLE_FOOTER = "📌 作戰準則：在預算內最大化單位數量。物流費用：零股低消 {MIN_FEE} 元，整股低消 20 元。出售時需另計 0.3% 聯邦交易稅。"

# --- 校準數據 (星海/繁中風格) ---
CALIBRATION_HEADER = "⚙️ 市場偵測與議價設定"
TARGET_DESIGNATION_LABEL = "🎯 標的代號"
STRATEGIC_RATIO_LABEL = "作戰區域配比"
DEFAULT_UNIT_COST_LABEL = "偵測到當前市場單價 (TWD)" 
PRICE_BUFFER_LABEL_SC = "超額訂購溢價 (TWD)"
DATA_SYNC_SPINNER = '星區雷達正在獲取最新資源報價...'
DATA_SYNC_INFO = "🌐 資料鏈同步時間：{fetch_time} (雷達數據每 60 秒自動刷新)"
DATA_FETCH_WARNING = "⚠️ 紅色警報：星區資料鏈傳輸中斷或無法獲取。所有價格已暫設為 0.01 元，請您手動輸入當前市場單價以確保部署準確！"

# --- 核心參數 ---
MAIN_COLOR = "#cf6955"    # 橘紅色 (Terran accent)
ACCENT_COLOR = "#e9967a"  # 亮橘色
TEXT_COLOR = "#ffffff"
LABEL_COLOR = "#b0b0b0"
DARK_BG = "#1a1a1a"
TILE_BG = "#1e2126" 

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
FEE_RATE_DEFAULT = 0.000855 
MIN_FEE_ODD = 1  # 零股低消
MIN_FEE_REGULAR = 20 # 整股低消
DEFAULT_BUDGET = 3000 

DEFAULT_BUFFERS = {
    "009813": 0.10, 
    "0050": 0.10,  
    "00878": 0.10, 
}


st.set_page_config(
    page_title=APP_TITLE_TEXT,
    layout="wide",
    initial_sidebar_state="expanded"
)

# 樣式定義
st.markdown(f"""
<style>
.stApp {{
    font-size: 1.05rem;
    color: {TEXT_COLOR};
    background-color: #0e1117; 
}}
h1 {{
    font-size: 2.2em !important;
    color: {MAIN_COLOR} !important;
    font-weight: bold !important;
    margin-bottom: 0.5rem !important;
    text-shadow: 0 0 5px rgba(207, 105, 85, 0.5);
    padding-top: 1rem; 
}}
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
.highlight-tile {{
    background: {TILE_BG}; 
    border-radius: 8px;
    padding: 1.2rem; 
    height: 100%;
    margin-bottom: 1rem;
    border: 2px solid {ACCENT_COLOR}; 
    box-shadow: 0 0 15px rgba(233, 150, 122, 0.5); 
}}
.setting-row {{
    background: #181b20; 
    border-radius: 6px;
    padding: 0.5rem 1rem; 
    margin-bottom: 0.5rem; 
    border-left: 3px solid #333; 
    display: flex; 
    align-items: center;
}}
.label-text {{
    font-size: 0.9em; 
    color: {LABEL_COLOR};
    font-weight: 500;
    margin-bottom: 0.5rem;
    line-height: 1.2;
    text-transform: uppercase;
}}
.value-text-regular {{
    color: {TEXT_COLOR};
    font-size: 1.7em; 
    font-weight: bold;
}}
.value-text-highlight {{
    color: {ACCENT_COLOR}; 
    font-size: 2.3em; 
    font-weight: 900;
    text-shadow: 0 0 8px rgba(233, 150, 122, 0.5);
    line-height: 1; 
}}
.value-text-remaining {{
    font-size: 1.7em; 
    font-weight: bold;
    line-height: 1.2;
}}
.value-text-setting {{
    color: {TEXT_COLOR};
    font-size: 1.4em; 
    font-weight: 700;
    margin-top: 0.2rem !important; 
    margin-bottom: 0.2rem !important;
}}
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
.ticker-group-header-sc {{
    color: {ACCENT_COLOR};
    font-weight: 600;
    font-size: 1.1em;
    padding: 0.5rem 0 0.5rem 0.5rem;
    margin-top: 1.5rem; 
    margin-bottom: 0.8rem;
    border-bottom: 1px dashed rgba(233, 150, 122, 0.5);
}}
.stNumberInput > div > div {{
    background-color: #2e2e2e; 
    border: none;
    border-radius: 6px;
    padding: 0.5rem;
    transition: all 0.2s ease;
}}
.setting-row .stNumberInput > div > div {{
    padding: 0.4rem 0.75rem; 
    margin-top: 0;
    margin-bottom: 0;
}}
.stNumberInput > div > div:focus-within {{
    background-color: #242424; 
    border: 1px solid {ACCENT_COLOR} !important;
    box-shadow: 0 0 7px rgba(233, 150, 122, 0.7); 
}}
.stNumberInput input {{
    color: {ACCENT_COLOR} !important;
    font-weight: bold;
    font-size: 1.1em; 
}}
div[role="alert"] {{
    background-color: rgba(207, 105, 85, 0.15) !important;
    border-left: 5px solid {MAIN_COLOR} !important;
    color: {TEXT_COLOR} !important;
    font-size: 1.0em !important;
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
    padding-left: 1rem; 
}}
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


@st.cache_data(ttl=60)
def get_current_prices(ticker_map):
    prices = {}
    fetch_time = datetime.now()
    tickers = list(ticker_map.values())

    for code in ticker_map.keys():
        prices[code] = 0.0

    try:
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
                    if ticker == tickers[0] and len(tickers) == 1: 
                         valid_prices = close_data.dropna()
                         if not valid_prices.empty:
                             prices[code] = round(valid_prices.iloc[-1], 2)
            except Exception:
                prices[code] = 0.0
    except Exception:
        pass
    return prices, fetch_time

def calculate_investment(edited_df, total_budget, fee_rate, min_fee_odd):
    results_list = []
    total_spent = 0.0

    for _, row in edited_df.iterrows():
        code = row["標的代號"]
        weight = row["設定比例"]
        market_price = row["當前價格 (自動獲取)"]
        price_buffer = row["價格緩衝溢價"]
        allocated_budget = total_budget * weight

        effective_price = market_price + price_buffer
        shares_to_buy = 0
        estimated_fee = 0
        conservative_total_cost = 0.0

        if effective_price <= 0.0001 or allocated_budget <= 0:
            results_list.append({
                "標的代號": code,
                "比例": f"{weight*100:.0f}%",
                "市場價格": market_price,
                "有效造價": effective_price,
                "分配金額": allocated_budget,
                "建議股數": 0,
                "預估手續費": 0,
                "總成本": 0.0,
                "緩衝溢價": price_buffer,
            })
            continue

        max_shares_theoretical = int(allocated_budget / effective_price)
        shares = 0

        for s in range(max_shares_theoretical, -1, -1):
            if s == 0:
                shares = 0
                break
            trade_value_conservative = s * effective_price
            fee_calculated = int(trade_value_conservative * fee_rate)
            
            if s >= 1000:
                current_min_fee = MIN_FEE_REGULAR 
            else:
                current_min_fee = min_fee_odd 

            current_fee = max(current_min_fee, fee_calculated)
            cost_for_budget_check = trade_value_conservative + current_fee

            if cost_for_budget_check <= allocated_budget:
                shares = s
                estimated_fee = current_fee
                conservative_total_cost = cost_for_budget_check
                break

        shares_to_buy = shares
        total_spent += conservative_total_cost
        results_list.append({
            "標的代號": code,
            "比例": f"{weight*100:.0f}%",
            "市場價格": market_price,
            "有效造價": effective_price,
            "分配金額": allocated_budget,
            "建議股數": shares_to_buy,
            "預估手續費": estimated_fee,
            "總成本": round(conservative_total_cost, 2), 
            "緩衝溢價": price_buffer, 
        })

    return results_list, round(total_spent, 2)


def render_budget_metrics(total_budget, total_spent):
    st.markdown(f"<div class='card-section-header'>{RESOURCE_READINESS_HEADER}</div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    remaining = total_budget - total_spent
    remaining_display = round(remaining) 
    total_spent_display = round(total_spent) 

    remaining_color = ACCENT_COLOR if remaining > 0 else MAIN_COLOR
    remaining_icon = "✅" if remaining > 0 else "🚨" 

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
    """渲染每個標的的建議結果 (V37: 優化為 2x2 網格，簡潔版)"""
    st.markdown(f"<div class='card-section-header'>{DEPLOYMENT_HEADER}</div>", unsafe_allow_html=True)

    for item in results_list:
        # 標題
        st.markdown(f"<div class='ticker-group-header-sc'>{DEPLOYMENT_TARGET_LABEL.format(code=item['標的代號'], ratio=item['比例'])}</div>", unsafe_allow_html=True)

        # --- 戰術網格佈局 (2x2) ---
        # Row 1: 部署數量 & 單價
        col1, col2 = st.columns(2)
        
        # 1. 建議部署單位數量 (Highlight)
        with col1:
            st.markdown(f"""
            <div class='highlight-tile'>
                <div class='label-text'>{RECOMMENDED_UNITS_LABEL}</div>
                <div class='value-text-highlight'>{item['建議股數']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # 2. 戰術單位招募單價 (有效造價)
        with col2:
            st.markdown(f"""
            <div class='sub-card-tile'>
                <div class='label-text'>{UNIT_COST_LABEL}</div>
                <div class='value-text-regular'>TWD {item['有效造價']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        # Row 2: 最終開支 & 資金配給/物流費
        col3, col4 = st.columns(2)

        # 3. 最終戰損開支
        with col3:
            st.markdown(f"""
            <div class='sub-card-tile'>
                <div class='label-text'>{TOTAL_DEPLOYMENT_COST_LABEL}</div>
                <div class='value-text-regular'>TWD {item['總成本']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        # 4. 目標戰區晶礦配給 & 預估物流補給費 (整合顯示)
        with col4:
            st.markdown(f"""
            <div class='sub-card-tile'>
                <div class='label-text'>{TARGET_FUND_ALLOCATION_LABEL}</div>
                <div class='value-text-regular' style='margin-bottom: 0.8rem;'>TWD {item['分配金額']:,.0f}</div>
                
                <div style='border-top: 1px dashed rgba(255, 255, 255, 0.1); padding-top: 0.5rem; font-size: 0.9em; color: {LABEL_COLOR};'>
                    📦 {LOGISTICS_FEE_LABEL}: <span style='color: {TEXT_COLOR}; font-weight: bold;'>TWD {item['預估手續費']:,.0f}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_ticker_settings(ticker_map, allocation_weights, prices_ready=True):
    st.markdown(f"<div class='card-section-header'>{CALIBRATION_HEADER}</div>", unsafe_allow_html=True)

    if not prices_ready:
        st.warning(DATA_FETCH_WARNING)

    # 設置標題列
    cols_header = st.columns([1.5, 1, 2.5, 2.5])
    with cols_header[0]:
        st.markdown(f"<div class='label-text'>{TARGET_DESIGNATION_LABEL}</div>", unsafe_allow_html=True)
    with cols_header[1]:
        st.markdown(f"<div class='label-text'>{STRATEGIC_RATIO_LABEL}</div>", unsafe_allow_html=True)
    with cols_header[2]:
        st.markdown(f"<div class='label-text'>{DEFAULT_UNIT_COST_LABEL}</div>", unsafe_allow_html=True) 
    with cols_header[3]:
        st.markdown(f"<div class='label-text'>{PRICE_BUFFER_LABEL_SC}</div>", unsafe_allow_html=True) 

    for code in ticker_map.keys():
        weight = allocation_weights[code]
        price_value = st.session_state.editable_prices.get(code, 0.01)
        buffer_value = st.session_state.ticker_buffers.get(code, DEFAULT_BUFFERS.get(code, 0.01))

        with st.container():
            st.markdown("<div class='setting-row'>", unsafe_allow_html=True)
            col_code, col_weight, col_price, col_buffer = st.columns([1.5, 1, 2.5, 2.5])

            with col_code:
                st.markdown(f"""<div class='value-text-setting'>{code}</div>""", unsafe_allow_html=True)
            with col_weight:
                st.markdown(f"""<div class='value-text-setting'>{weight*100:.0f}%</div>""", unsafe_allow_html=True)
            with col_price:
                new_price = st.number_input(
                    label=f"Price_Input_{code}",
                    min_value=0.01,
                    value=price_value,
                    step=0.01,
                    format="%.2f",
                    key=f"price_input_{code}",
                    label_visibility="collapsed"
                )
                st.session_state.editable_prices[code] = new_price
            with col_buffer:
                new_buffer = st.number_input(
                    label=f"Buffer_Input_{code}",
                    min_value=0.00,
                    value=buffer_value,
                    step=0.01,
                    format="%.2f",
                    key=f"buffer_input_{code}",
                    label_visibility="collapsed"
                )
                st.session_state.ticker_buffers[code] = new_buffer
            st.markdown("</div>", unsafe_allow_html=True)

def check_allocation_sum(weights):
    current_sum = sum(weights.values())
    return abs(current_sum - 1.0) < 1e-9

st.title(APP_TITLE_TEXT)

prices_ready = True
with st.spinner(DATA_SYNC_SPINNER):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)
    if all(p == 0.0 for p in current_prices.values()):
        prices_ready = False

if 'editable_prices' not in st.session_state:
    st.session_state.editable_prices = current_prices.copy()
else:
    for code, price in current_prices.items():
        if f"price_input_{code}" not in st.session_state and st.session_state.editable_prices[code] != price:
             st.session_state.editable_prices[code] = price

if 'ticker_buffers' not in st.session_state:
    st.session_state.ticker_buffers = DEFAULT_BUFFERS.copy()
else:
    for code in TICKER_MAP.keys():
        if code not in st.session_state.ticker_buffers:
            st.session_state.ticker_buffers[code] = DEFAULT_BUFFERS.get(code, 0.01)

st.sidebar.header(BUDGET_SIDEBAR_HEADER)
total_budget = st.sidebar.number_input(
    BUDGET_INPUT_LABEL, 
    min_value=100,
    value=DEFAULT_BUDGET,
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
st.sidebar.caption(MIN_FEE_CAPTION.format(MIN_FEE=MIN_FEE_ODD))

if not check_allocation_sum(ALLOCATION_WEIGHTS):
    st.sidebar.error("❌ 警告：所有戰區配比總和不等於 100%。請修正 `ALLOCATION_WEIGHTS` 變量。")
    safe_weights = {k: v / sum(ALLOCATION_WEIGHTS.values()) for k, v in ALLOCATION_WEIGHTS.items()}
else:
    safe_weights = ALLOCATION_WEIGHTS

st.info(DATA_SYNC_INFO.format(fetch_time=fetch_time.strftime('%Y-%m-%d %H:%M:%S')))

render_ticker_settings(TICKER_MAP, safe_weights, prices_ready)

data_for_calc = {
    "標的代號": list(TICKER_MAP.keys()),
    "設定比例": [safe_weights[code] for code in TICKER_MAP.keys()],
    "當前價格 (自動獲取)": [st.session_state.editable_prices[code] for code in TICKER_MAP.keys()],
    "價格緩衝溢價": [st.session_state.ticker_buffers[code] for code in TICKER_MAP.keys()],
}
edited_df = pd.DataFrame(data_for_calc)

results_list, total_spent = calculate_investment(edited_df, total_budget, fee_rate, MIN_FEE_ODD)

render_budget_metrics(total_budget, total_spent)
render_ticker_results_and_breakdown(results_list)

st.markdown(f"<div style='margin-top: 1.5rem; color: {LABEL_COLOR}; font-size: 0.9em; padding-left: 1rem;'>{DEPLOYMENT_PRINCIPLE_FOOTER.format(MIN_FEE=MIN_FEE_ODD)}</div>", unsafe_allow_html=True)
