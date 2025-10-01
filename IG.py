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

# 抑制 ta 庫可能發出的警告
warnings.filterwarnings('ignore')

# ==============================================================================
# 1. 頁面配置與全局設定
# ==============================================================================

st.set_page_config(
    page_title="🤖 AI趨勢分析儀表板 📈", 
    page_icon="📈", 
    layout="wide"
)

# --- 🚀 自定義 IG 輪播圖樣式 (完全貼合設計模板) ---
CUSTOM_IG_CSS = """
<style>
/* 核心配色與字體 */
:root {
    --bg-dark: #0B172A;        /* 深色科技風背景 */
    --trend-blue: #00A3FF;     /* 趨勢藍 (買入) */
    --alert-orange: #FF4D00;   /* 警示橙 (賣出) */
    --text-white: #FFFFFF;     /* 純白色文字 */
    --text-light: #99AABB;     /* 次要文字 */
    --card-dark: #11213A;      /* 參數卡片背景 */
    --line-color: #1f304f;     /* 分隔線 */
    --font-family: 'Inter', sans-serif;
}

/* Page 1, 2, 3 共同容器樣式 */
.ig-page {
    background-color: var(--bg-dark); 
    color: var(--text-white);
    padding: 30px;
    margin-bottom: 25px;
    border-radius: 16px;
    min-height: 480px; /* 確保 IG 視覺高度一致性 */
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    font-family: var(--font-family);
}
.ig-page h1, .ig-page h2, .ig-page h3, .ig-page h4 {
    color: var(--text-white);
    font-weight: 800;
}

/* --- Page 1 結論頁樣式 --- */
.page1-header {
    text-align: center;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 2px solid var(--line-color);
}
.page1-header h1 { /* 標的代碼 */
    font-size: 2.5rem;
    margin: 0;
    line-height: 1.2;
}
.page1-header h4 { /* 標的名稱 */
    color: var(--text-light);
    font-size: 1.1rem;
    font-weight: 500;
    margin-bottom: 5px;
}

/* AI 結論：極致突出，比標題大 30% (約 4.5rem) */
.ai-conclusion-buy {
    font-size: 4.8rem; 
    font-weight: 900;
    color: var(--trend-blue); 
    text-align: center;
    line-height: 1.1;
    margin: 20px 0 30px 0;
    text-shadow: 0 0 15px rgba(0, 163, 255, 0.7);
}
.ai-conclusion-sell {
    font-size: 4.8rem;
    font-weight: 900;
    color: var(--alert-orange); 
    text-align: center;
    line-height: 1.1;
    margin: 20px 0 30px 0;
    text-shadow: 0 0 15px rgba(255, 77, 0, 0.7);
}
.ai-conclusion-hold {
    font-size: 4.8rem;
    font-weight: 900;
    color: var(--text-light); 
    text-align: center;
    line-height: 1.1;
    margin: 20px 0 30px 0;
}

/* 交易參數表格樣式 */
.trade-params {
    background-color: var(--card-dark);
    border-radius: 10px;
    padding: 15px 25px;
}
.param-row {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--line-color);
}
.param-row:last-child {
    border-bottom: none;
}
.param-label {
    font-weight: 600;
    color: var(--text-light);
    font-size: 1.1rem;
}
.param-value {
    font-weight: 700;
    color: var(--text-white);
    font-size: 1.1rem;
}
.param-value.tp { color: var(--trend-blue); }
.param-value.sl { color: var(--alert-orange); }

/* 導流提示 (Page 1 & 2 底部) */
.cta-tip {
    text-align: right;
    font-size: 1.2rem;
    color: var(--trend-blue); 
    margin-top: 15px;
    font-weight: 700;
}

/* --- Page 2 數據驗證樣式 --- */
.page2-validation-header {
    text-align: center;
    color: var(--trend-blue);
    margin-bottom: 20px;
}
.indicator-table-sim {
    background-color: var(--card-dark);
    border-radius: 10px;
    padding: 15px;
}
.indicator-row {
    display: flex;
    padding: 12px 0;
    border-bottom: 1px solid var(--line-color);
    font-size: 1.05rem;
}
.indicator-row:last-child {
    border-bottom: none;
}
.indicator-name {
    width: 30%;
    font-weight: 600;
    color: var(--text-light);
}
.indicator-value {
    width: 25%;
    font-weight: 700;
    text-align: right;
}
.indicator-summary {
    width: 45%;
    font-weight: 500;
    text-align: right;
}

/* 顏色編碼 */
.color-red { color: #FF4B4B; } /* 多頭/強化信號 */
.color-green { color: #00FF00; } /* 空頭/削弱信號 */
.color-orange { color: #FFA500; } /* 中性/警告 */

/* --- Page 3 行動呼籲樣式 --- */
.page3-cta {
    text-align: center;
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.cta-main-title {
    font-size: 3.5rem;
    color: var(--text-white);
    line-height: 1.2;
    margin-bottom: 10px;
}
.cta-main-action {
    font-size: 4.5rem;
    color: var(--trend-blue);
    font-weight: 900;
    margin-bottom: 40px;
    text-shadow: 0 0 10px rgba(0, 163, 255, 0.5);
}
.cta-link-instruction {
    font-size: 1.5rem;
    color: var(--text-light);
    margin-top: 20px;
}
.disclaimer {
    text-align: center;
    font-size: 0.8rem;
    color: #445566;
    padding-top: 15px;
    border-top: 1px solid var(--line-color);
}
</style>
"""
st.markdown(CUSTOM_IG_CSS, unsafe_allow_html=True)


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
    "TSLA": {"name": "特斯拉", "keywords": ["特斯拉", "電動車", "TSLA", "Tesla"], "category": "美股"},
    "NVDA": {"name": "輝達", "keywords": ["輝達", "英偉達", "AI", "NVDA", "Nvidia"], "category": "美股"},
    "AAPL": {"name": "蘋果", "keywords": ["蘋果", "手機", "AAPL", "Apple"], "category": "美股"},
    "GOOGL": {"name": "Google (A股)", "keywords": ["Google", "字母", "GOOGL"], "category": "美股"},
    "MSFT": {"name": "微軟", "keywords": ["微軟", "雲端", "MSFT", "Microsoft"], "category": "美股"},
    "AMZN": {"name": "亞馬遜", "keywords": ["亞馬遜", "電商", "AMZN", "Amazon"], "category": "美股"},
    # ----------------------------------------------------
    # B. 台股核心 (Taiwan Stocks) - 個股
    # ----------------------------------------------------
    "2330.TW": {"name": "台積電", "keywords": ["台積電", "晶圓", "2330"], "category": "台股"},
    "2303.TW": {"name": "聯電", "keywords": ["聯電", "2303"], "category": "台股"},
    "2454.TW": {"name": "聯發科", "keywords": ["聯發科", "2454"], "category": "台股"},
    "0050.TW": {"name": "元大台灣50", "keywords": ["0050", "台灣50", "ETF"], "category": "台股"},
    # ----------------------------------------------------
    # C. 加密貨幣 (Crypto)
    # ----------------------------------------------------
    "BTC-USD": {"name": "比特幣", "keywords": ["比特幣", "BTC", "Bitcoin", "加密"], "category": "加密貨幣"},
    "ETH-USD": {"name": "以太幣", "keywords": ["以太幣", "ETH", "Ethereum", "加密"], "category": "加密貨幣"},
}

# ==============================================================================
# 2. 數據獲取與處理
# ==============================================================================

@st.cache_data(ttl=3600)
def get_data(symbol, period, interval):
    """從 yfinance 獲取股價數據和公司名稱。"""
    error_msg = ""
    name = symbol 
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        name = info.get('longName') or info.get('shortName') or symbol

        df = ticker.history(period=period, interval=interval, auto_adjust=True)
        
        if df.empty or len(df) < 30: 
            error_msg = f"錯誤：無法獲取 {symbol} 的足夠數據。請檢查代碼或時間週期/區間設置。"
            return pd.DataFrame(), name, error_msg

        df.columns = [col.capitalize() for col in df.columns]
        
        return df, name, ""
        
    except Exception as e:
        error_msg = f"數據獲取失敗（{symbol}）：{e.__class__.__name__} - {e}"
        return pd.DataFrame(), name, error_msg


def calculate_indicators(df):
    """計算並添加常用的技術分析指標。"""
    
    # 趨勢指標 (Trend Indicators)
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA_60'] = ta.trend.sma_indicator(df['Close'], window=60)
    
    # MACD
    macd_indicator = ta.trend.MACD(df['Close'], window_fast=12, window_slow=26, window_sign=9)
    df['MACD'] = macd_indicator.macd()
    df['MACD_Signal'] = macd_indicator.macd_signal()
    df['MACD_Hist'] = macd_indicator.macd_diff()
    
    # 動能指標 (Momentum Indicators)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    stoch_rsi_indicator = ta.momentum.StochRSI(df['Close'], window=14, smooth1=3, smooth2=3)
    df['StochRSI_K'] = stoch_rsi_indicator.stochrsi_k() * 100
    df['StochRSI_D'] = stoch_rsi_indicator.stochrsi_d() * 100
    
    # 波動性指標 (Volatility Indicators)
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    
    df.dropna(inplace=True) 
    
    return df

# ==============================================================================
# 3. AI 核心判讀與交易策略生成
# ==============================================================================

def determine_ai_signal(df):
    """
    基於多指標的組合判斷，生成明確的 BUY/SELL/HOLD 信號與交易參數。
    """
    if df.empty:
        return "HOLD", {"Entry": 0, "TP": 0, "SL": 0, "Latest": 0}

    latest = df.iloc[-1]
    close = latest['Close']
    atr = latest['ATR']
    
    if np.isnan(atr) or atr <= 0:
        atr = close * 0.02 

    # 交易參數計算 (基於 ATR 動態風險管理)
    signal = "HOLD"
    
    # --- BUY 信號判斷 ---
    buy_condition_1 = latest['MACD_Hist'] > 0 
    buy_condition_2 = latest['RSI'] > 50 or latest['StochRSI_K'] > latest['StochRSI_D'] 
    buy_condition_3 = close > latest['SMA_20'] 
    
    if buy_condition_1 and buy_condition_2 and buy_condition_3:
        signal = "BUY"
    
    # --- SELL 信號判斷 ---
    sell_condition_1 = latest['MACD_Hist'] < 0 
    sell_condition_2 = latest['RSI'] < 50 or latest['StochRSI_K'] < latest['StochRSI_D'] 
    sell_condition_3 = close < latest['SMA_20'] 

    if sell_condition_1 and sell_condition_2 and sell_condition_3:
        signal = "SELL"
        
    # --- 交易參數計算 ---
    if signal == "BUY":
        entry = close * 1.001 # 略高於現價作為入場參考
        tp = entry + (atr * 3) # 3倍 ATR 止盈
        sl = entry - (atr * 2) # 2倍 ATR 止損
    elif signal == "SELL":
        entry = close * 0.999 # 略低於現價作為入場參考
        tp = entry - (atr * 3)
        sl = entry + (atr * 2)
    else: # HOLD
        entry = close
        tp = close 
        sl = close
        
    params = {
        "Latest": close,
        "Entry": entry,
        "TP": tp,
        "SL": sl
    }
    
    # 格式化數字 (保留小數點後兩位或三位，取決於價格大小)
    for key in params:
        # 使用一個簡單的邏輯：如果價格大於 100，保留兩位；否則保留三位
        decimal_places = 2 if params[key] > 100 else 3
        params[key] = float(f"{params[key]:.{decimal_places}f}")

    return signal, params

# ==============================================================================
# 4. IG 輪播圖視覺化渲染 (遵循設計模板)
# ==============================================================================

def render_ig_carousel_view(symbol, name, period_key, signal, params, data_to_display):
    """
    渲染三頁 IG 輪播圖的 HTML 結構。
    """
    st.header(f"📸 IG 輪播圖預覽 (請單獨截圖以下三個區塊)")
    st.caption("🚨 **重要提示:** 請務必放大瀏覽器視窗至全螢幕，並確保每個區塊完整顯示後再進行截圖，以確保最佳解析度。")
    st.markdown("---")


    # --- Page 1: 趨勢信號卡 (結論頁) ---
    st.markdown("### 1. 趨勢信號卡 (Page 1)")
    page_1_html = f"""
    <div class="ig-page">
        <div>
            <div class="page1-header">
                <h4>{name} ({period_key})</h4>
                <h1>${symbol}</h1>
            </div>
            
            <!-- AI 結論：極致突出 -->
            <p class="ai-conclusion-{signal.lower()}">
                {signal}
            </p>
        </div>
        
        <div class="trade-params">
            <h4 style="color: var(--trend-blue); text-align: center; margin-bottom: 15px; font-weight: 700;">交易參數 (最新數據)</h4>
            <div class="param-row">
                <span class="param-label">最新價格 (Last Close)</span>
                <span class="param-value">${params['Latest']}</span>
            </div>
            <div class="param-row">
                <span class="param-label">入場參考 (Entry)</span>
                <span class="param-value">${params['Entry']}</span>
            </div>
            <div class="param-row">
                <span class="param-label">止盈價格 (TP)</span>
                <span class="param-value tp">${params['TP']}</span>
            </div>
            <div class="param-row">
                <span class="param-label">止損價格 (SL)</span>
                <span class="param-value sl">${params['SL']}</span>
            </div>
        </div>

        <div class="cta-tip">
            詳情見 App，請向左滑動 → (AI 眼 LOGO 浮水印)
        </div>
    </div>
    """
    st.markdown(page_1_html, unsafe_allow_html=True)
    st.markdown("---")


    # --- Page 2: 儀表板數據驗證 (信任頁) ---
    st.markdown("### 2. 儀表板數據驗證 (Page 2)")
    
    # 建立指標驗證 HTML 結構 (模擬 Streamlit 表格截圖)
    table_rows = ""
    for row in data_to_display:
        # 將 'red', 'green', 'orange' 映射到 CSS class
        color_class = f"color-{row.get('顏色代碼', 'color-orange')}"
        
        # 突出顯示 MACD, RSI, SMA20/60
        is_key_indicator = row['指標'] in ["MACD", "RSI", "20/60 SMA"]
        highlight_style = "border: 2px solid var(--trend-blue); border-radius: 6px; padding: 10px; margin: 5px 0;" if is_key_indicator else ""
        
        table_rows += f"""
        <div class="indicator-row" style="{highlight_style}">
            <span class="indicator-name" style="color: {'var(--trend-blue)' if is_key_indicator else 'var(--text-light)'};">
                {row['指標']}
            </span>
            <span class="indicator-value {color_class}">
                {row['最新值']}
            </span>
            <span class="indicator-summary {color_class}">
                {row['分析結論']}
            </span>
        </div>
        """
        
    page_2_html = f"""
    <div class="ig-page">
        <div>
            <h2 class="page2-validation-header">AI 判讀背後的數據支撐</h2>
            <h4 style="color: var(--text-white); text-align: center; font-weight: 500;">
                關鍵技術指標與 {signal} 結論驗證
            </h4>

            <div class="indicator-table-sim">
                {table_rows}
            </div>
            
            <p style="text-align: center; margin-top: 25px; font-style: italic; color: var(--text-light); font-size: 0.95rem;">
                AI 策略依據：MACD 動能、RSI 動能與均線關係。
            </p>
        </div>
        
        <div class="cta-tip">
            更多回測與細節，請向左滑動 →
        </div>
    </div>
    """
    st.markdown(page_2_html, unsafe_allow_html=True)
    st.markdown("---")


    # --- Page 3: 行動呼籲專頁 (獲利導流頁) ---
    st.markdown("### 3. 行動呼籲專頁 (Page 3)")
    page_3_html = f"""
    <div class="ig-page">
        <div class="page3-cta">
            <h2 class="cta-main-title">想驗證 AI 策略？</h2>
            <p class="cta-main-action">前往 APP 立即回測！</p>
            
            <!-- 核心視覺導航指引：使用大箭頭模擬 -->
            <div style="font-size: 4rem; color: var(--alert-orange); margin: 30px 0;">
                👉
            </div>
            
            <p class="cta-link-instruction">點擊主頁連結 [您的 App 連結]</p>
        </div>

        <div class="disclaimer">
            ⚠️ 免責聲明：本內容僅供學習與參考，不構成任何投資建議。交易有風險，入場需謹慎。
        </div>
    </div>
    """
    st.markdown(page_3_html, unsafe_allow_html=True)
    st.markdown("---")


# (create_comprehensive_chart 函數保持不變，略過以縮短篇幅，確保它是完整的)
def create_comprehensive_chart(df, symbol, period_key):
    """
    創建包含K線圖、成交量、MACD和RSI的綜合Plotly圖表。
    """
    # 確保索引是 datetime 類型
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # 創建四個子圖：K線圖, 成交量, MACD, RSI
    # 共享 X 軸
    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.04,
        row_heights=[0.5, 0.15, 0.15, 0.2] # 調整子圖高度比例
    )

    # --- 1. K線圖 (Candlestick) ---
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='價格',
        increasing_line_color='#FF4B4B', # Streamlit Red (多頭)
        decreasing_line_color='#00FF00' # Streamlit Green (空頭)
    ), row=1, col=1)

    # 增加移動平均線 (SMA 20, 60)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='orange', width=1), name='SMA 20'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_60'], line=dict(color='blue', width=1), name='SMA 60'), row=1, col=1)

    # --- 2. 成交量 (Volume) ---
    colors = ['#FF4B4B' if c >= o else '#00FF00' for c, o in zip(df['Close'], df['Open'])]
    fig.add_trace(go.Bar(
        x=df.index, 
        y=df['Volume'], 
        name='成交量', 
        marker_color=colors, 
        opacity=0.5
    ), row=2, col=1)

    # --- 3. MACD ---
    # MACD 柱狀圖 (Histogram)
    fig.add_trace(go.Bar(
        x=df.index, 
        y=df['MACD_Hist'], 
        name='MACD Hist', 
        marker_color=['#FF4B4B' if val > 0 else '#00FF00' for val in df['MACD_Hist']]
    ), row=3, col=1)
    # MACD 線
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='purple', width=1), name='MACD Line'), row=3, col=1)
    # Signal 線
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='yellow', width=1), name='Signal Line'), row=3, col=1)
    
    # 增加零線
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="white", row=3, col=1)

    # --- 4. RSI ---
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='cyan', width=1.5), name='RSI'), row=4, col=1)
    # 增加超買/超賣區間
    fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="#FF4B4B", row=4, col=1)
    fig.add_hline(y=30, line_width=1, line_dash="dash", line_color="#00FF00", row=4, col=1)
    
    # --- 佈局設置 (Layout Configuration) ---
    fig.update_layout(
        title={
            'text': f"K線圖與關鍵指標 ({symbol} - {period_key})",
            'y':0.95, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top',
            'font': dict(size=20, color="white")
        },
        height=900, 
        xaxis_rangeslider_visible=False, # 隱藏底部的滑動條
        template="plotly_dark", # 使用深色主題
        hovermode="x unified",
        margin=dict(l=10, r=10, t=50, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # 調整子圖的 Y 軸標籤
    fig.update_yaxes(title_text="價格 / SMA", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1, showticklabels=False)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    fig.update_yaxes(title_text="RSI / 動能", row=4, col=1, range=[0, 100])
    
    # 隱藏所有 X 軸標籤，除了最底下的子圖
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=3, col=1)
    fig.update_xaxes(showticklabels=True, row=4, col=1) # 僅顯示最底部圖表的 X 軸
    
    return fig


def generate_indicator_table(df):
    """
    根據最新的技術指標數值，提供趨勢/動能判讀的表格。
    同時返回用於 IG 視圖的 `data_with_style` 列表。
    """
    if df.empty:
        return pd.DataFrame(), {}

    latest = df.iloc[-1]
    
    # 判讀邏輯
    indicators_data = {
        "指標": ["MACD", "RSI", "StochRSI (K/D)", "ATR (波動性)", "20/60 SMA"],
        "最新值": [
            f"{latest['MACD_Hist']:.3f}",
            f"{latest['RSI']:.2f}",
            f"{latest['StochRSI_K']:.2f} / {latest['StochRSI_D']:.2f}",
            f"{latest['ATR']:.2f}",
            f"C={latest['Close']:.2f}, SMA20={latest['SMA_20']:.2f}, SMA60={latest['SMA_60']:.2f}",
        ],
        "分析結論": ["", "", "", "", ""],
        "顏色代碼": ["", "", "", "", ""] # red: 多頭/強化, green: 空頭/削弱, orange: 中性/警告
    }
    
    # MACD 判讀
    if latest['MACD_Hist'] > 0 and latest['MACD'] > latest['MACD_Signal']:
        indicators_data['分析結論'][0] = "多頭動能強化 (MACD柱體>0)"
        indicators_data['顏色代碼'][0] = "red"
    elif latest['MACD_Hist'] < 0 and latest['MACD'] < latest['MACD_Signal']:
        indicators_data['分析結論'][0] = "空頭動能強化 (MACD柱體<0)"
        indicators_data['顏色代碼'][0] = "green"
    else:
        indicators_data['分析結論'][0] = "趨勢中性/轉折警示"
        indicators_data['顏色代碼'][0] = "orange"

    # RSI 判讀 (動能)
    if latest['RSI'] > 60:
        indicators_data['分析結論'][1] = "動能強勁 (RSI > 60)"
        indicators_data['顏色代碼'][1] = "red" 
    elif latest['RSI'] < 40:
        indicators_data['分析結論'][1] = "動能疲弱 (RSI < 40)"
        indicators_data['顏色代碼'][1] = "green" 
    else:
        indicators_data['分析結論'][1] = "動能區間震盪 (40-60)"
        indicators_data['顏色代碼'][1] = "orange"

    # StochRSI 判讀 (短線動能)
    if latest['StochRSI_K'] > latest['StochRSI_D']:
        indicators_data['分析結論'][2] = "短線動能上揚 (K線>D線)"
        indicators_data['顏色代碼'][2] = "red"
    elif latest['StochRSI_K'] < latest['StochRSI_D']:
        indicators_data['分析結論'][2] = "短線動能下降 (K線<D線)"
        indicators_data['顏色代碼'][2] = "green"
    else:
        indicators_data['分析結論'][2] = "極端區/短線震盪"
        indicators_data['顏色代碼'][2] = "orange"
        
    # ATR 判讀 (僅顯示數值，提供提示)
    indicators_data['分析結論'][3] = f"最近14期平均波動幅度"
    indicators_data['顏色代碼'][3] = "orange" 

    # 20/60 SMA 判讀 (趨勢判斷)
    if latest['SMA_20'] > latest['SMA_60'] and latest['Close'] > latest['SMA_20']:
        indicators_data['分析結論'][4] = "多頭排列 (股價>SMA20>SMA60)"
        indicators_data['顏色代碼'][4] = "red"
    elif latest['SMA_20'] < latest['SMA_60'] and latest['Close'] < latest['SMA_60']:
        indicators_data['分析結論'][4] = "空頭排列 (股價<SMA60<SMA20)"
        indicators_data['顏色代碼'][4] = "green"
    else:
        indicators_data['分析結論'][4] = "橫向整理/均線糾結"
        indicators_data['顏色代碼'][4] = "orange"

    
    df_indicators = pd.DataFrame(indicators_data)
    
    # 顏色轉換函數 for Streamlit Data Editor
    def color_picker(row):
        color = row['顏色代碼']
        if color == 'red':
            # 使用 Streamlit 預設的多頭色
            return 'background-color: rgba(255, 75, 75, 0.1); color: #FF4B4B;'
        elif color == 'green':
            # 使用 Streamlit 預設的空頭色
            return 'background-color: rgba(0, 255, 0, 0.1); color: #00FF00;' 
        elif color == 'orange':
            return 'background-color: rgba(255, 165, 0, 0.1); color: #FFA500;'
        else:
            return ''
            
    # Streamlit 表格樣式
    styler = df_indicators.style.apply(color_picker, axis=1)

    df_display = df_indicators.drop(columns=['顏色代碼'])
    
    data_list = df_display.to_dict('records')
    
    # 重新加入顏色代碼用於 ColumnConfig 和 IG 視圖
    data_with_style = []
    for i, row in enumerate(data_list):
        row['顏色代碼'] = indicators_data['顏色代碼'][i] 
        data_with_style.append(row)
        
    return data_with_style, styler


def main():
    
    # --- 側邊欄 (Sidebar) 設置 ---
    st.sidebar.header("⚙️ 數據與參數設置")
    
    categories = sorted(list(set(item['category'] for item in FULL_SYMBOLS_MAP.values())))
    selected_category = st.sidebar.selectbox("1. 選擇資產類別", categories, index=1, key="sidebar_category")
    
    filtered_symbols = {k: v for k, v in FULL_SYMBOLS_MAP.items() if v['category'] == selected_category}
    asset_names = [v['name'] for v in filtered_symbols.values()]
    
    default_symbol = "2330.TW" if selected_category == "台股" else ("NVDA" if selected_category == "美股" else "BTC-USD")
    default_asset_name = next((v['name'] for k, v in FULL_SYMBOLS_MAP.items() if k == default_symbol), asset_names[0] if asset_names else "")
    default_index = asset_names.index(default_asset_name) if default_asset_name in asset_names else 0
    
    selected_asset_name = st.sidebar.selectbox(
        "2. 快速選擇標的", 
        asset_names, 
        index=default_index,
        key="sidebar_symbol_select"
    )
    
    st.sidebar.text_input(
        "或 3. 直接輸入代碼 (e.g., TSLA, 2330.TW)", 
        value=st.session_state.get('last_search_symbol', default_symbol), 
        key="sidebar_search_input",
        help="輸入後請按 Enter 鍵確定，並點擊下方分析按鈕。"
    )
    
    period_options = list(PERIOD_MAP.keys())
    selected_period_key = st.sidebar.selectbox(
        "4. 選擇分析週期", 
        period_options,
        index=period_options.index("1 日 (中長線)"),
        key="sidebar_period_select"
    )
    
    st.sidebar.markdown("---")
    
    analyze_button_clicked = st.sidebar.button("📊 執行AI分析", type="primary", use_container_width=True)
    
    user_input_symbol = st.session_state.get('sidebar_search_input', '').upper().strip()
    
    if user_input_symbol and user_input_symbol != default_symbol:
        final_symbol_to_analyze = user_input_symbol
    else:
        final_symbol_to_analyze = next((k for k, v in filtered_symbols.items() if v['name'] == selected_asset_name), default_symbol)

    if not final_symbol_to_analyze:
        final_symbol_to_analyze = default_symbol


    # --- 主畫面內容呈現邏輯 ---

    if analyze_button_clicked or st.session_state.get('data_ready', False):
        
        if analyze_button_clicked:
            with st.spinner(f"🚀 正在載入與分析 {final_symbol_to_analyze} 的 {selected_period_key} 數據..."):
                
                period, interval = PERIOD_MAP[selected_period_key]
                df, name, error_msg = get_data(final_symbol_to_analyze, period, interval)
                
                st.session_state['asset_name'] = name
                st.session_state['data_ready'] = not df.empty and not error_msg
                st.session_state['analysis_error'] = error_msg
                st.session_state['analysis_df'] = df.copy()
                st.session_state['symbol_to_display'] = final_symbol_to_analyze
                st.session_state['period_to_display'] = selected_period_key
                st.session_state['last_search_symbol'] = final_symbol_to_analyze
                
                if st.session_state['analysis_error']:
                    st.session_state['data_ready'] = False
                
                time.sleep(1)

        if st.session_state.get('analysis_error'):
            st.error(f"❌ 分析失敗: {st.session_state['analysis_error']}")
            st.session_state['data_ready'] = False
        
        if st.session_state.get('data_ready', False):
            
            df = st.session_state['analysis_df']
            final_symbol_to_analyze = st.session_state['symbol_to_display']
            selected_period_key = st.session_state['period_to_display']
            asset_name = st.session_state.get('asset_name', final_symbol_to_analyze)

            # 1. 主標題
            st.title(f"🔍 {asset_name} ({final_symbol_to_analyze}) AI 技術趨勢分析")
            
            # --- 核心邏輯計算 ---
            df = calculate_indicators(df)
            signal, params = determine_ai_signal(df) 
            data_to_display, _ = generate_indicator_table(df) # <-- 指標表格數據
            # --- 核心邏輯計算 ---

            # 2. 最新價格與基本資訊
            latest_close = df['Close'].iloc[-1]
            last_date = df.index[-1]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("最新收盤價 (Close)", f"${latest_close:.2f}")
            with col2:
                if len(df) >= 2:
                    last_day_change = (df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100
                    st.metric("最近期漲跌幅", f"{last_day_change:.2f}%", delta=f"{df['Close'].iloc[-1] - df['Close'].iloc[-2]:.2f}", delta_color="inverse")
                else:
                    st.metric("最近期漲跌幅", "N/A")
            with col3:
                st.metric("AI 綜合信號", f"🎯 {signal}", delta_color=("inverse" if signal == "SELL" else ("normal" if signal == "BUY" else "off")))
            with col4:
                date_format = "%Y-%m-%d %H:%M" if '分' in selected_period_key or '時' in selected_period_key else "%Y-%m-%d"
                st.metric("數據截止日期", last_date.strftime(date_format))
                
            st.markdown("---")
            
            # 3. 關鍵技術指標表格 
            st.subheader(f"⚡️ 關鍵技術指標一覽 (基於 {last_date.strftime('%Y-%m-%d')} 數據)")
            
            # 由於 Streamlit 不支援直接渲染 styled DataFrames in data_editor,
            # 我們使用 data_editor 來呈現數據，並在下方用 caption 解釋顏色邏輯。
            st.data_editor(
                data_to_display,
                hide_index=True,
                column_order=("指標", "最新值", "分析結論"),
                column_config={
                    "最新值": st.column_config.Column("最新數值", help="技術指標的最新計算值"),
                    "分析結論": st.column_config.Column("趨勢/動能判讀", help="基於數值範圍的專業解讀"),
                    "顏色代碼": st.column_config.Column("顏色代碼", disabled=True, visibility="hidden")
                }
            )
            st.caption("ℹ️ **設計師提示:** 表格顏色會根據指標的趨勢/風險等級自動變化（**紅色**=多頭/強化信號，**綠色**=空頭/削弱信號，**橙色**=中性/警告）。")

            st.markdown("---")
            
            # 4. IG 輪播圖生成區塊 (已更新)
            with st.expander("✨ 點擊生成 IG 輪播圖 (3 頁) 預覽並截圖", expanded=True):
                render_ig_carousel_view(
                    final_symbol_to_analyze, 
                    asset_name, 
                    selected_period_key, 
                    signal, 
                    params, 
                    data_to_display
                )

            st.markdown("---")

            # 5. 完整技術分析圖表 (保持不變)
            st.subheader(f"📊 完整技術分析圖表")
            chart = create_comprehensive_chart(df, final_symbol_to_analyze, selected_period_key) 
            st.plotly_chart(chart, use_container_width=True, key=f"plotly_chart_{final_symbol_to_analyze}_{selected_period_key}")

        else:
            if not st.session_state.get('analysis_error'):
                st.info("無足夠數據生成關鍵技術指標表格。")
        
    elif not st.session_state.get('data_ready', False) and not analyze_button_clicked:
          # 初次載入畫面
          st.title("🤖 歡迎使用 AI 趨勢分析儀表板 📈")
          st.info(f"請在左側選擇或輸入標的（例如：**2330.TW**、**NVDA**、**BTC-USD**），然後點擊 <span style='color: #FF4B4B; font-weight: bold;'>『📊 執行AI分析』</span> 按鈕開始。", unsafe_allow_html=True)
          
          st.markdown("---")
          
          st.subheader("📝 使用步驟：")
          st.markdown("1. **選擇資產類別**：在左側欄選擇 `美股`、`台股` 或 `加密貨幣`。")
          st.markdown("2. **選擇標的**：使用下拉選單快速選擇熱門標的，或直接在輸入框中鍵入代碼或名稱。")
          st.markdown("3. **選擇週期**：決定分析的長度（例如：`30 分 (短期)`、`1 日 (中長線)`、`1 週 (長期)`）。")
          st.markdown(f"4. **執行分析**：點擊 <span style='color: #FF4B4B; font-weight: bold;'>『📊 執行AI分析』**</span>，AI將融合基本面與技術面指標提供交易策略。", unsafe_allow_html=True)
          
          st.markdown("---")


if __name__ == '__main__':
    # Streamlit Session State 初始化，確保變數存在
    if 'last_search_symbol' not in st.session_state:
        st.session_state['last_search_symbol'] = "2330.TW"
    if 'data_ready' not in st.session_state:
        st.session_state['data_ready'] = False
    if 'sidebar_search_input' not in st.session_state:
        st.session_state['sidebar_search_input'] = ""
    if 'analysis_error' not in st.session_state:
        st.session_state['analysis_error'] = ""
    if 'symbol_to_display' not in st.session_state:
        st.session_state['symbol_to_display'] = "2330.TW"
    if 'period_to_display' not in st.session_state:
        st.session_state['period_to_display'] = "1 日 (中長線)"
    if 'asset_name' not in st.session_state:
        st.session_state['asset_name'] = FULL_SYMBOLS_MAP['2330.TW']['name']
        
    main()
