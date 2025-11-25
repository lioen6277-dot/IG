import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time 

# 設定頁面配置必須在 CSS 注入前 (必須放在腳本最頂端)
st.set_page_config(
    page_title="泰倫戰術資本部署介面 (T.C.D.I.)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 顏色定義與常數 ---
# Round 1 & 8: 導入 StarCraft Terran 主題顏色
TERRAN_CRIMSON = "#e54848"  # 核心紅色 (用於標題, 邊框, 警告)
TERRAN_ACCENT = "#ffc300"   # 琥珀色/金色強調 (用於建議股數, 剩餘資本)
TEXT_COLOR = "#ffffff"       # 白色 (內容文字)
LABEL_COLOR = "#b0b0b0"      # 淡灰 (標籤文字)
DARK_BG = "#1a1a1a"          # 卡片深背景

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
TCDI_TITLE_TEXT = "泰倫戰術資本部署介面 (T.C.D.I.)"

# --- 0. CSS 注入：深色模式與客製化主題 (全面指標卡片化) ---

st.markdown(f"""
<style>
/* -------------------- 應用程式全域設定 (字體放大) -------------------- */
.stApp {{
    font-size: 1.05rem; 
    color: {TEXT_COLOR};
    background-color: #0e1117; 
}}

/* -------------------- 標題樣式 (Round 1 & 8: Terran 主題) -------------------- */
h1 {{
    font-size: 2.2em !important; 
    color: {TERRAN_CRIMSON} !important; 
    font-weight: bold !important;
    margin-bottom: 0.5rem !important;
    text-shadow: 0 0 5px rgba(229, 72, 72, 0.5); /* 增加光暈效果 */
}}

/* -------------------- 單一卡片排版的核心調整 -------------------- */
/* Base Card Style */
.metric-card {{
    background: rgba(255, 255, 255, 0.05); 
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    height: 100%; 
    color: {TEXT_COLOR};
    transition: background 0.3s; 
}}

/* Main Budget Card - Round 1: 應用主體卡片 */
.metric-card-main {{
    background: {DARK_BG}; 
    border: 2px solid {TERRAN_CRIMSON}; 
    border-radius: 12px;
    padding: 1.5rem; 
    margin-top: 1rem;
    box-shadow: 0 0 10px rgba(229, 72, 72, 0.2); 
}}

/* Detail Card - 內部區塊細節卡片 */
.metric-card-detail {{
    background: rgba(255, 255, 255, 0.03); 
    border-left: 3px solid rgba(255, 255, 255, 0.1); 
    padding: 0.8rem;
    margin-bottom: 0.3rem;
    height: 100%; 
}}

/* Label text - Round 8: 增加科技感 */
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

/* Value text - Highlighted style for Shares (Round 4: 最大化強調) */
.value-text-highlight {{
    color: {TERRAN_ACCENT}; 
    font-size: 2.0em; 
    font-weight: 900; 
    text-shadow: 0 0 8px rgba(255, 195, 0, 0.5); 
}}

/* Ticker Header (Round 8: StarCraft 風格標頭) */
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
    /* 虛線邊框 */
    border-bottom: 1px dashed rgba(229, 72, 72, 0.5); 
}}

/* --- 專門針對 st.number_input 的樣式優化 (Round 5: UX 優化) --- */
.stNumberInput label {{ display: none !important; }}

.stNumberInput > div > div {{
    background-color: #2c2c2c; /* 更深的輸入框背景 */
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 4px;
}}

/* -------------------- 其他微調 -------------------- */
/* Info box (st.info) 風格覆蓋 - Round 1: 與主題色一致 */
div[role="alert"] {{
    background-color: rgba(229, 72, 72, 0.15) !important; 
    border-left: 5px solid {TERRAN_CRIMSON} !important; 
    color: {TEXT_COLOR} !important;
    font-size: 1.0em !important; 
    margin-top: 0.5rem !important;
    margin-bottom: 0.5rem !important;
}}

/* Sidebar 優化 (Round 7) */
.stSidebar > div:first-child {{
    background-color: #1a1a1a;
    border-right: 2px solid {TERRAN_CRIMSON};
}}

</style>
""", unsafe_allow_html=True)


# --- 2. 核心函式 ---

@st.cache_data(ttl=60)
def get_current_prices(ticker_map):
    """
    從 Yahoo Finance 獲取即時價格 (60秒快取)。
    Round 2: 增加穩健性，處理多檔、單檔及下載失敗的情況。
    """
    prices = {}
    fetch_time = datetime.now()
    tickers = list(ticker_map.values())
    
    # 初始化所有價格為 0.0 以確保 DataFrame 構造時不會出錯
    for code in ticker_map.keys():
        prices[code] = 0.0

    try:
        # Round 2: 增加 timeout 到 8 秒
        data = yf.download(tickers, period="1d", interval="1m", progress=False, timeout=8) 

        if data.empty:
             print("⚠️ 數據下載成功，但返回的 DataFrame 為空。")
             return prices, fetch_time

        for code, ticker in ticker_map.items():
            try:
                close_data = data['Close']
                
                if isinstance(close_data, pd.DataFrame):
                    # 處理多檔股票下載
                    if ticker in close_data.columns:
                        price_series = close_data[ticker]
                        valid_prices = price_series.dropna()
                        if not valid_prices.empty:
                            prices[code] = round(valid_prices.iloc[-1], 2)
                elif isinstance(close_data, pd.Series): 
                    # 處理只下載一檔股票
                    if ticker == tickers[0]:
                         valid_prices = close_data.dropna()
                         if not valid_prices.empty:
                            prices[code] = round(valid_prices.iloc[-1], 2)
                            
            except Exception as e:
                print(f"⚠️ 處理 {code} ({ticker}) 數據時發生錯誤: {e}")
                prices[code] = 0.0
                
    except Exception as e:
        # 整體下載失敗的錯誤處理
        print(f"❌ 無法獲取行情數據 (整體失敗): {e}")
            
    return prices, fetch_time

def calculate_investment(edited_df, total_budget, fee_rate, min_fee):
    """
    計算投資分配結果。
    Round 6: 採用迭代法嚴格確保總成本 <= 分配預算，並處理最低手續費。
    Round 9: 接收 min_fee 參數。
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
        
        # Round 3: 價格為 0 則跳過計算
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

        # Round 6: 迭代法找出最大可買股數
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
            
            # 找到第一個符合預算的最大股數
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
            "總成本": round(total_cost, 2), # Round 6: 總成本保留 2 位小數
        })
        
    # Round 6: 總花費也保留 2 位小數
    return results_list, round(total_spent, 2)

def render_budget_metrics(total_budget, total_spent):
    """渲染總預算指標卡片 (3欄)"""
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
        # Round 4: 剩餘預算顏色邏輯優化
        remaining_color = TERRAN_ACCENT if remaining > 0 else TERRAN_CRIMSON
        remaining_icon = "✅" if remaining > 0 else "⚠️"
        
        st.markdown(f"""
        <div class='metric-card'>
            <div class='label-text'>{remaining_icon} 剩餘彈藥 (Remaining Budget)</div>
            <div style='color: {remaining_color}; font-size: 1.5em; font-weight: bold;'>TWD {remaining:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

def render_ticker_results_and_breakdown(results_list):
    """
    渲染每檔股票的關鍵投資建議 (5 欄統一格式)。
    Round 9: 調整標籤為 StarCraft 風格。
    """
    
    for item in results_list:
        # Round 8: 增加 StarCraft 風格的標頭
        st.markdown(f"<div class='ticker-group-header-sc'>🛡️ 部署目標: {item['標的代號']} ({item['比例']})</div>", unsafe_allow_html=True)
        
        # 使用 5 欄佈局
        col1, col2, col3, col4, col5 = st.columns(5) 
        
        # Col 1: 建議股數 (最大化高亮)
        col1.markdown(f"""
        <div class='metric-card-detail'>
            <div class='label-text'>建議戰術股數 (Shares)</div>
            <div class='value-text-highlight'>{item['建議股數']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Col 2: 總成本 (Round 6: 顯示 2 位小數)
        col2.markdown(f"""
        <div class='metric-card-detail'>
            <div class='label-text'>總部署成本 (Cost)</div>
            <div class='value-text-regular'>TWD {item['總成本']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Col 3: 分配預算
        col3.markdown(f"""
        <div class='metric-card-detail'>
            <div class='label-text'>目標資本 (Target Capital)</div>
            <div class='value-text-regular'>TWD {item['分配金額']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Col 4: 當前價格
        col4.markdown(f"""
        <div class='metric-card-detail'>
            <div class='label-text'>單價 (Unit Price)</div>
            <div class='value-text-regular'>TWD {item['價格']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Col 5: 預估手續費
        col5.markdown(f"""
        <div class='metric-card-detail'>
            <div class='label-text'>交易燃料費 (Broker Fee)</div>
            <div class='value-text-regular'>TWD {item['預估手續費']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)


def render_editable_input_panel(ticker_map, allocation_weights, prices_ready=True):
    """
    渲染價格與比例設定區塊。
    Round 5: 優化輸入面板的視覺對齊與卡片集成。
    """
    st.markdown("<div class='card-section-header'>⚙️ 戰術參數設定 (價格與比例)</div>", unsafe_allow_html=True)

    # Round 3: 價格未就緒時的警告
    if not prices_ready:
        st.warning("⚠️ 警告：價格數據獲取失敗，所有價格已設為 0。請手動輸入價格以進行準確計算！")
    
    st.caption("💬 請在 **部署單價 (TWD)** 欄位輸入您想測試的價格。")

    # 1. Column Header (Labels)
    header_cols = st.columns(3)
    header_cols[0].markdown("<div class='label-text' style='color: white; padding-bottom: 0.3rem;'>🎯 標的代號</div>", unsafe_allow_html=True)
    header_cols[1].markdown("<div class='label-text' style='color: white; padding-bottom: 0.3rem;'>分配比例 (%)</div>", unsafe_allow_html=True)
    header_cols[2].markdown("<div class='label-text' style='color: white; padding-bottom: 0.3rem;'>部署單價 (TWD)</div>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin: 0.1rem 0; border-top: 1px solid rgba(255, 255, 255, 0.1);'>", unsafe_allow_html=True)

    # 2. Data Rows
    for code in ticker_map.keys():
        weight = allocation_weights[code]
        cols = st.columns(3)
        
        # Col 1: Ticker Value (Round 8: 強調代號)
        with cols[0]:
            st.markdown(f"""
            <div style='padding: 0.4rem 0;'>
                <div class='value-text-regular' style='color: {TERRAN_CRIMSON}; font-weight: 900;'>{code}</div>
            </div>
            """, unsafe_allow_html=True)

        # Col 2: Weight Value
        with cols[1]:
            st.markdown(f"""
            <div style='padding: 0.4rem 0;'>
                <div class='value-text-regular'>{weight*100:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)

        # Col 3: Editable Price Input
        with cols[2]:
            # Round 6: 最小價格設為 0.0001
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
        
        # 在行與行之間添加虛線分隔
        if code != list(ticker_map.keys())[-1]:
             st.markdown("<div style='border-bottom: 1px dotted rgba(255, 255, 255, 0.05); margin: 0.2rem 0;'></div>", unsafe_allow_html=True)

def check_allocation_sum(weights):
    """Round 3: 檢查分配比例總和是否為 1.0"""
    current_sum = sum(weights.values())
    return abs(current_sum - 1.0) < 1e-9 # 浮點數比較

# ========== 頁面主體邏輯 ==========

st.title(TCDI_TITLE_TEXT)

# 獲取價格 (Round 2 & 3: 穩健性檢查)
prices_ready = True
with st.spinner('正在從 Terran 交易所獲取最新戰術報價 (Yahoo Finance)...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)
    # 如果所有價格都是 0.0，則視為獲取失敗
    if all(p == 0.0 for p in current_prices.values()):
        prices_ready = False

# --- NEW: 初始化 Session State 以管理可編輯價格 ---
if 'editable_prices' not in st.session_state:
    st.session_state.editable_prices = current_prices.copy()
else:
    # Round 10: 確保 session state 中的價格與新獲取的價格同步 (僅當用戶未修改過價格時)
    for code, price in current_prices.items():
        # 如果該 number_input 還沒有被用戶明確初始化（即還不在 session state 的 widgets 列表中），則用新價格覆蓋
        if f"price_input_{code}" not in st.session_state:
             st.session_state.editable_prices[code] = price


# -------------------- Sidebar 參數設定 --------------------
st.sidebar.header("⚙️ 資源調度配置")
total_budget = st.sidebar.number_input(
    "每月資本調度預算 (TWD)",
    min_value=100, # Round 6: 最小預算設為 100
    value=3000,
    step=1000,
    format="%d"
)
fee_rate = st.sidebar.number_input(
    "交易燃料費率 (0.xxxx)",
    min_value=0.000001, # Round 6: 最小費率
    max_value=0.01,
    value=FEE_RATE_DEFAULT,
    step=0.000001,
    format="%.6f"
)
st.sidebar.caption(f"💡 最低燃料費為 **{MIN_FEE}** 元 / 筆。請使用 **小數** 格式輸入。")

# Round 3: 比例總和檢查
if not check_allocation_sum(ALLOCATION_WEIGHTS):
    st.sidebar.error("❌ 警告：所有標的分配比例總和不等於 100%。請修正 `ALLOCATION_WEIGHTS` 變量。")
    # 如果比例不對，則計算安全比例
    safe_weights = {k: v / sum(ALLOCATION_WEIGHTS.values()) for k, v in ALLOCATION_WEIGHTS.items()}
else:
    safe_weights = ALLOCATION_WEIGHTS

# --- 應用程式主體：單一卡片開始 ---
st.markdown("<div class='metric-card-main'>", unsafe_allow_html=True)

# 1. 報價資訊
st.info(f"🌐 數據同步時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')} (戰術報價資料每 60 秒自動更新一次)")

# 2. 價格與比例輸入 (Setting)
render_editable_input_panel(TICKER_MAP, safe_weights, prices_ready)

# ========== 構造 DataFrame for Calculation (從 Session State 讀取數據) ==========
data_for_calc = {
    "標的代號": list(TICKER_MAP.keys()),
    "設定比例": [safe_weights[code] for code in TICKER_MAP.keys()],
    "當前價格 (自動獲取)": [st.session_state.editable_prices[code] for code in TICKER_MAP.keys()]
}
edited_df = pd.DataFrame(data_for_calc)

# ========== 計算（基於編輯後的數據）==========
# Round 9: 傳遞 MIN_FEE 參數
results_list, total_spent = calculate_investment(edited_df, total_budget, fee_rate, MIN_FEE)

# 3. 總預算總覽 (Budget Metrics)
st.markdown("<div class='card-section-header'>💰 資本部署總覽 (Budget Overview)</div>", unsafe_allow_html=True)
render_budget_metrics(total_budget, total_spent)

# 4. 建議買入與詳細明細 (Results)
st.markdown("<div class='card-section-header'>✨ 戰術部署建議 (Purchase Recommendation)</div>", unsafe_allow_html=True)
render_ticker_results_and_breakdown(results_list)

# 5. 邏輯說明
st.markdown(f"<div style='margin-top: 1.5rem; color: {LABEL_COLOR}; font-size: 0.9em;'>📌 T.C.D.I. 部署原則：優先確保買入股數最大化，且總成本 **嚴格不超過** 分配預算 (Round 6 迭代優化)。交易燃料費最低 {MIN_FEE} 元計算。</div>", unsafe_allow_html=True)

# --- 應用程式主體：單一卡片結束 ---
st.markdown("</div>", unsafe_allow_html=True)
