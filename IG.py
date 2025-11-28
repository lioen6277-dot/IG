import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

TACC_TITLE_TEXT = "泰倫戰術指揮中心 (T.A.C.C.)"

# --- 基礎設定與常數 ---
TOTAL_CAPITAL_LABEL = "💰 總戰備資金"
ESTIMATED_COST_LABEL = "📊 預計軍備開支"
REMAINING_FUNDS_LABEL = "現存資金餘額"
RESOURCE_READINESS_HEADER = "💰 資源戰備總覽"
BUDGET_SIDEBAR_HEADER = "⚙️ 資源調度指揮站"
BUDGET_INPUT_LABEL = "每月行動預算 (TWD)"
FEE_RATE_INPUT_LABEL = "輸送燃料費率 (0.xxxxxx)" 
MIN_FEE_CAPTION = "💡 零股 (<1000股) 最低手續費為 **{MIN_FEE}** 元；整股 (≥1000股) 最低手續費自動調整為 **20** 元。"

# --- 部署指令與結果 ---
DEPLOYMENT_HEADER = "✨ 軍事單位部署指令"
RECOMMENDED_UNITS_LABEL = "建議生產單位數"
TOTAL_DEPLOYMENT_COST_LABEL = "部署總開支"
TARGET_FUND_ALLOCATION_LABEL = "目標資金配給"
UNIT_COST_LABEL = "單位造價 (含溢價)" 
DEPLOYMENT_TARGET_LABEL = "🛡️ 部署目標: {code} ({ratio})"
DEPLOYMENT_PRINCIPLE_FOOTER = "📌 T.A.C.C. 部署原則：買入單位數最大化且不超支。手續費：零股低消 {MIN_FEE} 元，整股低消 20 元。賣出時需另計 0.3% 交易稅。"

# --- 校準數據 ---
CALIBRATION_HEADER = "⚙️ 戰術數據校準 (價格與緩衝設定)"
TARGET_DESIGNATION_LABEL = "🎯 戰場目標代號"
STRATEGIC_RATIO_LABEL = "戰略配置比例"
DEFAULT_UNIT_COST_LABEL = "當前市價單價 (TWD)" 
PRICE_BUFFER_LABEL_SC = "價格緩衝溢價 (TWD)"
DATA_SYNC_SPINNER = '正在從聯邦情報網絡獲取最新戰術報價...'
DATA_SYNC_INFO = "🌐 數據鏈同步時間：{fetch_time} (戰術報價資訊每 60 秒自動刷新)"
DATA_FETCH_WARNING = "⚠️ 警告：戰術報價數據鏈中斷。所有價格已暫設為 0.01 元，請您手動輸入當前市價以確保計算準確！"

# --- 核心參數 ---
MAIN_COLOR = "#cf6955"    
ACCENT_COLOR = "#e9967a"  
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
FEE_RATE_DEFAULT = 0.001425
MIN_FEE_ODD = 1  # 零股低消
MIN_FEE_REGULAR = 20 # 整股低消
DEFAULT_BUDGET = 3000 

# 針對不同標的設定的預設緩衝溢價
DEFAULT_BUFFERS = {
    "009813": 0.10, 
    "0050": 0.10,  
    "00878": 0.10, 
}


st.set_page_config(
    page_title=TACC_TITLE_TEXT,
    layout="wide",
    initial_sidebar_state="expanded"
)

# 樣式定義 (保持不變)
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
    margin-top: 0.25rem;
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
.stNumberInput > div > div:focus-within {{
    background-color: #242424; 
    border: 1px solid {ACCENT_COLOR} !important;
    box-shadow: 0 0 7px rgba(233, 150, 122, 0.7); 
}}
.stNumberInput input {{
    color: {ACCENT_COLOR} !important;
    font-weight: bold;
    font-size: 1.3em; 
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

# --- 核心計算邏輯更新：整股/零股手續費規則 ---
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

        # 從理論最大值開始遞減，找出符合預算的股數
        for s in range(max_shares_theoretical, -1, -1):
            if s == 0:
                shares = 0
                break

            # 1. 交易價值
            trade_value_conservative = s * effective_price
            
            # 2. 手續費計算 (整數運算)
            fee_calculated = int(trade_value_conservative * fee_rate)
            
            # 3. 判斷整股 (>=1000) 或零股 (<1000) 適用不同低消
            if s >= 1000:
                current_min_fee = 20 # 整股低消 20元
            else:
                current_min_fee = min_fee_odd # 零股低消 1元 (使用者設定)

            current_fee = max(current_min_fee, fee_calculated)
            
            # 4. 總成本
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
    st.markdown(f"<div class='card-section-header'>{DEPLOYMENT_HEADER}</div>", unsafe_allow_html=True)

    for item in results_list:
        st.markdown(f"<div class='ticker-group-header-sc'>{DEPLOYMENT_TARGET_LABEL.format(code=item['標的代號'], ratio=item['比例'])}</div>", unsafe_allow_html=True)

        total_cost_display = item['總成本']
        effective_price = item['有效造價'] 

        metrics = [
            (RECOMMENDED_UNITS_LABEL, item['建議股數'], "highlight"),
            (UNIT_COST_LABEL, f"TWD {effective_price:,.2f}", "regular"),
            (TOTAL_DEPLOYMENT_COST_LABEL, f"TWD {total_cost_display:,.2f}", "regular"), 
            (TARGET_FUND_ALLOCATION_LABEL, f"TWD {item['分配金額']:,.0f}", "regular"),
            (LOGISTICS_FEE_LABEL, f"TWD {item['預估手續費']:,.0f}", "regular"),
        ]

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

        st.markdown("<div class='sub-card-tile'>", unsafe_allow_html=True)
        
        col_code, col_weight, col_price, col_buffer = st.columns([1.5, 1, 2.5, 2.5])

        with col_code:
            st.markdown(f"""
                <div class='value-text-setting' style='margin-top: 0.25rem;'>{code}</div>
            """, unsafe_allow_html=True)

        with col_weight:
            st.markdown(f"""
                <div class='value-text-setting' style='margin-top: 0.25rem;'>{weight*100:.0f}%</div>
            """, unsafe_allow_html=True)

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

st.title(TACC_TITLE_TEXT)

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
    st.sidebar.error("❌ 警告：所有標的分配比例總和不等於 100%。請修正 `ALLOCATION_WEIGHTS` 變量。")
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
