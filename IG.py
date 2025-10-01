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
    "MSFT": {"name": "微軟", "keywords": ["微軟", "雲端", "MSFT", "Microsoft"]},
    "AAPL": {"name": "蘋果", "keywords": ["蘋果", "手機", "AAPL", "Apple"]},
    "AMZN": {"name": "亞馬遜", "keywords": ["亞馬遜", "電商", "AMZN", "Amazon"]},
    # ----------------------------------------------------
    # B. 台股精選 (TW Stocks) - 個股
    # ----------------------------------------------------
    "2330.TW": {"name": "台積電", "keywords": ["台積電", "晶圓", "2330", "TSMC"]},
    "2317.TW": {"name": "鴻海", "keywords": ["鴻海", "AI伺服器", "2317", "Foxconn"]},
    "0050.TW": {"name": "元大台灣50", "keywords": ["0050", "ETF", "台灣50"]},
    # ----------------------------------------------------
    # C. 加密貨幣 (Crypto) - 主流幣
    # ----------------------------------------------------
    "BTC-USD": {"name": "比特幣/美元", "keywords": ["比特幣", "BTC", "Bitcoin"]},
    "ETH-USD": {"name": "以太幣/美元", "keywords": ["以太幣", "ETH", "Ethereum"]},
    "BNB-USD": {"name": "幣安幣/美元", "keywords": ["幣安幣", "BNB", "Binance Coin"]},
}

ASSET_CATEGORIES = {
    "美股 (US)": ["TSLA", "NVDA", "MSFT", "AAPL", "AMZN"],
    "台股 (TW)": ["2330.TW", "2317.TW", "0050.TW"],
    "加密貨幣 (Crypto)": ["BTC-USD", "ETH-USD", "BNB-USD"],
}


# ==============================================================================
# 2. 資料獲取與處理
# ==============================================================================

@st.cache_data(ttl=60*10) # 緩存10分鐘
def fetch_stock_data(symbol, period, interval):
    """從 YFinance 獲取股價數據。"""
    try:
        # 增加重試機制
        for i in range(3):
            data = yf.download(symbol, period=period, interval=interval, progress=False)
            if not data.empty:
                break
            time.sleep(1) # 等待 1 秒後重試
            
        if data.empty:
            st.error(f"❌ 錯誤: 無法獲取 {symbol} 的數據。請檢查代碼或稍後再試。")
            return None
        
        # 清理欄位名稱
        data.columns = [col.replace(' ', '_') for col in data.columns]
        
        # 確保必要的欄位存在
        if 'Close' not in data.columns:
            st.error(f"數據結構異常，缺少 'Close' 欄位。")
            return None
            
        # 數據預處理 (TA-Lib 需要 float 類型)
        data['Close'] = data['Close'].astype(float)
        data['High'] = data['High'].astype(float)
        data['Low'] = data['Low'].astype(float)
        data['Open'] = data['Open'].astype(float)
        data['Volume'] = data['Volume'].astype(float)
        
        return data.dropna()
    except Exception as e:
        st.error(f"❌ 數據獲取過程中發生錯誤: {e}")
        return None

# ==============================================================================
# 3. 技術指標計算與分析
# ==============================================================================

def calculate_technical_indicators(df):
    """計算常用的技術指標並添加到 DataFrame。"""
    
    # 檢查是否有足夠的數據點
    if len(df) < 50: # 至少需要足夠的數據來計算例如 SMA(20), Bollinger Band(20) 等
        return None

    df = df.copy()

    # 趨勢指標 (Trend)
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['EMA_12'] = ta.trend.ema_indicator(df['Close'], window=12)
    df['EMA_26'] = ta.trend.ema_indicator(df['Close'], window=26)
    
    # 動能指標 (Momentum) - MACD
    macd = ta.trend.macd(df['Close'], window_fast=12, window_slow=26, window_sign=9)
    df['MACD'] = macd
    df['MACD_Signal'] = ta.trend.macd_signal(df['Close'], window_fast=12, window_slow=26, window_sign=9)
    df['MACD_Hist'] = ta.trend.macd_diff(df['Close'], window_fast=12, window_slow=26, window_sign=9)
    
    # 動能指標 (Momentum) - RSI
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    # 波動性指標 (Volatility) - Bollinger Bands
    bollinger = ta.volatility.bollinger_bands(df['Close'], window=20, window_dev=2)
    df['BB_High'] = bollinger.bollinger_hband()
    df['BB_Low'] = bollinger.bollinger_lband()
    df['BB_Mid'] = bollinger.bollinger_mavg()
    df['BB_Bandwidth'] = bollinger.bollinger_wband()
    
    # 交易量指標 (Volume) - OBV
    df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])

    return df.dropna()

def analyze_indicator_value(df):
    """
    對關鍵技術指標的最新數值進行分析判讀，並提供趨勢/風險結論。
    """
    
    # 確保 DataFrame 不為空
    if df is None or df.empty:
        return None

    # 取最新的數據行
    latest = df.iloc[-1]
    
    # 檢查必要的指標是否存在
    required_indicators = ['Close', 'SMA_20', 'SMA_50', 'MACD', 'MACD_Signal', 'RSI', 'BB_High', 'BB_Low', 'BB_Mid']
    if not all(ind in latest for ind in required_indicators):
        st.warning("技術指標計算數據不足，無法進行完整分析。")
        return None

    # --- 1. RSI (相對強弱指數) ---
    rsi_val = latest['RSI']
    if rsi_val > 70:
        rsi_conclusion = "🚨 超買/動能過熱"
        rsi_color = 'red'
    elif rsi_val < 30:
        rsi_conclusion = "🟢 超賣/動能低檔"
        rsi_color = 'green'
    elif rsi_val > 50:
        rsi_conclusion = "🟠 偏多頭動能"
        rsi_color = 'orange'
    else:
        rsi_conclusion = "🟡 偏空頭動能"
        rsi_color = 'yellow'
        
    # --- 2. MACD (移動平均線收斂與發散) ---
    macd_val = latest['MACD']
    macd_signal = latest['MACD_Signal']
    if macd_val > macd_signal and macd_val > 0:
        macd_conclusion = "🔴 多頭排列/動能強化"
        macd_color = 'red'
    elif macd_val < macd_signal and macd_val < 0:
        macd_conclusion = "🟢 空頭排列/動能削弱"
        macd_color = 'green'
    elif macd_val > macd_signal:
        macd_conclusion = "🟠 零軸上方金叉/看多"
        macd_color = 'orange'
    else:
        macd_conclusion = "🟡 零軸下方死叉/觀望"
        macd_color = 'yellow'
        
    # --- 3. 均線趨勢 (SMA 20/50) ---
    if latest['Close'] > latest['SMA_20'] and latest['SMA_20'] > latest['SMA_50']:
        ma_conclusion = "🔴 多頭趨勢/線形排列良好"
        ma_color = 'red'
    elif latest['Close'] < latest['SMA_20'] and latest['SMA_20'] < latest['SMA_50']:
        ma_conclusion = "🟢 空頭趨勢/線形排列惡化"
        ma_color = 'green'
    elif latest['Close'] > latest['SMA_20']:
        ma_conclusion = "🟠 短線偏多/留意長線壓力"
        ma_color = 'orange'
    else:
        ma_conclusion = "🟡 短線偏空/留意長線支撐"
        ma_color = 'yellow'
        
    # --- 4. 布林帶 (Bollinger Bands) ---
    bb_high = latest['BB_High']
    bb_low = latest['BB_Low']
    close_val = latest['Close']
    
    if close_val > bb_high:
        bb_conclusion = "🚨 突破上軌/短期強勢"
        bb_color = 'red'
    elif close_val < bb_low:
        bb_conclusion = "🟢 跌破下軌/短期超賣"
        bb_color = 'green'
    elif close_val > latest['BB_Mid']:
        bb_conclusion = "🟠 中軌上方/偏多震盪"
        bb_color = 'orange'
    else:
        bb_conclusion = "🟡 中軌下方/偏空震盪"
        bb_color = 'yellow'
        
    
    # 創建結果 DataFrame
    analysis_results = pd.DataFrame({
        '指標': ['RSI (14)', 'MACD (12, 26, 9)', '均線趨勢 (SMA 20/50)', '布林帶 (20)'],
        '最新值': [f"{rsi_val:.2f}", f"{macd_val:.2f}", f"收盤價 {close_val:.2f}", f"收盤價 {close_val:.2f}"],
        '分析結論': [rsi_conclusion, macd_conclusion, ma_conclusion, bb_conclusion],
        '顏色標籤': [rsi_color, macd_color, ma_color, bb_color]
    })
    
    return analysis_results

def create_indicator_table(analysis_df):
    """根據分析結果創建 Streamlit 表格，包含顏色標記。"""
    
    # 定義顏色映射
    color_map = {
        'red': '#FF4B4B',    # Streamlit Red
        'green': '#00B894',  # Streamlit Green (slightly darker/better contrast)
        'orange': '#FF8700', # Streamlit Orange
        'yellow': '#FFD700'  # Gold/Yellow
    }

    # 應用顏色樣式
    def color_rows(s):
        color = color_map.get(s['顏色標籤'], 'transparent')
        # 設置背景顏色
        return [f'background-color: {color}; color: #000000' if color != 'transparent' else ''] * len(s)

    # 隱藏顏色標籤列並應用樣式
    styled_df = analysis_df.style.apply(color_rows, axis=1)

    # 移除顏色標籤列
    display_df = analysis_df[['指標', '最新值', '分析結論']]

    return display_df

# ==============================================================================
# 4. 圖表視覺化
# ==============================================================================

def create_comprehensive_chart(df, symbol, period):
    """創建包含 K 線圖、RSI 和 MACD 的綜合 Plotly 圖表。"""
    
    # 檢查是否有足夠的數據點來繪圖
    if df is None or df.empty or 'RSI' not in df.columns or 'MACD' not in df.columns:
        st.warning("數據不足或指標計算失敗，無法繪製圖表。")
        return go.Figure()

    # 創建子圖：K 線圖+BB (row 1)，RSI (row 2)，MACD (row 3)
    fig = make_subplots(
        rows=3, 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2] # 調整圖表高度比例
    )

    # --- 1. K線圖與布林帶 (主圖) ---
    
    # K線圖
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='K線圖',
        increasing_line_color='red', # 陽線紅色
        decreasing_line_color='green' # 陰線綠色
    ), row=1, col=1)

    # 布林帶 (BB) 上軌
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['BB_High'], 
        line=dict(color='rgba(255, 165, 0, 0.5)', width=1), 
        name='BB上軌',
        showlegend=True
    ), row=1, col=1)

    # 布林帶 (BB) 中軌 (SMA_20)
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['BB_Mid'], 
        line=dict(color='rgba(100, 149, 237, 0.8)', width=1.5, dash='dash'), 
        name='BB中軌 (SMA 20)',
        showlegend=True
    ), row=1, col=1)

    # 布林帶 (BB) 下軌
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['BB_Low'], 
        line=dict(color='rgba(255, 165, 0, 0.5)', width=1), 
        name='BB下軌',
        fill='tonexty', # 填充上下軌之間
        fillcolor='rgba(255, 165, 0, 0.1)',
        showlegend=False
    ), row=1, col=1)

    # 均線 (SMA 50) - 作為長期趨勢線
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['SMA_50'], 
        line=dict(color='purple', width=1.5), 
        name='SMA 50 (長線趨勢)',
        showlegend=True
    ), row=1, col=1)

    # --- 2. RSI (動能圖) ---
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['RSI'], 
        line=dict(color='darkorange', width=1.5), 
        name='RSI',
        showlegend=True
    ), row=2, col=1)

    # 繪製 RSI 70/30 警戒線
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=2, col=1)
    
    # --- 3. MACD (動能圖) ---
    
    # MACD 柱狀圖 (Histogram)
    histogram_colors = ['red' if h >= 0 else 'green' for h in df['MACD_Hist']]
    fig.add_trace(go.Bar(
        x=df.index, 
        y=df['MACD_Hist'], 
        name='MACD 柱狀圖',
        marker_color=histogram_colors,
        showlegend=False
    ), row=3, col=1)
    
    # MACD 線
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['MACD'], 
        line=dict(color='blue', width=1.5), 
        name='MACD 線',
        showlegend=True
    ), row=3, col=1)
    
    # MACD 信號線
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['MACD_Signal'], 
        line=dict(color='orange', width=1.5), 
        name='Signal 線',
        showlegend=True
    ), row=3, col=1)
    
    # --- 全局配置與佈局 ---
    fig.update_layout(
        title=f"**{symbol}** - {period} 綜合技術分析圖表",
        xaxis_rangeslider_visible=False, # 隱藏底部時間軸滑塊
        hovermode="x unified",
        template="plotly_dark", # 使用暗色主題
        height=800, # 調整整體高度
        margin=dict(t=50, b=20, l=20, r=20),
    )

    # 調整 X/Y 軸設置
    fig.update_xaxes(
        showgrid=True, 
        gridwidth=1, 
        gridcolor='rgba(255,255,255,0.1)', 
        row=1, col=1
    )
    fig.update_yaxes(
        title_text='價格/K線', 
        showgrid=True, 
        gridwidth=1, 
        gridcolor='rgba(255,255,255,0.1)', 
        row=1, col=1
    )
    fig.update_yaxes(
        title_text='RSI', 
        range=[0, 100], 
        showgrid=True, 
        gridwidth=1, 
        gridcolor='rgba(255,255,255,0.1)', 
        row=2, col=1
    )
    fig.update_yaxes(
        title_text='MACD', 
        showgrid=True, 
        gridwidth=1, 
        gridcolor='rgba(255,255,255,0.1)', 
        row=3, col=1
    )
    
    return fig

# ==============================================================================
# 5. 側邊欄 UI 函數
# ==============================================================================

def get_asset_list(category_name):
    """根據資產類別獲取所有可用的標的代碼/名稱字典。"""
    asset_keys = ASSET_CATEGORIES.get(category_name, [])
    return {key: FULL_SYMBOLS_MAP[key]['name'] for key in asset_keys if key in FULL_SYMBOLS_MAP}

def get_quick_select_options(category_name):
    """獲取快速選擇下拉選單的選項 (代碼 - 名稱)。"""
    asset_list = get_asset_list(category_name)
    return {key: f"{key} - {name}" for key, name in asset_list.items()}

def get_default_period_key():
    """獲取預設的週期鍵值 (1 日)。"""
    return "1 日 (中長線)"

# ******************************************************************************
# 🌟 修正函數：確保快速選擇同步更新手動輸入框
# ******************************************************************************
def update_search_input():
    """
    回調函數：當快速選擇標的下拉選單的值改變時，
    自動將其代碼同步到 'sidebar_search_input' 的 Session State。
    """
    if 'quick_select_asset' in st.session_state:
        # st.session_state['quick_select_asset'] 的值是 "代碼 - 名稱"，我們需要提取代碼部分
        selected_option = st.session_state['quick_select_asset']
        # 提取代碼 (例如從 "MSFT - 微軟" 提取 "MSFT")
        symbol_code = selected_option.split(' - ')[0].strip()
        
        # 將提取出的代碼賦值給手動輸入框使用的 Session State 變數
        st.session_state['sidebar_search_input'] = symbol_code
        
        # 重設資料狀態，以便點擊分析時能重新下載
        st.session_state['data_ready'] = False
        
def main_app():
    """Streamlit 應用程式的主體。"""

    # --- 側邊欄 (Sidebar) ---
    st.sidebar.title("🛠️ 分析參數設定")

    # 1. 選擇資產類別
    asset_categories = list(ASSET_CATEGORIES.keys())
    selected_asset_category = st.sidebar.selectbox(
        "選擇資產類別:",
        options=asset_categories,
        index=asset_categories.index("美股 (US)"),
        key="asset_category"
    )

    # 根據資產類別獲取選項
    quick_select_symbols = get_quick_select_options(selected_asset_category)
    
    # 設置預設的快速選擇標的代碼 (例如 MSFT)
    default_quick_symbol_code = ASSET_CATEGORIES.get(selected_asset_category, ["MSFT"])[0] 
    
    # 根據預設代碼找到對應的顯示字串 (例如 MSFT - 微軟)
    default_quick_symbol_display = quick_select_symbols.get(default_quick_symbol_code, list(quick_select_symbols.values())[0])

    # 設置下拉選單的起始索引，使其與當前的 sidebar_search_input 保持一致 (如果可能)
    try:
        current_search_symbol = st.session_state.get('sidebar_search_input', default_quick_symbol_code)
        # 嘗試在當前類別的選項中找到與 'sidebar_search_input' 匹配的索引
        initial_index = list(quick_select_symbols.values()).index(quick_select_symbols.get(current_search_symbol, default_quick_symbol_display))
    except ValueError:
        # 如果當前的 'sidebar_search_input' 不在快速選擇列表中，則使用第一個選項
        initial_index = 0
    
    # 2. 快速選擇標的 (推薦)
    st.sidebar.selectbox(
        "快速選擇標的 (推薦):",
        options=list(quick_select_symbols.values()),
        index=initial_index,
        key='quick_select_asset', # 設置唯一的 key
        on_change=update_search_input # ** 關鍵：綁定回調函數 **
    )
    
    # 3. 手動輸入代碼/名稱
    # ⚠️ 這裡的 value 必須綁定到 Session State，以便被上方的 on_change 函數所控制。
    search_input = st.sidebar.text_input(
        "或手動輸入代碼/名稱 (如 2330.TW, NVDA, BTC-USD):",
        value=st.session_state.get('sidebar_search_input', default_quick_symbol_code), 
        key="sidebar_search_input" # 設置唯一的 key
    )
    
    # 確定最終用於分析的標的
    final_symbol_to_analyze = search_input.strip().upper()
    
    # 4. 選擇分析週期
    period_options = list(PERIOD_MAP.keys())
    selected_period_key = st.sidebar.selectbox(
        "選擇分析週期:",
        options=period_options,
        index=period_options.index(get_default_period_key()),
        key="selected_period_key"
    )

    # 5. 執行分析按鈕
    analyze_button_clicked = st.sidebar.button(
        "📊 執行AI分析", 
        use_container_width=True,
        type="primary"
    )
    
    # --- 主區域 (Main Content) ---

    if analyze_button_clicked or st.session_state.get('data_ready', False):
        if analyze_button_clicked:
            st.session_state['data_ready'] = False # 點擊後重設狀態
            
        if not final_symbol_to_analyze:
            st.error("請輸入或選擇有效的標的代碼。")
            return
            
        with st.spinner(f"正在分析 **{final_symbol_to_analyze}** 的 {selected_period_key} 數據..."):
            period_yf, interval_yf = PERIOD_MAP[selected_period_key]
            
            # 獲取數據
            df = fetch_stock_data(final_symbol_to_analyze, period_yf, interval_yf)
            
            if df is None or df.empty:
                st.session_state['data_ready'] = False
                st.error(f"無法取得 **{final_symbol_to_analyze}** 的數據。請檢查代碼或選擇更長的週期。")
                return
            
            # 計算指標 (這裡會更新 df)
            df_with_indicators = calculate_technical_indicators(df)
            
            if df_with_indicators is None:
                st.session_state['data_ready'] = False
                st.error("數據點不足 (少於 50 點) 無法計算技術指標。請選擇更長的分析週期。")
                return

            st.session_state['df_indicators'] = df_with_indicators
            st.session_state['data_ready'] = True
            st.session_state['last_search_symbol'] = final_symbol_to_analyze

        # 顯示結果
        st.markdown(f"## 📈 **{final_symbol_to_analyze}** ({selected_period_key}) AI技術分析")
        
        # 確保在非點擊時也能從 Session State 讀取數據
        df_display = st.session_state.get('df_indicators', pd.DataFrame())
        
        # --- 顯示關鍵指標分析 ---
        st.subheader("💡 關鍵技術指標判讀")
        
        analysis_df = analyze_indicator_value(df_display)
        
        if analysis_df is not None and not analysis_df.empty:
            
            display_df = create_indicator_table(analysis_df)
            
            # 使用 st.dataframe 呈現表格並設定欄位樣式
            st.dataframe(
                display_df,
                hide_index=True,
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
        chart = create_comprehensive_chart(df_display, final_symbol_to_analyze, selected_period_key) 
        
        st.plotly_chart(chart, use_container_width=True, key=f"plotly_chart_{final_symbol_to_analyze}_{selected_period_key}")

    elif not st.session_state.get('data_ready', False) and not analyze_button_clicked:
        # --- 初始歡迎畫面 ---
        st.markdown("# 歡迎使用 **🤖 AI趨勢分析儀表板**")
        st.markdown("---")
        st.markdown("### 快速掌握市場趨勢，讓 AI 成為您的交易夥伴！")
        
        st.markdown(f"請在左側選擇資產類別與標的（例如：**NVDA**、**BTC-USD**），然後點擊 <span style='color: #FA8072; font-weight: bold;'>『📊 執行AI分析』</span> 按鈕開始。", unsafe_allow_html=True)
          
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
        st.session_state['last_search_symbol'] = "MSFT" # 預設使用美股
    if 'data_ready' not in st.session_state:
        st.session_state['data_ready'] = False
    if 'sidebar_search_input' not in st.session_state:
        st.session_state['sidebar_search_input'] = "MSFT" # 預設手動輸入框的值
    
    main_app()
