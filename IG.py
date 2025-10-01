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
    "AAPL": {"name": "蘋果", "keywords": ["蘋果", "iPhone", "AAPL", "Apple"]},
    "MSFT": {"name": "微軟", "keywords": ["微軟", "雲端", "MSFT", "Microsoft"]},
    "GOOG": {"name": "谷歌 (A股)", "keywords": ["谷歌", "Google", "Alphabet", "GOOG"]},
    "AMZN": {"name": "亞馬遜", "keywords": ["亞馬遜", "電商", "AMZN", "Amazon"]},
    # ----------------------------------------------------
    # B. 台股核心 (TW Stocks) - 個股
    # ----------------------------------------------------
    "2330.TW": {"name": "台積電", "keywords": ["台積電", "晶圓", "2330", "TSMC"]},
    "2317.TW": {"name": "鴻海", "keywords": ["鴻海", "富士康", "2317", "Foxconn"]},
    "2454.TW": {"name": "聯發科", "keywords": ["聯發科", "MTK", "2454"]},
    # ----------------------------------------------------
    # C. 加密貨幣 (Crypto)
    # ----------------------------------------------------
    "BTC-USD": {"name": "比特幣", "keywords": ["比特幣", "BTC", "Bitcoin"]},
    "ETH-USD": {"name": "以太幣", "keywords": ["以太幣", "ETH", "Ethereum"]},
    "XRP-USD": {"name": "瑞波幣", "keywords": ["瑞波幣", "XRP", "Ripple"]},
}

# 資產類別映射
ASSET_CLASSES = {
    "美股": ["TSLA", "NVDA", "AAPL", "MSFT", "GOOG", "AMZN"],
    "台股": ["2330.TW", "2317.TW", "2454.TW"],
    "加密貨幣": ["BTC-USD", "ETH-USD", "XRP-USD"]
}

# ==============================================================================
# 2. 數據獲取與處理
# ==============================================================================

@st.cache_data(ttl=3600) # 數據快取一小時
def load_data(symbol, period, interval):
    """從 yfinance 下載歷史數據。"""
    # 使用 st.markdown 替代 st.info 避免渲染衝突
    st.markdown(f"🤖 正在從 Yahoo Finance 下載 **{symbol}** 的 {period} 數據 (週期: {interval})... 請稍候 ⏳")
    
    try:
        # 使用 auto_adjust=True 讓 yfinance 自動處理分割和股利調整
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        
        if df.empty:
            st.error(f"⚠️ 無法獲取 **{symbol}** 在 {interval} 週期下的數據。請檢查代碼或更換週期。")
            return None
        
        # **關鍵修正：修復 'tuple' object has no attribute 'capitalize' 錯誤**
        # 即使欄位是 MultiIndex 或 Tuple，先安全地轉成 string 再 capitalize
        df.columns = [str(col).capitalize() for col in df.columns]
        
        # 對於高頻數據（例如 30m, 60m），移除不必要的 'Volume' 0 值行
        if 'm' in interval or 'h' in interval:
            df = df[df['Volume'] > 0]

        st.success(f"✅ **{symbol}** 數據下載完成。共 {len(df)} 條紀錄。")
        return df
    
    except Exception as e:
        # 顯示更友好的錯誤信息
        st.error(f"❌ 下載數據時發生錯誤：{e}。請檢查網路連線或標的代碼。")
        return None

def add_technical_indicators(df):
    """計算所有關鍵技術指標。"""
    if df.empty:
        return df

    # --- 1. 趨勢指標 (Trend Indicators) ---
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['SMA_200'] = ta.trend.sma_indicator(df['Close'], window=200)
    
    macd = ta.trend.MACD(df['Close'], window_fast=12, window_slow=26, window_sign=9)
    df['MACD_Line'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff() # Histogram

    bollinger = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_High'] = bollinger.bollinger_hband()
    df['BB_Low'] = bollinger.bollinger_lband()
    df['BB_Mid'] = bollinger.bollinger_mavg()
    df['BB_Width'] = bollinger.bollinger_wband()

    # --- 2. 動能指標 (Momentum Indicators) ---
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close'], window=14, smooth_window=3)
    df['STOCH_K'] = stoch.stoch()
    df['STOCH_D'] = stoch.stoch_signal()

    adx = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'], window=14)
    df['ADX'] = adx.adx()
    df['DI_Plus'] = adx.adx_pos()
    df['DI_Minus'] = adx.adx_neg()

    # --- 3. 成交量指標 (Volume Indicators) ---
    df['OBV'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])

    # 移除計算指標所需的NaN值，但保留至少150根K線用於顯示
    df = df.dropna().tail(150) 
    
    return df

def analyze_indicator_status(df, indicator_name, period_key):
    """根據指標的最新值和週期，提供分析結論和顏色代碼。"""
    
    latest_value = df[indicator_name].iloc[-1]
    
    # 針對不同週期調整判讀策略
    if "日" in period_key or "週" in period_key:
        RSI_BULL_THRESHOLD = 55  
        RSI_BEAR_THRESHOLD = 45  
        ADX_TREND_THRESHOLD = 25 
    else:
        RSI_BULL_THRESHOLD = 60 
        RSI_BEAR_THRESHOLD = 40 
        ADX_TREND_THRESHOLD = 20 

    color_code = 'gray'
    conclusion = '中性'
    
    # --- 1. RSI (相對強弱指數) ---
    if indicator_name == 'RSI':
        if latest_value >= 70:
            conclusion = "🔴 強勢超買，有回調風險 (極度強勢)"
            color_code = 'red' 
        elif latest_value > RSI_BULL_THRESHOLD:
            conclusion = f"🟢 動能強勁，多頭佔優 (> {RSI_BULL_THRESHOLD})"
            color_code = 'green'
        elif latest_value < RSI_BEAR_THRESHOLD:
            conclusion = f"🔴 動能衰弱，空頭佔優 (< {RSI_BEAR_THRESHOLD})"
            color_code = 'red'
        elif latest_value <= 30:
            conclusion = "🟢 弱勢超賣，或有反彈需求 (極度弱勢)"
            color_code = 'green'
        else:
            conclusion = "⚪ 中性震盪，缺乏方向"
            color_code = 'gray'
            
    # --- 2. MACD 柱狀圖 (MACD_Hist) ---
    elif indicator_name == 'MACD_Hist':
        if latest_value > 0 and latest_value > df[indicator_name].iloc[-2]:
            conclusion = "🟢 多頭柱增長，動能持續強化"
            color_code = 'green'
        elif latest_value > 0 and latest_value <= df[indicator_name].iloc[-2]:
            conclusion = "⚪ 多頭柱收縮，動能減弱 (警惕)"
            color_code = 'gray'
        elif latest_value < 0 and latest_value < df[indicator_name].iloc[-2]:
            conclusion = "🔴 空頭柱擴大，下跌壓力增加"
            color_code = 'red'
        elif latest_value < 0 and latest_value >= df[indicator_name].iloc[-2]:
            conclusion = "⚪ 空頭柱收縮，下跌動能減緩 (警惕)"
            color_code = 'gray'
        else:
            conclusion = "⚪ 中性或零軸附近震盪"
            color_code = 'gray'

    # --- 3. ADX (平均趨向指數) ---
    elif indicator_name == 'ADX':
        di_plus = df['DI_Plus'].iloc[-1]
        di_minus = df['DI_Minus'].iloc[-1]

        if latest_value >= ADX_TREND_THRESHOLD:
            trend_strength = "強勁趨勢 (ADX > 25)"
        elif latest_value >= 15:
            trend_strength = "有趨勢形成跡象 (ADX > 15)"
        else:
            trend_strength = "無明顯趨勢 (ADX < 15)"

        if di_plus > di_minus and di_plus > ADX_TREND_THRESHOLD:
            conclusion = f"🟢 {trend_strength}，買方動能極強 (+DI主導)"
            color_code = 'green'
        elif di_minus > di_plus and di_minus > ADX_TREND_THRESHOLD:
            conclusion = f"🔴 {trend_strength}，賣方動能極強 (-DI主導)"
            color_code = 'red'
        else:
            conclusion = f"⚪ {trend_strength}，多空雙方力量均衡"
            color_code = 'gray'

    # --- 4. 價格與移動平均線 (Close Price vs. MAs) ---
    elif indicator_name == 'Price vs MA':
        close_price = df['Close'].iloc[-1]
        ma_50 = df['SMA_50'].iloc[-1]
        ma_200 = df['SMA_200'].iloc[-1]
        
        # 排除短期週期沒有200MA的情況
        if np.isnan(ma_200) or np.isnan(ma_50):
            conclusion = "數據不足或短期週期，無法判斷長期趨勢"
            color_code = 'gray'
        elif close_price > ma_50 and close_price > ma_200:
            conclusion = "🟢 長短期均線之上，多頭趨勢確立"
            color_code = 'green'
        elif close_price < ma_50 and close_price < ma_200:
            conclusion = "🔴 長短期均線之下，空頭趨勢確立"
            color_code = 'red'
        else:
            conclusion = "⚪ 價格在均線間震盪，趨勢不明確"
            color_code = 'gray'
            
    # --- 5. 隨機指標 (STOCH_K vs. STOCH_D) ---
    elif indicator_name == 'STOCH_K':
        k = latest_value
        d = df['STOCH_D'].iloc[-1]
        
        if k > d and k < 80:
            conclusion = "🟢 K線向上穿越D線，買入信號 (未超買)"
            color_code = 'green'
        elif k < d and k > 20:
            conclusion = "🔴 K線向下穿越D線，賣出信號 (未超賣)"
            color_code = 'red'
        elif k >= 80 and k > d:
            conclusion = "🔴 超買區多頭，警惕回調風險"
            color_code = 'red'
        elif k <= 20 and k < d:
            conclusion = "🟢 超賣區空頭，警惕反彈機會"
            color_code = 'green'
        else:
            conclusion = "⚪ 中性盤整"
            color_code = 'gray'

    # 格式化輸出
    if indicator_name == 'Price vs MA':
        latest_str = f"C:{df['Close'].iloc[-1]:.2f} / MA50:{df['SMA_50'].iloc[-1]:.2f} / MA200:{df['SMA_200'].iloc[-1]:.2f}"
    else:
        latest_str = f"{latest_value:.2f}"
    
    return latest_str, conclusion, color_code

# ==============================================================================
# 3. 圖表生成函數
# ==============================================================================

def create_comprehensive_chart(df, symbol, period_key):
    """生成包含 K線、MACD、RSI、ADX 的綜合圖表。"""
    
    # 創建四個子圖：K線、MACD、RSI、ADX
    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        row_heights=[0.5, 0.15, 0.15, 0.20], # 調整各子圖高度
        subplot_titles=(f'{symbol} K線圖與趨勢線 ({period_key})', 'MACD 動能指標', 'RSI 相對強弱指數', 'ADX 趨勢強度與方向')
    )

    # --- Subplot 1: K線圖 & 趨勢指標 ---
    fig.add_trace(go.Candlestick(
        x=df.index, 
        open=df['Open'], high=df['High'], 
        low=df['Low'], close=df['Close'],
        name='K線',
        increasing_line_color='#FF4B4B', # Streamlit Red
        decreasing_line_color='#00B336' # Streamlit Green
    ), row=1, col=1)

    # 繪製均線
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='#FFD700', width=1.5), name='SMA 50'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_200'], line=dict(color='#1E90FF', width=2), name='SMA 200'), row=1, col=1)
    
    # 繪製布林帶
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], line=dict(color='rgba(128, 128, 128, 0.5)', width=1), name='BB Upper', showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], line=dict(color='rgba(128, 128, 128, 0.5)', width=1), name='BB Lower', showlegend=False), row=1, col=1)


    # --- Subplot 2: MACD ---
    colors = ['#00B336' if val >= 0 else '#FF4B4B' for val in df['MACD_Hist']]
    
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='MACD Hist', marker_color=colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Line'], line=dict(color='#FF4B4B', width=1.5), name='MACD Line'), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='#FFD700', width=1.5, dash='dash'), name='Signal Line'), row=2, col=1)
    fig.update_yaxes(title_text='MACD', row=2, col=1)
    
    # --- Subplot 3: RSI ---
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#1E90FF', width=1.5), name='RSI'), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#FF4B4B", row=3, col=1) # 超買
    fig.add_hline(y=30, line_dash="dash", line_color="#00B336", row=3, col=1) # 超賣
    fig.update_yaxes(title_text='RSI', range=[0, 100], row=3, col=1)

    # --- Subplot 4: ADX and Directional Indicators ---
    fig.add_trace(go.Scatter(x=df.index, y=df['ADX'], line=dict(color='rgba(255, 255, 255, 0.8)', width=1.5), name='ADX', fill='tozeroy', fillcolor='rgba(100, 100, 100, 0.1)'), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['DI_Plus'], line=dict(color='#00B336', width=1.5), name='+DI'), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['DI_Minus'], line=dict(color='#FF4B4B', width=1.5), name='-DI'), row=4, col=1)
    fig.add_hline(y=25, line_dash="dot", line_color="#FFD700", row=4, col=1) # 趨勢線
    fig.update_yaxes(title_text='ADX', range=[0, 100], row=4, col=1)
    
    # --- 全局佈局設定 ---
    fig.update_layout(
        height=900, 
        xaxis_rangeslider_visible=False,
        template="plotly_dark", # 深色主題
        title_font_size=20,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # 隱藏非K線圖的X軸標籤
    fig.update_xaxes(showticklabels=True, row=4, col=1) # 只有最底層顯示X軸
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=3, col=1)

    return fig

# ==============================================================================
# 4. Streamlit UI 介面與主邏輯
# ==============================================================================

# ----------------------------------------------------
# 側邊欄 UI
# ----------------------------------------------------
def sidebar_ui():
    st.sidebar.markdown(
        """
        <style>
        .stButton>button {
            width: 100%;
            background-color: #FA8072; /* Salmon Pink */
            color: white;
            font-weight: bold;
            border-radius: 8px;
            border: none;
            padding: 10px;
            transition: all 0.2s;
        }
        .stButton>button:hover {
            background-color: #E6675B;
        }
        </style>
        """, unsafe_allow_html=True)
    
    st.sidebar.header("⚙️ 數據與參數設置")
    
    # 1. 選擇資產類別
    asset_class = st.sidebar.selectbox("選擇資產類別", list(ASSET_CLASSES.keys()))

    # 2. 快速選擇標的 (下拉式選單)
    suggested_symbols = ASSET_CLASSES.get(asset_class, [])
    # 讓用戶可以快速選擇，但預設為上次搜尋的值或第一個建議值
    default_symbol_key = st.session_state.get('last_search_symbol', suggested_symbols[0] if suggested_symbols else "2330.TW")
    
    # 確保預設值在下拉選單中
    if default_symbol_key not in suggested_symbols:
         if suggested_symbols:
              suggested_symbols.insert(0, default_symbol_key)
         else:
              suggested_symbols.append(default_symbol_key)
    
    # 找出預設值在建議列表中的位置
    try:
        default_index = suggested_symbols.index(default_symbol_key)
    except ValueError:
        default_index = 0

    selected_quick_symbol = st.sidebar.selectbox(
        "快速選擇標的",
        options=suggested_symbols,
        index=default_index,
        key="quick_select_symbol"
    )

    # 3. 直接輸入代碼 (或名稱)
    symbol_input = st.sidebar.text_input(
        f"或 3. 直接輸入代碼 (e.g., {selected_quick_symbol})",
        value=st.session_state.get('sidebar_search_input', selected_quick_symbol),
        placeholder="輸入代碼，例如：NVDA, TSLA, 2330.TW",
        key="symbol_text_input"
    )

    # 決定最終要分析的標的
    final_symbol_to_analyze = symbol_input.upper().strip() if symbol_input.strip() else selected_quick_symbol.upper().strip()

    # 4. 選擇分析週期
    selected_period_key = st.sidebar.selectbox(
        "選擇分析週期",
        options=list(PERIOD_MAP.keys()),
        index=list(PERIOD_MAP.keys()).index(st.session_state.get('last_period', "1 日 (中長線)")),
        key="period_select"
    )
    period, interval = PERIOD_MAP[selected_period_key]

    # 5. 執行按鈕
    analyze_button_clicked = st.sidebar.button("📊 執行AI分析")
    
    return final_symbol_to_analyze, period, interval, selected_period_key, analyze_button_clicked

# ----------------------------------------------------
# 主 UI 邏輯
# ----------------------------------------------------
def main():
    
    # 獲取側邊欄參數和按鈕狀態
    final_symbol_to_analyze, period, interval, selected_period_key, analyze_button_clicked = sidebar_ui()
    
    # 更新 session state 中的最新輸入
    if analyze_button_clicked:
        st.session_state['last_search_symbol'] = final_symbol_to_analyze
        st.session_state['last_period'] = selected_period_key
        # 清除舊數據狀態
        st.session_state['data_ready'] = False

    # 標題
    st.title("🤖 AI 趨勢分析儀表板 📈")
    st.markdown("---")

    # 檢查是否需要執行分析
    if analyze_button_clicked or st.session_state.get('data_ready', False):
        
        # 步驟 1: 數據獲取與處理
        df = load_data(final_symbol_to_analyze, period, interval)
        
        if df is None or df.empty:
            st.session_state['data_ready'] = False
            return # 數據錯誤，終止執行

        # 步驟 2: 計算技術指標
        df = add_technical_indicators(df)
        
        if df.empty:
            st.error("⚠️ 數據量不足，無法計算完整的技術指標（至少需要200個週期）。請嘗試更長的分析週期。")
            st.session_state['data_ready'] = False
            return
            
        st.session_state['data_ready'] = True
        
        # 步驟 3: 顯示分析結果
        st.subheader(f"✅ {final_symbol_to_analyze} - {selected_period_key} 關鍵技術指標分析")
        
        # 核心指標列表 (名稱, 資料欄位名稱)
        key_indicators = [
            ("價格與長期均線", "Price vs MA"), 
            ("RSI (14)", "RSI"),
            ("MACD 柱狀圖", "MACD_Hist"),
            ("STOCH K線", "STOCH_K"),
            ("ADX (14)", "ADX")
        ]
        
        # 建立結果表格
        results = []
        for display_name, data_col in key_indicators:
            if data_col in df.columns or data_col == "Price vs MA":
                latest_value_str, conclusion, color_code = analyze_indicator_status(df, data_col, selected_period_key)
                results.append({
                    "指標名稱": display_name,
                    "最新值": latest_value_str,
                    "分析結論": conclusion,
                    "顏色代碼": color_code 
                })

        if results:
            results_df = pd.DataFrame(results)
            
            # 定義表格顏色樣式
            def color_cells(row):
                style = [''] * len(row)
                color = row['顏色代碼']
                
                if color == 'green':
                    style[2] = 'background-color: #D4EDDA; color: #155724; font-weight: bold;'
                elif color == 'red':
                    style[2] = 'background-color: #F8D7DA; color: #721C24; font-weight: bold;'
                elif color == 'gray':
                    style[2] = 'background-color: #E2E3E5; color: #383D41;'
                
                return style

            st.dataframe(
                results_df.drop(columns=['顏色代碼']).style.apply(color_cells, axis=1),
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
        chart = create_comprehensive_chart(df, final_symbol_to_analyze, selected_period_key) 
        
        st.plotly_chart(chart, use_container_width=True, key=f"plotly_chart_{final_symbol_to_analyze}_{selected_period_key}")

    # 應用程式啟動或未點擊按鈕時的提示訊息 (已修正)
    elif not st.session_state.get('data_ready', False) and not analyze_button_clicked:
          
          st.markdown("""
              <div style='
                  padding: 10px; 
                  border-radius: 5px; 
                  background-color: #D6ECF0; /* Light info-like color */
                  color: #31708f; /* Info-like text color */
                  border-left: 5px solid #31708f;'>
                  請在左側選擇或輸入標的（例如：<strong>2330.TW</strong>、<strong>NVDA</strong>、<strong>BTC-USD</strong>），然後點擊 <span style='color: #FA8072; font-weight: bold;'>『📊 執行AI分析』</span> 按鈕開始。
              </div>
          """, unsafe_allow_html=True)
          
          st.markdown("---")
          
          st.subheader("📝 使用步驟：")
          st.markdown("1. **選擇資產類別**：在左側欄選擇 `美股`、`台股` 或 `加密貨幣`。")
          st.markdown("2. **選擇標的**：使用下拉選單快速選擇熱門標的，或直接在輸入框中鍵入代碼或名稱。")
          st.markdown("3. **選擇週期**：決定分析的長度（例如：`30 分 (短期)`、`4 小時 (波段)`、`1 日 (中長線)`）。")
          st.markdown("4. **執行分析**：點擊 <span style='color: #FA8072; font-weight: bold;'>『📊 執行AI分析』</span>，AI將融合技術指標提供交易策略。", unsafe_allow_html=True)
          
          st.markdown("---")


if __name__ == '__main__':
    # Streamlit Session State 初始化，確保變數存在
    if 'last_search_symbol' not in st.session_state:
        st.session_state['last_search_symbol'] = "2330.TW"
    if 'data_ready' not in st.session_state:
        st.session_state['data_ready'] = False
    if 'sidebar_search_input' not in st.session_state:
        st.session_state['sidebar_search_input'] = ""
    if 'last_period' not in st.session_state:
        st.session_state['last_period'] = "1 日 (中長線)"
        
    main()
