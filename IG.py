import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import time 

# 設定頁面配置必須在 CSS 注入前 (必須放在腳本最頂端)
st.set_page_config(
    page_title="零股投資計算機 (即時報價)",
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
# 預設分配權重
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
/* -------------------- 應用程式全域設定 (字體放大) -------------------- */

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

h2, h3, h4 {{
    font-size: 1.5em !important;
    color: {PRIMARY_COLOR} !important;
    font-weight: bold !important;
    margin: 0.8rem 0 0.3rem 0 !important;
}}

/* -------------------- 文字與指標卡片樣式 (核心優化部分) -------------------- */

/* Data Editor 表頭背景色 (Settings 區塊視覺一致性) */
.st-emotion-cache-1c19gh9 {{
    background-color: {ACCENT_COLOR} !important;
    color: white !important;
}}

/* Base Card Style */
.metric-card {{
    background: rgba(255, 255, 255, 0.05); 
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    height: 100%; /* Ensure column content aligns */
    color: {TEXT_COLOR};
}}

/* Main Budget Card - with strong primary color border */
.metric-card-main {{
    padding: 1.2rem 1rem; 
    border-left: 3px solid {PRIMARY_COLOR}; 
}}

/* Detail Card - for the breakdown section, using a light border */
.metric-card-detail {{
    background: rgba(255, 255, 255, 0.03); 
    border-left: 1px solid rgba(255, 255, 255, 0.1); 
    padding: 0.8rem;
    margin-bottom: 0.3rem;
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
    font-size: 1.2em; /* 略微縮小以適應緊湊佈局 */
    font-weight: bold;
}}

/* Value text - Highlighted style for Shares (最大化強調) */
.value-text-highlight {{
    color: {ACCENT_COLOR}; 
    font-size: 1.8em; 
    font-weight: bold;
}}

/* Ticker Header (New unified header) */
.ticker-group-header {{
    color: {PRIMARY_COLOR};
    font-weight: bold;
    font-size: 1.3em;
    padding: 0.5rem 0;
    margin-top: 1rem;
    margin-bottom: 0.2rem;
    border-bottom: 1px dashed rgba(240, 128, 128, 0.5); 
}}

/* -------------------- 其他微調 -------------------- */

/* Info box (st.info) 風格覆蓋 */
div[role="alert"] {{
    background-color: rgba(240, 128, 128, 0.15) !important; 
    border-left: 5px solid {PRIMARY_COLOR} !important; 
    color: {TEXT_COLOR} !important;
    font-size: 1.0em !important; 
}}

/* 分隔線 (優化垂直間距) */
hr {{
    margin: 0.6rem 0 !important; 
}}

</style>
""", unsafe_allow_html=True)


# --- 2. 核心函式 ---

@st.cache_data(ttl=60)
def get_current_prices(ticker_map):
    """
    從 Yahoo Finance 獲取即時價格 (60秒快取)。
    已優化錯誤處理，確保即使 API 失敗或價格無效，應用程式仍能穩定運行。
    """
    prices = {}
    fetch_time = datetime.now()
    tickers = list(ticker_map.values())
    
    try:
        # 設置較短的超時時間，避免長時間阻塞
        data = yf.download(tickers, period="1d", interval="1m", progress=False, timeout=5)
        
        for code, ticker in ticker_map.items():
            try:
                # 檢查數據是否包含該股票代碼且有有效的收盤價
                if not data.empty and ticker in data['Close']:
                    price_series = data['Close'][ticker]
                    # 排除 NaN 值並取得最後一個有效價格
                    valid_prices = price_series.dropna()
                    if not valid_prices.empty:
                        price = valid_prices.iloc[-1]
                        prices[code] = round(price, 2)
                    else:
                        prices[code] = 0.0 # 數據為空或 NaN 則設為 0
                else:
                    prices[code] = 0.0
            except Exception:
                prices[code] = 0.0 # 單一股票處理錯誤
    except Exception:
        # 網路或 yfinance 嚴重錯誤，全部價格設為 0
        st.warning("⚠️ 無法獲取行情數據，請檢查網絡連接或代碼是否正確。所有價格已設為 0。")
        for code in ticker_map.keys():
            prices[code] = 0.0
            
    return prices, fetch_time

def calculate_investment(edited_df, total_budget, fee_rate):
    """
    計算投資分配結果。
    已優化計算邏輯，確保總成本絕對不超過分配預算，並正確處理最低手續費問題。
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
            # 1. 估算最高可買股數 (使用簡化公式: 股數 = 預算 / (價格 * (1 + 費率)))
            shares_to_buy = int(allocated_budget / (price * (1 + fee_rate)))
            
            # 2. 如果一股都買不起，則停在 0
            if shares_to_buy < 0:
                shares_to_buy = 0
            
            # 3. 如果能買，計算該股數下的成本和手續費
            if shares_to_buy > 0:
                fee_calculated = price * shares_to_buy * fee_rate
                estimated_fee = max(MIN_FEE, round(fee_calculated))
                total_cost = (shares_to_buy * price) + estimated_fee
            
                # 4. 健壯性檢查：如果最低手續費 (1元) 導致總成本超支，則減少一股
                if total_cost > allocated_budget:
                    # 減少一股後重新計算
                    shares_to_buy -= 1
                    
                    if shares_to_buy > 0:
                        # 重新計算股數減少後的費用
                        fee_recalculated = price * shares_to_buy * fee_rate
                        estimated_fee = max(MIN_FEE, round(fee_recalculated))
                        total_cost = (shares_to_buy * price) + estimated_fee
                    else:
                         # 如果減到 0，確保成本也為 0
                        estimated_fee = 0
                        total_cost = 0.0

        # 確保總成本不會因為浮點數誤差導致微小超支
        if total_cost > allocated_budget:
             # 如果仍然超支 (通常是四捨五入問題)，則強制設為分配預算 (這是一個視覺上的保險)
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
    """渲染總預算指標卡片 (使用客製化 Markdown 樣式)"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card metric-card-main'> 
            <div class='label-text'>💰 總投資預算</div>
            <div class='value-text-main'>TWD {total_budget:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class='metric-card metric-card-main'>
            <div class='label-text'>📊 預估總花費</div>
            <div class='value-text-main'>TWD {total_spent:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        remaining = total_budget - total_spent
        # 根據剩餘預算決定文字顏色 (負值使用強調色)
        remaining_color = ACCENT_COLOR if remaining < 0 else TEXT_COLOR
        st.markdown(f"""
        <div class='metric-card metric-card-main'>
            <div class='label-text'>💵 剩餘預算</div>
            <div style='color: {remaining_color}; font-size: 1.5em; font-weight: bold;'>TWD {remaining:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

def render_ticker_results(results_list):
    """渲染每檔股票的關鍵投資建議 (4個關鍵指標卡片)"""
    
    for item in results_list:
        # 標題獨立顯示
        st.markdown(f"<div class='ticker-group-header'>✅ {item['標的代號']} ({item['比例']})</div>", unsafe_allow_html=True)
        
        # 使用 4 欄佈局 (建議股數、預估成本、分配預算、當前價格)
        col1, col2, col3, col4 = st.columns(4) 
        
        # Col 1: 建議股數 (最大化高亮)
        col1.markdown(f"""
        <div class='metric-card'>
            <div class='label-text'>建議股數</div>
            <div class='value-text-highlight'>{item['建議股數']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Col 2: 預估成本 (常規顯示)
        col2.markdown(f"""
        <div class='metric-card'>
            <div class='label-text'>預估成本</div>
            <div class='value-text-regular'>TWD {item['總成本']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Col 3: 分配預算 (常規顯示)
        col3.markdown(f"""
        <div class='metric-card'>
            <div class='label-text'>分配預算</div>
            <div class='value-text-regular'>TWD {item['分配金額']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Col 4: 當前價格 (常規顯示)
        col4.markdown(f"""
        <div class='metric-card'>
            <div class='label-text'>當前價格</div>
            <div class='value-text-regular'>TWD {item['價格']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

def render_detailed_breakdown_cards(results_list):
    """
    渲染詳細投資明細，使用 3 欄指標卡片佈局取代 st.dataframe。
    只顯示明細中獨有的欄位：分配金額、預估手續費、總成本。
    """
    
    for item in results_list:
        # 標題：股票代號與分配比例
        st.markdown(f"<div class='ticker-group-header' style='margin-top: 1.5rem;'>📌 {item['標的代號']} 詳細明細 ({item['比例']})</div>", unsafe_allow_html=True)
        
        # 使用 3 欄佈局顯示所有詳細數據
        col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5) 
        
        # 1. 建議股數 (高亮且在詳細中再次顯示)
        col_s1.markdown(f"""
        <div class='metric-card metric-card-detail'>
            <div class='label-text'>建議股數</div>
            <div class='value-text-highlight' style='font-size: 1.5em;'>{item['建議股數']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. 總成本
        col_s2.markdown(f"""
        <div class='metric-card metric-card-detail'>
            <div class='label-text'>總成本</div>
            <div class='value-text-regular'>TWD {item['總成本']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. 分配金額
        col_s3.markdown(f"""
        <div class='metric-card metric-card-detail'>
            <div class='label-text'>分配預算</div>
            <div class='value-text-regular'>TWD {item['分配金額']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

        # 4. 預估手續費
        col_s4.markdown(f"""
        <div class='metric-card metric-card-detail'>
            <div class='label-text'>預估手續費</div>
            <div class='value-text-regular'>TWD {item['預估手續費']:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

        # 5. 當前價格
        col_s5.markdown(f"""
        <div class='metric-card metric-card-detail'>
            <div class='label-text'>當前價格</div>
            <div class='value-text-regular'>TWD {item['價格']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---") # 用於分隔每檔股票的詳細明細


# ========== 頁面主體邏輯 ==========

st.title("📈 零股投資分配計算機 (即時報價)")
st.markdown("---")

# 獲取價格
with st.spinner('正在從 Yahoo Finance 獲取最新報價...'):
    current_prices, fetch_time = get_current_prices(TICKER_MAP)

# 使用優化後的 st.info 風格
st.info(f"📍 報價更新時間：{fetch_time.strftime('%Y-%m-%d %H:%M:%S')} (價格資料每 60 秒自動更新一次)")

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

# 初始化數據編輯框
data_to_edit = {
    "標的代號": list(current_prices.keys()),
    "設定比例": [ALLOCATION_WEIGHTS[code] for code in current_prices.keys()],
    "當前價格 (自動獲取)": [current_prices[code] for code in current_prices.keys()]
}
input_df = pd.DataFrame(data_to_edit)

# ========== 價格與比例輸入（供使用者編輯）==========
st.divider()
st.subheader("⚙️ 價格與比例設定")
st.caption("💬 報價為自動獲取，您可手動點擊 **當前價格** 欄位進行情境測試。其他欄位已鎖定。建議比例總和必須為 1.0 (100%)。")

# 保持 st.data_editor 進行輸入，確保功能性最佳
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
    disabled=["標的代號", "設定比例"], # 鎖定標的代號與比例，只允許修改價格
    num_rows="fixed",
    key="data_editor_key",
    use_container_width=True
)

# 檢查比例合計 (即使鎖定，仍需檢查以防初始配置錯誤)
weight_sum = edited_df['設定比例'].sum()
# 由於浮點數計算，使用微小的容忍度 (0.01)
if abs(weight_sum - 1.0) > 0.01:
    st.error(f"⚠️ 錯誤：設定比例總和必須為 100% (目前為 {weight_sum*100:.0f}%)，請調整。")
    st.stop()

# ========== 計算（基於編輯後的數據）==========
results_list, total_spent = calculate_investment(edited_df, total_budget, fee_rate)

# ========== 顯示結果區域 ==========

st.divider()
st.header("💰 投資預算總覽")
render_budget_metrics(total_budget, total_spent)

st.divider()
st.header("✨ 建議買入股數概覽")
render_ticker_results(results_list)

st.divider()
st.header("📋 詳細投資明細 (卡片化)")
render_detailed_breakdown_cards(results_list) # 使用新的卡片化函式

st.divider()
st.caption("📌 計算邏輯：優先確保買入股數最大化，且總花費不超過分配預算；手續費最低 1 元計算。")
