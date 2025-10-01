import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta
import warnings
import time
import re 
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# ==============================================================================
# 1. 頁面配置與全局設定
# ==============================================================================

st.set_page_config(
    page_title="🤖 AI趨勢分析儀表板 📈", 
    page_icon="📈", 
    layout="wide"
)

# 週期映射：(YFinance Period, YFinance Interval)
PERIOD_MAP = { 
    "30 分 (短期)": ("60d", "30m"), 
    "4 小時 (波段)": ("1y", "60m"), 
    "1 日 (中長線)": ("5y", "1d"), 
    "1 週 (長期)": ("max", "1wk")
}

# 🚀 您的【所有資產清單】(FULL_SYMBOLS_MAP)
FULL_SYMBOLS_MAP = {
    # ----------------------------------------------------
    # A. 美股核心 (US Stocks) - 個股
    # ----------------------------------------------------
    "TSLA": {"name": "特斯拉", "keywords": ["特斯拉", "電動車", "TSLA", "Tesla"]},
    "NVDA": {"name": "輝達", "keywords": ["輝達", "英偉達", "AI", "NVDA", "Nvidia"]},
    "AAPL": {"name": "蘋果", "keywords": ["蘋果", "手機", "AAPL", "Apple"]},
    "MSFT": {"name": "微軟", "keywords": ["微軟", "軟體", "MSFT", "Microsoft"]},
    "GOOGL": {"name": "谷歌", "keywords": ["谷歌", "Google", "Alphabet", "GOOGL"]},
    "AMZN": {"name": "亞馬遜", "keywords": ["亞馬遜", "電商", "AMZN", "Amazon"]},
    # ----------------------------------------------------
    # B. 台股核心 (TW Stocks) - 個股/ETF
    # ----------------------------------------------------
    "2330.TW": {"name": "台積電", "keywords": ["台積電", "晶圓", "2330", "TSMC"]},
    "2303.TW": {"name": "聯電", "keywords": ["聯電", "晶圓", "2303"]},
    "0050.TW": {"name": "元大台灣50", "keywords": ["0050", "台灣50", "ETF"]},
    "2454.TW": {"name": "聯發科", "keywords": ["聯發科", "MTK", "2454"]},
    # ----------------------------------------------------
    # C. 加密貨幣 (Crypto) - 採用幣安數據 (yfinance 格式)
    # ----------------------------------------------------
    "BTC-USD": {"name": "比特幣", "keywords": ["比特幣", "BTC", "Crypto"]},
    "ETH-USD": {"name": "以太幣", "keywords": ["以太幣", "ETH", "Crypto"]},
}

# 輔助字典，用於快速從代碼查找到名稱
SYMBOL_TO_NAME = {symbol: data['name'] for symbol, data in FULL_SYMBOLS_MAP.items()}

# ------------------------------------------------------------------------------
# 2. 核心數據處理與技術指標計算 (修正區)
# ------------------------------------------------------------------------------

@st.cache_data(ttl=60*15) # 緩存15分鐘
def download_data(symbol, period, interval):
    """使用 yfinance 下載數據並進行基本清理。"""
    try:
        # 下載數據
        data = yf.download(symbol, period=period, interval=interval, progress=False)
        
        if data.empty:
            st.warning(f"⚠️ **數據警告:** 無法獲取 {symbol} 的數據。請檢查代碼或調整時間範圍/週期。")
            return pd.DataFrame()
        
        # 處理缺失值 (前一個有效值填充)
        data.fillna(method='ffill', inplace=True)
        # 移除任何剩餘的 NaN 行
        data.dropna(inplace=True)
        
        # 確保必要的欄位存在
        required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(col in data.columns for col in required_cols):
            st.error(f"❌ **數據錯誤:** 獲取的數據缺少必要的 OHLCV 欄位。")
            return pd.DataFrame()
            
        return data
    except Exception as e:
        st.error(f"❌ **下載失敗:** 獲取 {symbol} 數據時發生錯誤: {e}")
        return pd.DataFrame()

def calculate_technical_indicators(df):
    """計算所有技術指標並返回原始df與格式化後的摘要表。"""
    
    # --- FIX FOR ValueError: Data must be 1-dimensional (Add robust data check) ---
    # 檢查DataFrame是否為空或缺少關鍵的'Close'欄位 (yfinance下載失敗時常發生)
    if df.empty or 'Close' not in df.columns or df['Close'].isnull().all():
        # 如果數據無效，顯示錯誤並返回空的 DataFrames 以防止後續錯誤
        st.error("⚠️ **數據不足:** 無法計算技術指標。數據集為空、缺少 'Close' 價格或數據皆為 NaN。請嘗試調整時間範圍/週期。")
        return pd.DataFrame(), pd.DataFrame()
    # -----------------------------------------------------------------------------
    
    try:
        # 確保 'Close' 是一個 1D 的 Series (這一步通常可以防止 ValueError)
        close_series = df['Close'].astype(float).squeeze()

        # 趨勢指標
        df['SMA_5'] = ta.trend.sma_indicator(close_series, window=5, fillna=False)
        df['SMA_20'] = ta.trend.sma_indicator(close_series, window=20, fillna=False)
        df['SMA_60'] = ta.trend.sma_indicator(close_series, window=60, fillna=False)
        
        # 動能指標 (RSI, StochRSI)
        df['RSI'] = ta.momentum.rsi(close_series, window=14, fillna=False)
        stoch_rsi = ta.momentum.StochRSIIndicator(close=close_series, window=14, smooth1=3, smooth2=3, fillna=False)
        df['StochRSI_K'] = stoch_rsi.stochrsi_k()
        df['StochRSI_D'] = stoch_rsi.stochrsi_d()

        # 波動性指標 (ATR)
        df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], close_series, window=14, fillna=False)

        # 交易量指標 (OBV)
        df['OBV'] = ta.volume.on_balance_volume(close_series, df['Volume'], fillna=False)

        # 清理並準備摘要表
        df.dropna(inplace=True) # 移除所有包含 NaN 的行 (即移除指標計算初期的空值)
        
        if df.empty:
            st.warning("⚠️ **數據不足:** 經過指標計算和 NaN 清理後，剩餘的數據點不足。請選擇更長的時間範圍或週期。")
            return pd.DataFrame(), pd.DataFrame()


        # 建立技術指標摘要
        latest = df.iloc[-1]
        tech_data = {
            '指標': ['最新價', 'SMA (5日)', 'SMA (20日)', 'SMA (60日)', 'RSI (14)', 'StochRSI K/D', 'ATR (14)', 'OBV'],
            '最新值': [
                latest['Close'], latest['SMA_5'], latest['SMA_20'], latest['SMA_60'], 
                latest['RSI'], f"{latest['StochRSI_K']:.2f} / {latest['StochRSI_D']:.2f}", 
                latest['ATR'], latest['OBV']
            ],
            '分析結論': [
                "市場價格",
                f"趨勢判讀 ({latest['Close']-latest['SMA_5']:.2f})",
                f"趨勢判讀 ({latest['Close']-latest['SMA_20']:.2f})",
                f"趨勢判讀 ({latest['Close']-latest['SMA_60']:.2f})",
                "動能強弱",
                "超買/超賣",
                "市場波動性",
                "交易量趨勢"
            ]
        }
        
        tech_df = pd.DataFrame(tech_data)

        # 趨勢/動能判讀邏輯
        def get_conclusion(row):
            if row['指標'] == '最新價': return '當前市場價格'
            
            # 趨勢判讀
            if row['指標'].startswith('SMA'):
                diff = latest['Close'] - latest[f"SMA_{row['指標'].split(' ')[1].replace('日', '')}"]
                if diff > 0: return f"多頭趨勢 ({diff:.2f}) - 價格在均線之上"
                if diff < 0: return f"空頭趨勢 ({diff:.2f}) - 價格在均線之下"
                return "中性趨勢 - 價格貼近均線"
            
            # RSI 判讀
            if row['指標'] == 'RSI (14)':
                if row['最新值'] > 70: return f"超買區 (>70) - 動能過強，留意回調"
                if row['最新值'] < 30: return f"超賣區 (<30) - 動能不足，留意反彈"
                return "中性區 (30-70)"

            # StochRSI 判讀 (只看 K 線)
            if row['指標'] == 'StochRSI K/D':
                k = latest['StochRSI_K']
                d = latest['StochRSI_D']
                if k > 80 and d > 80: return "高檔超買 (K,D > 80) - 潛在賣出信號"
                if k < 20 and d < 20: return "低檔超賣 (K,D < 20) - 潛在買入信號"
                if k > d and k < 80 and k > 50: return "多頭動能增強 (K > D)"
                if k < d and d > 20 and d < 50: return "空頭動能增強 (K < D)"
                return "中性動能/整理"
            
            # ATR/OBV
            if row['指標'] == 'ATR (14)':
                # 與前20日ATR比較判斷波動性
                avg_atr_20 = df['ATR'].iloc[-21:-1].mean() if len(df) >= 20 else 0
                if latest['ATR'] > avg_atr_20 * 1.5: return "高波動率 - 趨勢變化可能加速"
                if latest['ATR'] < avg_atr_20 * 0.5: return "低波動率 - 盤整待突破"
                return "正常波動率"

            if row['指標'] == 'OBV':
                obv_change = latest['OBV'] - df['OBV'].iloc[-2] if len(df) >= 2 else 0
                if obv_change > 0: return "多頭量能 (OBV 上升) - 買盤積極"
                if obv_change < 0: return "空頭量能 (OBV 下降) - 賣壓沉重"
                return "量能持平"
            
            return "N/A"

        tech_df['分析結論'] = tech_df.apply(get_conclusion, axis=1)

        # 顏色樣式函數
        def apply_color(row):
            style = 'background-color: '
            conclusion = row['分析結論']
            
            if '多頭' in conclusion or '買入信號' in conclusion or '上升' in conclusion or row['指標'] == '最新價':
                return [''] * len(row) # 價格不標色，其他指標用下面邏輯

            if row['指標'].startswith('SMA'):
                if '多頭' in conclusion: style += '#FFE7E7; color: #CC0000' # 淡紅 (強多頭)
                elif '空頭' in conclusion: style += '#E7F7E7; color: #008000' # 淡綠 (強空頭)
                else: style += '#FFF3E0; color: #E65100' # 淡橙 (中性)
            
            elif row['指標'] == 'RSI (14)':
                if '超買區' in conclusion: style += '#FFE7E7; color: #CC0000'
                elif '超賣區' in conclusion: style += '#E7F7E7; color: #008000'
                else: style += '#F0F0F0'
            
            elif row['指標'] == 'StochRSI K/D':
                if '高檔超買' in conclusion or '空頭動能增強' in conclusion: style += '#FFE7E7; color: #CC0000'
                elif '低檔超賣' in conclusion or '多頭動能增強' in conclusion: style += '#E7F7E7; color: #008000'
                else: style += '#F0F0F0'
                
            elif row['指標'] == 'OBV':
                if '多頭量能' in conclusion: style += '#FFE7E7; color: #CC0000'
                elif '空頭量能' in conclusion: style += '#E7F7E7; color: #008000'
                else: style += '#F0F0F0'
            else:
                style += 'white'

            return [style] * len(row)

        styled_tech_df = tech_df.style.apply(apply_color, axis=1)

        return df, styled_tech_df
        
    except Exception as e:
        # 兜底捕獲任何計算錯誤
        st.error(f"❌ **技術指標計算失敗:** 發生意外錯誤。錯誤信息: {e}")
        return pd.DataFrame(), pd.DataFrame()


# ------------------------------------------------------------------------------
# 3. 圖表生成函數
# ------------------------------------------------------------------------------

def create_comprehensive_chart(df, symbol, period_key):
    """創建包含 K 線、交易量、RSI、StochRSI 的綜合 Plotly 圖表。"""
    
    if df.empty:
        return go.Figure()

    # 創建子圖：3行，高度比例為 [4, 1, 1, 1]
    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05, 
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=(f'{SYMBOL_TO_NAME.get(symbol, symbol)} K線圖 ({period_key})', '交易量', 'RSI (14)', 'StochRSI (K/D)')
    )

    # 圖表 1: K 線圖
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='K線',
            increasing_line_color='#FF4B4B',  # 紅色上漲
            decreasing_line_color='#00B36B'   # 綠色下跌
        ), row=1, col=1
    )

    # 添加 SMA
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_5'], mode='lines', name='SMA 5', line=dict(color='#FFD700', width=1), opacity=0.8), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], mode='lines', name='SMA 20', line=dict(color='#ADD8E6', width=1), opacity=0.8), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_60'], mode='lines', name='SMA 60', line=dict(color='#FF69B4', width=1), opacity=0.8), row=1, col=1)
    
    # 圖表 2: 交易量
    colors_vol = ['#FF4B4B' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#00B36B' for i in range(len(df))]
    fig.add_trace(
        go.Bar(
            x=df.index, 
            y=df['Volume'], 
            name='成交量', 
            marker_color=colors_vol, 
            opacity=0.6
        ), row=2, col=1
    )

    # 圖表 3: RSI (14)
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI', line=dict(color='#1E90FF', width=1.5)), row=3, col=1)
    # 添加超買/超賣線
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1, name='RSI 70')
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1, name='RSI 30')
    fig.update_yaxes(range=[0, 100], row=3, col=1)

    # 圖表 4: StochRSI (K/D)
    fig.add_trace(go.Scatter(x=df.index, y=df['StochRSI_K'], mode='lines', name='StochRSI K', line=dict(color='#FFA500', width=1.5)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['StochRSI_D'], mode='lines', name='StochRSI D', line=dict(color='#8A2BE2', width=1.5, dash='dot')), row=4, col=1)
    # 添加超買/超賣線
    fig.add_hline(y=80, line_dash="dash", line_color="red", row=4, col=1)
    fig.add_hline(y=20, line_dash="dash", line_color="green", row=4, col=1)
    fig.update_yaxes(range=[0, 100], row=4, col=1)

    # 全局佈局調整
    fig.update_layout(
        height=900, 
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # 隱藏非 K 線圖的 x 軸標籤
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=3, col=1)
    fig.update_xaxes(showticklabels=True, row=4, col=1)

    # 隱藏交易量和技術指標的範圍選擇器
    fig.update_layout(
        xaxis2_rangeslider_visible=False,
        xaxis3_rangeslider_visible=False,
        xaxis4_rangeslider_visible=False,
    )
    
    # K線圖的Y軸設定
    fig.update_yaxes(title_text="價格 (USD/TWD)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1, showgrid=False)
    fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100])
    fig.update_yaxes(title_text="StochRSI", row=4, col=1, range=[0, 100])
    
    return fig

# ------------------------------------------------------------------------------
# 4. 數據搜索與選擇功能
# ------------------------------------------------------------------------------

def find_symbol_info(search_term):
    """根據輸入的代碼或名稱查找資產信息。"""
    search_term = search_term.strip().upper()
    
    # 1. 查找代碼完全匹配
    if search_term in FULL_SYMBOLS_MAP:
        return search_term, FULL_SYMBOLS_MAP[search_term]['name']

    # 2. 查找名稱或關鍵字部分匹配
    for symbol, data in FULL_SYMBOLS_MAP.items():
        if search_term in data['name'].upper() or any(search_term in k.upper() for k in data['keywords']):
            return symbol, data['name']
            
    # 3. 如果是純數字代碼，假設是台股
    if re.match(r'^\d{4}$', search_term):
        tw_symbol = f"{search_term}.TW"
        if tw_symbol in FULL_SYMBOLS_MAP:
             return tw_symbol, FULL_SYMBOLS_MAP[tw_symbol]['name']
        return tw_symbol, f"台股代碼 {search_term}"
        
    return search_term, f"自定義代碼 {search_term}"


# ------------------------------------------------------------------------------
# 5. Streamlit App 主體
# ------------------------------------------------------------------------------

def main_app():
    
    st.title("🤖 AI 趨勢分析儀表板 📈")

    # 側邊欄配置
    st.sidebar.title("🛠️ 分析參數設定")

    # 選擇資產類別
    asset_class = st.sidebar.selectbox(
        "選擇資產類別:",
        ["台股 (TW)", "美股 (US)", "加密貨幣 (Crypto)"],
        index=0, # 預設選中台股
        key='sidebar_asset_class'
    )

    # 根據類別篩選快速選擇清單
    filtered_symbols = {}
    if asset_class == "台股 (TW)":
        filtered_symbols = {s: d for s, d in FULL_SYMBOLS_MAP.items() if s.endswith('.TW')}
    elif asset_class == "美股 (US)":
        filtered_symbols = {s: d for s, d in FULL_SYMBOLS_MAP.items() if not (s.endswith('.TW') or s.endswith('-USD'))}
    elif asset_class == "加密貨幣 (Crypto)":
        filtered_symbols = {s: d for s, d in FULL_SYMBOLS_MAP.items() if s.endswith('-USD')}
        
    # 格式化下拉選單選項
    options = {f"{s} - {d['name']}": s for s, d in filtered_symbols.items()}
    options_list = list(options.keys())
    
    # 快速選擇下拉菜單
    selected_option = st.sidebar.selectbox(
        "快速選擇標的 (推薦):",
        options_list,
        index=options_list.index(f"{st.session_state.get('last_search_symbol', '2330.TW')} - {SYMBOL_TO_NAME.get(st.session_state.get('last_search_symbol', '2330.TW'), '台積電')}") 
            if st.session_state.get('last_search_symbol', '2330.TW') in SYMBOL_TO_NAME and f"{st.session_state.get('last_search_symbol', '2330.TW')} - {SYMBOL_TO_NAME.get(st.session_state.get('last_search_symbol', '2330.TW'))}" in options_list else 0,
        key='sidebar_quick_select'
    )
    
    # 手動輸入/確認代碼
    default_input = options[selected_option] if selected_option else st.session_state.get('last_search_symbol', "2330.TW")
    search_input = st.sidebar.text_input(
        "或手動輸入代碼/名稱 (如 2330.TW, NVDA, BTC-USD):", 
        value=default_input, 
        key='sidebar_search_input'
    )
    
    # 選擇分析週期
    period_keys = list(PERIOD_MAP.keys())
    selected_period_key = st.sidebar.selectbox(
        "選擇分析週期:",
        period_keys,
        index=period_keys.index("1 日 (中長線)"), # 預設選擇 '1 日 (中長線)'
        key='sidebar_period'
    )
    
    # 執行按鈕
    analyze_button_clicked = st.sidebar.button("📊 執行AI分析", type="primary")

    # 檢查是否已點擊執行按鈕，或者從 session_state 中恢復上一次的分析結果
    if analyze_button_clicked:
        st.session_state['data_ready'] = False # 重置狀態，開始新的分析
        st.session_state['last_search_symbol'] = search_input
    
    final_symbol_to_analyze, display_name = find_symbol_info(st.session_state.get('last_search_symbol', '2330.TW'))
    selected_period_key = st.session_state.get('sidebar_period', '1 日 (中長線)')

    if analyze_button_clicked or st.session_state.get('data_ready', False):
        
        # 覆蓋為當前選擇的代碼和週期
        if analyze_button_clicked:
            final_symbol_to_analyze, display_name = find_symbol_info(search_input)
            st.session_state['last_search_symbol'] = final_symbol_to_analyze # 確保 session state 更新
            st.session_state['sidebar_period'] = selected_period_key
            
        period, interval = PERIOD_MAP[selected_period_key]

        # 標題和資訊展示
        st.header(f"🚀 {final_symbol_to_analyze} - {display_name} AI 趨勢分析儀表板")
        st.markdown(f"分析週期: **{selected_period_key}** | 時間範圍: **{period}** | 數據間隔: **{interval}**")
        st.markdown("---")
        
        # 數據下載
        with st.spinner(f'正在獲取 {final_symbol_to_analyze} 數據，請稍候...'):
            df = download_data(final_symbol_to_analyze, period, interval)
            
        if not df.empty:
            st.session_state['data_ready'] = True
            
            # 技術指標計算
            df, styled_tech_df = calculate_technical_indicators(df)

            if df.empty:
                # 數據計算後仍為空，表示指標計算失敗或數據不足
                st.info("無法進行分析。請檢查您的數據源或時間範圍設定。")
                return # 提前退出
            
            # ==============================================================================
            # 6. 結果展示
            # ==============================================================================

            st.subheader("🤖 AI 趨勢核心摘要")
            
            # 簡單的趨勢判斷 (可替換為更複雜的 AI 邏輯)
            latest_close = df['Close'].iloc[-1]
            latest_sma20 = df['SMA_20'].iloc[-1]
            
            if latest_close > latest_sma20:
                trend_status = "🟢 **強勢多頭** (價格位於中長線支撐之上)"
                color_box = "#E6FFE6" # 淡綠
            elif latest_close < latest_sma20:
                trend_status = "🔴 **弱勢空頭** (價格位於中長線壓力之下)"
                color_box = "#FFE6E6" # 淡紅
            else:
                trend_status = "🟡 **中性整理** (價格貼近均線)"
                color_box = "#FFFFE0" # 淡黃
                
            st.markdown(
                f"""
                <div style="padding: 15px; border-radius: 10px; border: 1px solid #ccc; background-color: {color_box};">
                    <p style="font-size: 1.1em; font-weight: bold; margin-bottom: 5px;">當前技術分析判讀 (基於 {selected_period_key})：</p>
                    <p style="font-size: 1.5em; margin: 0;">{trend_status}</p>
                    <small>最新收盤價: {latest_close:.2f} | 20週期均線: {latest_sma20:.2f}</small>
                </div>
                """, unsafe_allow_html=True
            )
            
            st.markdown("---")
            
            st.subheader(f"🔢 關鍵技術指標數據表")
            
            # 展示技術指標表格 (使用 Streamlit 的 dataframe 功能)
            st.dataframe(
                styled_tech_df,
                use_container_width=True,
                column_config={
                    "最新值": st.column_config.Column("最新數值", help="技術指標的最新計算值"),
                    "分析結論": st.column_config.Column("趨勢/動能判讀", help="基於數值範圍的專業解讀"),
                }
            )
            st.caption("ℹ️ **設計師提示:** 表格顏色會根據指標的趨勢/風險等級自動變化（**紅色=多頭/強化信號**（類似低風險買入），**綠色=空頭/削弱信號**（類似高風險賣出），**橙色=中性/警告**）。")

        else:
            st.info("無足夠數據生成關鍵技術指標表格。")
        
        st.markdown("---")
        
        st.subheader(f"📊 完整技術分析圖表")
        chart = create_comprehensive_chart(df, final_symbol_to_analyze, selected_period_key) 
        
        st.plotly_chart(chart, use_container_width=True, key=f"plotly_chart_{final_symbol_to_analyze}_{selected_period_key}")

    elif not st.session_state.get('data_ready', False) and not analyze_button_clicked:
          
          st.info("歡迎使用 AI 趨勢分析儀表板！")
          st.markdown("請在左側選擇或輸入標的（例如：**2330.TW**、**NVDA**、**BTC-USD**），然後點擊 <span style='color: #FA8072; font-weight: bold;'>『📊 執行AI分析』</span> 按鈕開始。", unsafe_allow_html=True)
          
          st.markdown("---")
          
          st.subheader("📝 使用步驟：")
          st.markdown("1. **選擇資產類別**：在左側欄選擇 `美股`、`台股` 或 `加密貨幣`。")
          st.markdown("2. **選擇標的**：使用下拉選單快速選擇熱門標的，或直接在輸入框中鍵入代碼或名稱。")
          st.markdown("3. **選擇週期**：決定分析的長度（例如：`30 分`、`4 小時`、`1 日`、`1 周`）。")
          st.markdown(f"4. **執行分析**：點擊 <span style='color: #FA8072; font-weight: bold;'>『📊 執行AI分析』**</span>，AI將融合基本面與技術面指標提供交易策略。", unsafe_allow_html=True)
          
          st.markdown("---")


if __name__ == '__main__':
    # Streamlit Session State 初始化，確保變數存在
    if 'last_search_symbol' not in st.session_state:
        st.session_state['last_search_symbol'] = "2330.TW"
    if 'data_ready' not in st.session_state:
        st.session_state['data_ready'] = False
    if 'sidebar_search_input' not in st.session_state:
        st.session_state['sidebar_search_input'] = "2330.TW"
    if 'sidebar_period' not in st.session_state:
        st.session_state['sidebar_period'] = '1 日 (中長線)'
    if 'sidebar_asset_class' not in st.session_state:
        st.session_state['sidebar_asset_class'] = "台股 (TW)"

    main_app()
