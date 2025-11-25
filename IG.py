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

TERRAN_CRIMSON = "#e54848"
TERRAN_ACCENT = "#ffc300"
TEXT_COLOR = "#ffffff"
LABEL_COLOR = "#b0b0b0"
DARK_BG = "#1a1a1a"

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
TCDI_TITLE_TEXT = "泰倫戰術資本部署介面 (T.C.D.I.)"

st.markdown(f"""
<style>
.stApp {{
    font-size: 1.05rem;
    color: {TEXT_COLOR};
    background-color: #0e1117;
}}

h1 {{
    font-size: 2.2em !important;
    color: {TERRAN_CRIMSON} !important;
    font-weight: bold !important;
    margin-bottom: 0.5rem !important;
    text-shadow: 0 0 5px rgba(229, 72, 72, 0.5);
}}

.metric-card {{
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    height: 100%;
    color: {TEXT_COLOR};
    transition: background 0.3s;
}}

.metric-card-main {{
    background: {DARK_BG};
    border: 2px solid {TERRAN_CRIMSON};
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 1rem;
    box-shadow: 0 0 10px rgba(229, 72, 72, 0.2);
}}

.metric-card-detail {{
    background: rgba(255, 255, 255, 0.03);
    border-left: 3px solid rgba(255, 255, 255, 0.1);
    padding: 0.8rem;
    margin-bottom: 0.3rem;
    height: 100%;
}}

.label-text {{
    font-size: 0.9em;
    color: {LABEL_COLOR};
    font-weight: 500;
    margin-bottom: 0.2rem;
    line-height: 1.2;
    text-transform: uppercase;
}}

.value-text-main {{
    color: {TEXT_COLOR};
    font-size: 1.5em;
    font-weight: bold;
}}

.value-text-highlight {{
    color: {TERRAN_ACCENT};
    font-size: 2.0em;
    font-weight: 900;
    text-shadow: 0 0 8px rgba(255, 195, 0, 0.5);
}}

.card-section-header {{
    color: {TERRAN_CRIMSON};
    font-weight: bold;
    font-size: 1.3em;
    padding: 0.7rem 0;
    margin-top: 1.5rem;
    margin-bottom: 0.5rem;
    border-bottom: 2px solid {TERRAN_CRIMSON};
    text-transform: uppercase;
}}

.ticker-group-header-sc {{
    color: {TERRAN_CRIMSON};
    font-weight: 600;
    font-size: 1.1em;
    padding: 0.5rem 0;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
    border-bottom: 1px dashed rgba(229, 72, 72, 0.5);
}}

.stNumberInput label {{ display: none !important; }}

.stNumberInput > div > div {{
    background-color: #2c2c2c;
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
}}

div[role="alert"] {{
    background-color: rgba(229, 72, 72, 0.15) !important;
    border-left: 5px solid {TERRAN_CRIMSON} !important;
    color: {TEXT_COLOR} !important;
    font-size: 1.0em !important;
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
}}

.stSidebar > div:first-child {{
    background-color: #1a1a1a;
    border-right: 2px solid {TERRAN_CRIMSON};
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
             print("⚠️ 數據下載成功，但返回的 DataFrame 為空。")
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
                print(f"⚠️ 處理 {code} ({ticker}) 數據時發生錯誤: {e}")
                prices[code] = 0.0

    except Exception as e:
        print(f"❌ 無法獲取行情數據 (整體失敗): {e}")

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
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='label-text'>💰 總分配資本 (Total Capital)</div>
            <div class='value-text-main'>TWD {total_budget:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='label-text'>📊 預估部署成本 (Estimated Cost)</div>
            <div class='value-text-main'>TWD {total_spent:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        remaining = total_budget - total_spent
        remaining_color = TERRAN_ACCENT if remaining > 0 else TERRAN_CRIMSON
        remaining_icon = "✅" if remaining > 0 else "⚠️"

        st.markdown(f"""
        <div class='metric-card'>
            <div class='label-text'>{remaining_icon} 剩餘彈藥 (Remaining Budget)</div>
            <div style='color: {remaining_color}; font-size: 1.5em; font-weight: bold;'>TWD {remaining:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

def render_ticker_results_and_breakdown(results_list):
    for item in results_list:
        st.markdown(f"<div class='ticker-group-header-sc'>🛡️ 部署目標: {item['標的代號']} ({item['比例']})</div>", unsafe_allow_html=True)

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            col1.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>建議戰術股數 (Shares)</div>
                <div class='value-text-highlight'>{item['建議股數']}</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            col2.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>總部署成本 (Cost)</div>
                <div class='value-text-regular'>TWD {item['總成本']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            col3.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>目標資本 (Target Capital)</div>
                <div class='value-text-regular'>TWD {item['分配金額']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            col4.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>單價 (Unit Price)</div>
                <div class='value-text-regular'>TWD {item['價格']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with col5:
            col5.markdown(f"""
            <div class='metric-card-detail'>
                <div class='label-text'>交易燃料費 (Broker Fee)</div>
                <div class='value-text-regular'>TWD {item['預估手續費']:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)


def render_editable_input_panel(ticker_map, allocation_weights, prices_ready=True):
    st.markdown("<div class='card-section-header'>⚙️ 戰術參數設定 (價格與比例)</div>", unsafe_allow_html=True)

    if not prices_ready:
        st.warning("⚠️ 警告：價格數據獲取失敗，所有價格已設為 0。請手動輸入價格以進行準確計算！")

    st.caption("💬 請在 **部署單價 (TWD)** 欄位輸入您想測試的價格。")

    header_cols = st.columns(3)
    header_cols[0].markdown("<div class='label-text' style='color: white; padding-bottom: 0.3rem;'>🎯 標的代號</div>", unsafe_allow_html=True)
    header_cols[1].markdown("<div class='label-text' style='color: white; padding-bottom: 0.3rem;'>分配比例 (%)</div>", unsafe_allow_html=True)
    header_cols[2].markdown("<div class='label-text' style='color: white; padding-bottom: 0.3rem;'>部署單價 (TWD)</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin: 0.1rem 0; border-top: 1px solid rgba(255, 255, 255, 0.1);'>", unsafe_allow_html=True)

    for code in ticker_map.keys():
        weight = allocation_weights[code]
        cols = st.columns(3)

        with cols[0]:
            st.markdown(f"""
            <div style='padding: 0.4rem 0;'>
                <div class='value-text-regular' style='color: {TERRAN_CRIMSON}; font-weight: 900;'>{code}</div>
            </div>
            """, unsafe_allow_html=True)

        with cols[1]:
            st.markdown(f"""
            <div style='padding: 0.4rem 0;'>
                <div class='value-text-regular'>{weight*100:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with cols[2]:
            price_value = st.session_state.editable_prices.get(code, 0.01)
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

        if code != list(ticker_map.keys())[-1]:
             st.markdown("<div style='border-bottom: 1px dotted rgba(255, 255, 255, 0.05); margin: 0.2rem 0;'></div>", unsafe_allow_html=True)

def check_allocation_sum(weights):
    current_sum = sum(weights.values())
    return abs(current_sum - 1.0) < 1e-9

st.title(TCDI_TITLE_TEXT)

prices_ready = True
with st.spinner('正在從 Terran 交易所獲取最新戰術報價 (Yahoo Finance)...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)
    if all(p == 0.0 for p in current_prices.values()):
        prices_ready = False

if 'editable_prices' not in st.session_state:
    st.session_state.editable_prices = current_prices.copy()
else:
    for code, price in current_prices.items():
        if f"price_input_{code}" not in st.session_state:
             st.session_state.editable_prices[code] = price


st.sidebar.header("⚙️ 資源調度配置")
total_budget = st.sidebar.number_input(
    "每月資本調度預算 (TWD)",
    min_value=100,
    value=3000,
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

if not check_allocation_sum(ALLOCATION_WEIGHTS):
    st.sidebar.error("❌ 警告：所有標的分配比例總和不等於 100%。請修正 `ALLOCATION_WEIGHTS` 變量。")
    safe_weights = {k: v / sum(ALLOCATION_WEIGHTS.values()) for k, v in ALLOCATION_WEIGHTS.items()}
else:
    safe_weights = ALLOCATION_WEIGHTS

st.markdown("<div class='metric-card-main'>", unsafe_allow_html=True)

st.info(f"🌐 數據同步時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')} (戰術報價資料每 60 秒自動更新一次)")

render_editable_input_panel(TICKER_MAP, safe_weights, prices_ready)

data_for_calc = {
    "標的代號": list(TICKER_MAP.keys()),
    "設定比例": [safe_weights[code] for code in TICKER_MAP.keys()],
    "當前價格 (自動獲取)": [st.session_state.editable_prices[code] for code in TICKER_MAP.keys()]
}
edited_df = pd.DataFrame(data_for_calc)

results_list, total_spent = calculate_investment(edited_df, total_budget, fee_rate, MIN_FEE)

st.markdown("<div class='card-section-header'>💰 資本部署總覽 (Budget Overview)</div>", unsafe_allow_html=True)
render_budget_metrics(total_budget, total_spent)

st.markdown("<div class='card-section-header'>✨ 戰術部署建議 (Purchase Recommendation)</div>", unsafe_allow_html=True)
render_ticker_results_and_breakdown(results_list)

st.markdown(f"<div style='margin-top: 1.5rem; color: {LABEL_COLOR}; font-size: 0.9em;'>📌 T.C.D.I. 部署原則：優先確保買入股數最大化，且總成本 **嚴格不超過** 分配預算。交易燃料費最低 {MIN_FEE} 元計算。</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
