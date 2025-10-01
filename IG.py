import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta # Technical Analysis Library
import warnings
import time
import re 
from datetime import datetime, timedelta

# 警告處理：隱藏 Pandas 或 TA-Lib 可能發出的未來警告
warnings.filterwarnings('ignore')

# ==============================================================================
# 1. 頁面配置與全局設定
# ==============================================================================

st.set_page_config(
    page_title="🤖 AI趨勢分析儀表板 📈", # 已更新分頁標題，新增 📈 圖標
    page_icon="📈", 
    layout="wide"
)

# YFinance 參數對應表
PERIOD_MAP = { 
    "30 分 (短期)": ("60d", "30m"), 
    "4 小時 (波段)": ("1y", "60m"), 
    "1 日 (中長線)": ("5y", "1d"), 
    "1 週 (長期)": ("max", "1wk")
}

# 🚀 您的【所有資產清單】(FULL_SYMBOLS_MAP) - 涵蓋美股、台股、加密貨幣、指數、ETF
FULL_SYMBOLS_MAP = {
    # ----------------------------------------------------
    # A. 美股核心 (US Stocks) - 個股
    # ----------------------------------------------------
    "TSLA": {"name": "特斯拉", "keywords": ["特斯拉", "電動車", "TSLA", "Tesla"], "class": "US Stock"},
    "NVDA": {"name": "輝達", "keywords": ["輝達", "英偉達", "AI", "NVDA", "Nvidia"], "class": "US Stock"},
    "AAPL": {"name": "蘋果", "keywords": ["蘋果", "手機", "AAPL", "Apple"], "class": "US Stock"},
    "GOOGL": {"name": "谷歌-A", "keywords": ["谷歌", "Google", "GOOGL"], "class": "US Stock"},
    # ----------------------------------------------------
    # B. 台股核心 (Taiwan Stocks) - 個股/指數
    # ----------------------------------------------------
    "2330.TW": {"name": "台積電", "keywords": ["台積電", "晶圓", "2330", "TSMC"], "class": "Taiwan Stock"},
    "2317.TW": {"name": "鴻海", "keywords": ["鴻海", "2317", "Foxconn"], "class": "Taiwan Stock"},
    "^TWII": {"name": "加權指數", "keywords": ["加權", "台股大盤", "TWII"], "class": "Taiwan Stock"},
    # ----------------------------------------------------
    # C. 加密貨幣核心 (Crypto) - 需加 -USD
    # ----------------------------------------------------
    "BTC-USD": {"name": "比特幣", "keywords": ["比特幣", "BTC"], "class": "Crypto"},
    "ETH-USD": {"name": "以太幣", "keywords": ["以太幣", "ETH"], "class": "Crypto"},
    # ----------------------------------------------------
    # D. ETF核心 (ETFs)
    # ----------------------------------------------------
    "VOO": {"name": "Vanguard 標普500", "keywords": ["標普500", "VOO", "S&P"], "class": "ETF"},
    "QQQ": {"name": "Invesco 那斯達克100", "keywords": ["那斯達克", "QQQ"], "class": "ETF"},
}


# ==============================================================================
# 2. 技術指標計算與分析函式
# ==============================================================================

def calculate_technical_indicators(df, prefix="TT"):
    """
    計算一系列關鍵技術指標並將結果加入 DataFrame。
    :param df: 包含 ['Close', 'High', 'Low', 'Open', 'Volume'] 的 Pandas DataFrame
    :param prefix: 指標欄位名稱的前綴 (e.g., 'TT_')
    :return: 包含技術指標欄位的新 DataFrame
    """
    
    # 檢查是否具備計算指標所需的數據量
    if len(df) < 50: # 假設至少需要50根K線來計算多數指標
        return df

    # --- 趨勢指標 (Trend) ---
    # SMA (Simple Moving Average)
    df[f'{prefix}_SMA20'] = ta.trend.sma_indicator(df.Close, window=20, fillna=False)
    df[f'{prefix}_SMA50'] = ta.trend.sma_indicator(df.Close, window=50, fillna=False)

    # MACD (Moving Average Convergence Divergence)
    # 修正: 'window_sign' 參數已在較新版本中更名為 'window_signal'
    df[f'{prefix}_MACD_Line'] = ta.trend.macd(df.Close, window_fast=12, window_slow=26, window_signal=9, fillna=False)
    df[f'{prefix}_MACD_Hist'] = ta.trend.macd_diff(df.Close, window_fast=12, window_slow=26, window_signal=9, fillna=False)
    
    # ATR (Average True Range)
    df[f'{prefix}_ATR'] = ta.volatility.average_true_range(df.High, df.Low, df.Close, window=14, fillna=False)

    # --- 動能指標 (Momentum) ---
    # RSI (Relative Strength Index)
    df[f'{prefix}_RSI'] = ta.momentum.rsi(df.Close, window=14, fillna=False)

    # Stochastic Oscillator (KDJ/KD) - Using Stochastic Oscillator K/D for simplicity
    stoch = ta.momentum.StochasticOscillator(df.High, df.Low, df.Close, window=14, smooth_window=3, fillna=False)
    df[f'{prefix}_Stoch_K'] = stoch.stoch()
    df[f'{prefix}_Stoch_D'] = stoch.stoch_signal()

    # --- 交易量指標 (Volume) ---
    # MFI (Money Flow Index)
    df[f'{prefix}_MFI'] = ta.volume.money_flow_index(df.High, df.Low, df.Close, df.Volume, window=14, fillna=False)

    return df.dropna().copy()


def get_indicator_analysis(df, prefix="TT"):
    """
    獲取最新的技術指標數值和基於數值的分析結論。
    :param df: 包含技術指標計算結果的 DataFrame
    :param prefix: 指標欄位名稱的前綴
    :return: 包含最新數值和分析結論的 DataFrame
    """
    if df.empty:
        return pd.DataFrame()

    last_row = df.iloc[-1]
    
    # 定義分析邏輯 (基於最新的數值)
    analysis_data = {}

    # 1. MACD (動能與趨勢)
    macd_line = last_row[f'{prefix}_MACD_Line']
    macd_hist = last_row[f'{prefix}_MACD_Hist']
    
    macd_conclusion = "中性 (等待信號)"
    macd_color = "orange"
    
    if macd_hist > 0 and macd_line > 0:
        macd_conclusion = "多頭動能強化 (牛市區間)"
        macd_color = "red"
    elif macd_hist > 0 and macd_line < 0:
        macd_conclusion = "趨勢翻多中 (買入信號)"
        macd_color = "lightcoral"
    elif macd_hist < 0 and macd_line < 0:
        macd_conclusion = "空頭動能強化 (熊市區間)"
        macd_color = "green"
    elif macd_hist < 0 and macd_line > 0:
        macd_conclusion = "趨勢翻空中 (賣出信號)"
        macd_color = "lightgreen"
        
    analysis_data['MACD (12, 26, 9)'] = {
        "最新值": macd_line,
        "分析結論": macd_conclusion,
        "顏色": macd_color
    }

    # 2. RSI (超買/超賣)
    rsi_value = last_row[f'{prefix}_RSI']
    rsi_conclusion = "中性 (無明顯信號)"
    rsi_color = "orange"
    
    if rsi_value >= 70:
        rsi_conclusion = f"超買 ({rsi_value:.2f}) - 留意修正風險"
        rsi_color = "green" # 綠色代表高風險/賣出信號
    elif rsi_value <= 30:
        rsi_conclusion = f"超賣 ({rsi_value:.2f}) - 留意反彈機會"
        rsi_color = "red" # 紅色代表低風險/買入信號
        
    analysis_data['RSI (14)'] = {
        "最新值": rsi_value,
        "分析結論": rsi_conclusion,
        "顏色": rsi_color
    }
    
    # 3. KDJ (超買/超賣與交叉) - 使用 Stochastic Oscillator K/D
    stoch_k = last_row[f'{prefix}_Stoch_K']
    stoch_d = last_row[f'{prefix}_Stoch_D']
    
    stoch_conclusion = "中性 (K>D，上行趨勢)"
    stoch_color = "orange"
    
    if stoch_k > 80 and stoch_d > 80:
        stoch_conclusion = "超買區 (留意回調)"
        stoch_color = "green"
    elif stoch_k < 20 and stoch_d < 20:
        stoch_conclusion = "超賣區 (可能反彈)"
        stoch_color = "red"
    elif stoch_k > stoch_d and stoch_k < 80 and stoch_k > 20:
        stoch_conclusion = "金叉上行 (多頭動能)"
        stoch_color = "red"
    elif stoch_k < stoch_d and stoch_k < 80 and stoch_k > 20:
        stoch_conclusion = "死叉下行 (空頭動能)"
        stoch_color = "green"
        
    analysis_data['KDJ (Stoch K/D)'] = {
        "最新值": stoch_k,
        "分析結論": stoch_conclusion,
        "顏色": stoch_color
    }

    # 4. SMA (趨勢判斷) - 股價與 20 日線/50 日線的關係
    close = last_row['Close']
    sma20 = last_row[f'{prefix}_SMA20']
    sma50 = last_row[f'{prefix}_SMA50']
    
    sma_conclusion = "中性 (價格震盪於均線之間)"
    sma_color = "orange"

    if close > sma20 and sma20 > sma50:
        sma_conclusion = "多頭排列 (強勁上漲趨勢)"
        sma_color = "red"
    elif close < sma20 and sma20 < sma50:
        sma_conclusion = "空頭排列 (確認下跌趨勢)"
        sma_color = "green"

    analysis_data['股價 vs. 均線'] = {
        "最新值": close,
        "分析結論": sma_conclusion,
        "顏色": sma_color
    }


    # 轉換為 DataFrame 
    result_df = pd.DataFrame.from_dict(analysis_data, orient='index')
    # 格式化數值
    result_df['最新值'] = result_df['最新值'].apply(lambda x: f"{x:,.2f}")
    
    # 將顏色資訊轉換為 Streamlit 支援的格式 (HTML/CSS 標籤)
    def style_row(row):
        color = row['顏色']
        
        # 簡易的顏色映射 (Streamlit 只支持 HTML/CSS 顏色名稱)
        if color == 'red':
            bg_color = '#FBEFEF' # Light Red
            text_color = '#C70039' # Dark Red
        elif color == 'green':
            bg_color = '#EFFBEF' # Light Green
            text_color = '#007000' # Dark Green
        else:
            bg_color = '#FFF3E0' # Light Orange
            text_color = '#FFA500' # Dark Orange

        return [f"background-color: {bg_color}; color: {text_color}; font-weight: bold;" for _ in row.index]

    styled_df = result_df[['最新值', '分析結論']].style.apply(style_row, axis=1)

    return styled_df

# ==============================================================================
# 3. Plotly 圖表生成函式
# ==============================================================================

def create_comprehensive_chart(df, symbol, period_key):
    """
    創建一個包含K線圖、成交量、MACD和RSI的綜合Plotly圖表。
    :param df: 包含數據和指標的 DataFrame
    """
    # 創建子圖: 4 行，1 欄。高度比例: K線:成交量:MACD:RSI
    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        row_heights=[0.5, 0.15, 0.15, 0.2],
        subplot_titles=(f"{symbol} 價格走勢 ({period_key})", "成交量", "MACD (趨勢動能)", "RSI (超買超賣)")
    )
    
    # --- Row 1: K線圖與移動平均線 ---
    # K線圖 (Candlestick)
    fig.add_trace(go.Candlestick(
        x=df.index, 
        open=df.Open, 
        high=df.High, 
        low=df.Low, 
        close=df.Close,
        name='價格K線',
        increasing_line_color='#FF0000', decreasing_line_color='#008000'
    ), row=1, col=1)

    # SMA20
    prefix = "TT" # 預設前綴
    if f'{prefix}_SMA20' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[f'{prefix}_SMA20'], line=dict(color='#FFA500', width=1), name='SMA 20'), row=1, col=1)
    # SMA50
    if f'{prefix}_SMA50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[f'{prefix}_SMA50'], line=dict(color='#0000FF', width=1), name='SMA 50'), row=1, col=1)

    # --- Row 2: 成交量 ---
    colors_vol = ['#FF0000' if df.Close[i] > df.Open[i] else '#008000' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df.Volume, name='成交量', marker_color=colors_vol), row=2, col=1)
    
    # --- Row 3: MACD ---
    if f'{prefix}_MACD_Line' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[f'{prefix}_MACD_Line'], line=dict(color='#0000FF', width=2), name='MACD Line'), row=3, col=1)
    if f'{prefix}_MACD_Hist' in df.columns:
        # MACD 柱狀圖顏色判斷 (正紅負綠)
        colors_macd = ['#FF0000' if val > 0 else '#008000' for val in df[f'{prefix}_MACD_Hist']]
        fig.add_trace(go.Bar(x=df.index, y=df[f'{prefix}_MACD_Hist'], name='MACD Hist', marker_color=colors_macd), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df[f'{prefix}_MACD_Line'] - df[f'{prefix}_MACD_Hist'], line=dict(color='#FF00FF', width=1), name='Signal Line'), row=3, col=1)
        fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray", row=3, col=1) # 零軸線
    
    # --- Row 4: RSI ---
    if f'{prefix}_RSI' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[f'{prefix}_RSI'], line=dict(color='#FFA500', width=2), name='RSI'), row=4, col=1)
        # 超買/超賣線
        fig.add_hline(y=70, line_width=1, line_dash="dash", line_color="#FF0000", row=4, col=1)
        fig.add_hline(y=30, line_width=1, line_dash="dash", line_color="#008000", row=4, col=1)
        
    # --- 圖表佈局設定 ---
    fig.update_layout(
        title_text=f"**{symbol} AI 技術指標深度分析**", 
        height=900, 
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        template="plotly_dark", # 使用暗色主題
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    # 隱藏子圖上的範圍滑塊和圖例
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    fig.update_layout(showlegend=False)
    
    # 確保成交量和 MACD 的 X 軸沒有標籤 (共享 X 軸)
    fig.update_xaxes(title_text="", row=2, col=1, showticklabels=False)
    fig.update_xaxes(title_text="", row=3, col=1, showticklabels=False)
    
    # 調整 Y 軸，確保 MACD 零軸居中
    fig.update_yaxes(zeroline=True, zerolinecolor='gray', zerolinewidth=1, row=3, col=1)

    return fig


# ==============================================================================
# 4. Streamlit 應用程式主邏輯
# ==============================================================================

# Helper function to get the current symbol based on selection/input
def get_final_symbol(asset_class, selected_option, sidebar_search_input):
    """根據使用者輸入，確定最終的分析標的代碼"""
    final_symbol = ""
    
    # 1. 如果使用者有手動輸入，則以手動輸入為準 (忽略大小寫和空白)
    if sidebar_search_input and sidebar_search_input.strip():
        # 清理輸入, 移除所有空格並轉大寫 (除非是台股，台股代碼後綴大小寫敏感，但通常.TW是大小寫不敏感的)
        search_input_cleaned = sidebar_search_input.strip().upper()
        
        # 嘗試直接使用輸入作為代碼
        final_symbol = search_input_cleaned

        # 處理台股特殊情況: 如果輸入是純數字，自動補上 .TW
        if asset_class == "Taiwan Stock" and re.fullmatch(r'\d+', search_input_cleaned):
             final_symbol = f"{search_input_cleaned}.TW"
             
        # 更新 session state，以便下次載入時保留手動輸入
        st.session_state['sidebar_search_input'] = sidebar_search_input.strip()

    # 2. 如果沒有手動輸入，則使用下拉選單的選定值
    elif selected_option and selected_option != "請選擇...":
        # 解析選單格式: 名稱 (代碼) -> 提取代碼
        symbol_match = re.search(r'\(([^)]+)\)', selected_option)
        if symbol_match:
            final_symbol = symbol_match.group(1)
            # 自動更新手動輸入框的值 (關鍵修正)
            st.session_state['sidebar_search_input'] = final_symbol

    # 3. 如果以上都沒有，使用預設值
    else:
        # 如果 sidebar_search_input 是空的，使用上次的成功代碼作為預設
        if not st.session_state.get('sidebar_search_input'):
            final_symbol = st.session_state['last_search_symbol']
        else:
            final_symbol = st.session_state['sidebar_search_input']

    return final_symbol.strip()

# --- Callbacks for improved UX ---
def update_search_input_from_radio():
    """當資產類別改變時，清空手動輸入框，避免舊代碼干擾"""
    st.session_state['sidebar_search_input'] = ""
    st.session_state['selected_option_key'] = "" # 清空選單選項

# VITAL FIX: Function to update the text input when selectbox changes
def update_search_input_from_select():
    """當下拉選單選擇標的時，自動將代碼填入下方的輸入框"""
    selected_option = st.session_state.get('selected_option_key')
    if selected_option and selected_option != "請選擇...":
        symbol_match = re.search(r'\(([^)]+)\)', selected_option)
        if symbol_match:
            # 關鍵修正: 將選中的代碼賦值給手動輸入框的 session state key
            st.session_state['sidebar_search_input'] = symbol_match.group(1)
            # 重設 data_ready 狀態，確保下次分析是新的數據
            st.session_state['data_ready'] = False 
    else:
        st.session_state['sidebar_search_input'] = ""

# --- Sidebar 介面 ---
st.sidebar.title("🛠️ AI 分析參數設定")

# 步驟 1: 選擇資產類別 (Asset Class Selection)
asset_class = st.sidebar.radio(
    "1. 選擇資產類別",
    ["Taiwan Stock", "US Stock", "Crypto", "ETF"],
    index=0, # 預設選擇台股
    key="asset_class_key",
    on_change=update_search_input_from_radio
)

# 根據選擇的資產類別過濾標的
filtered_symbols = {
    symbol: data for symbol, data in FULL_SYMBOLS_MAP.items() 
    if data['class'] == asset_class
}

# 準備下拉選單的選項 (格式: 名稱 (代碼))
available_options = ["請選擇..."] + [
    f"{data['name']} ({symbol})" for symbol, data in filtered_symbols.items()
]

# 確定初始選單索引
initial_index = 0
if 'last_search_symbol' in st.session_state:
    last_symbol = st.session_state['last_search_symbol']
    for i, option in enumerate(available_options):
        if last_symbol in option:
            initial_index = i
            break
            
# 步驟 2: 選擇標的 (Select Symbol)
selected_option = st.sidebar.selectbox(
    "2. 從熱門標的清單選擇",
    options=available_options,
    index=initial_index,
    key='selected_option_key', 
    on_change=update_search_input_from_select # 綁定回調函式
)

# 步驟 3: 手動輸入或確認 (Manual Input/Confirmation)
# 確保手動輸入框的值與 Session State 同步
# 如果 Session State 為空，則使用上次成功的代碼
default_input_value = st.session_state.get('sidebar_search_input', st.session_state['last_search_symbol'])

sidebar_search_input = st.sidebar.text_input(
    "3. 或直接輸入代碼/名稱 (例如: 2330.TW)",
    value=default_input_value, # 使用 session state 的值作為預設/動態值
    key='sidebar_search_input',
    placeholder="請輸入代碼 (例如: AAPL, BTC-USD)"
)

# 步驟 4: 選擇時間週期
selected_period_key = st.sidebar.selectbox(
    "4. 選擇分析時間週期",
    list(PERIOD_MAP.keys()),
    index=2 # 預設 '1 日 (中長線)'
)

# 獲取最終分析代碼
final_symbol_to_analyze = get_final_symbol(asset_class, selected_option, sidebar_search_input)

# 步驟 5: 開始分析按鈕
analyze_button_clicked = st.sidebar.button("📊 開始 AI 分析", use_container_width=True)


# --- 主頁面內容 ---
st.title("🤖 AI 趨勢分析儀表板 📈")
st.markdown(f"**當前分析標的：** <span style='color: #4CAF50; font-size: 1.5em;'>**{final_symbol_to_analyze}**</span> | **分析週期：** {selected_period_key}", unsafe_allow_html=True)

if analyze_button_clicked or st.session_state.get('data_ready', False):
    
    if analyze_button_clicked or final_symbol_to_analyze != st.session_state.get('last_search_symbol'):
        
        # 1. 獲取數據
        with st.spinner(f"正在擷取 {final_symbol_to_analyze} 的數據 ({selected_period_key})..."):
            period, interval = PERIOD_MAP[selected_period_key]
            
            try:
                # 數據擷取 (使用重試機制)
                max_retries = 3
                df = pd.DataFrame()
                for i in range(max_retries):
                    data = yf.download(final_symbol_to_analyze, period=period, interval=interval, progress=False)
                    if not data.empty:
                        df = data
                        break
                    time.sleep(1)
                
                if df.empty:
                    st.error(f"❌ 擷取 {final_symbol_to_analyze} 數據失敗。請檢查代碼是否正確或稍後再試。")
                    st.session_state['data_ready'] = False
                    st.session_state['last_search_symbol'] = final_symbol_to_analyze
                    # 在 Streamlit 中，通常在 error 之後執行 st.stop() 來停止當前腳本的後續執行，但這裡為了更好的用戶體驗，只返回
                    return
                
                # 2. 計算技術指標
                df = calculate_technical_indicators(df)
                
                # 儲存到 Session State
                st.session_state['df_data'] = df
                st.session_state['final_symbol_to_analyze'] = final_symbol_to_analyze
                st.session_state['selected_period_key'] = selected_period_key
                st.session_state['data_ready'] = True
                st.session_state['last_search_symbol'] = final_symbol_to_analyze # 儲存成功分析的代碼

            except Exception as e:
                st.error(f"❌ 擷取數據或分析時發生錯誤 ({final_symbol_to_analyze}): {e}")
                st.session_state['data_ready'] = False
                st.session_state['last_search_symbol'] = final_symbol_to_analyze
                # 由於 Streamlit 在回調函數中無法使用 st.stop(), 故使用 return

                
    # 3. 顯示分析結果
    if st.session_state.get('data_ready', False):
        df = st.session_state['df_data']
        final_symbol_to_analyze = st.session_state['final_symbol_to_analyze']
        selected_period_key = st.session_state['selected_period_key']
        
        st.subheader("💡 關鍵技術指標速覽與判讀")
        
        indicator_table = get_indicator_analysis(df)
        
        if not indicator_table.empty:
            st.dataframe(
                indicator_table,
                use_container_width=True,
                key=f"indicator_table_df_{final_symbol_to_analyze}_{selected_period_key}",
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
    
# 首次載入或數據未準備好時的提示
elif not st.session_state.get('data_ready', False) and not analyze_button_clicked:
     st.info("請在左側選擇或輸入標的，然後點擊 **『📊 開始 AI 分析』** 按鈕開始。")


if __name__ == '__main__':
    # Streamlit Session State 初始化，確保變數存在
    if 'last_search_symbol' not in st.session_state:
        st.session_state['last_search_symbol'] = "2330.TW"
    if 'data_ready' not in st.session_state:
        st.session_state['data_ready'] = False
    if 'sidebar_search_input' not in st.session_state:
        # 使用上次成功的代碼作為手動輸入的預設值
        st.session_state['sidebar_search_input'] = st.session_state['last_search_symbol']
    if 'selected_option_key' not in st.session_state:
        st.session_state['selected_option_key'] = ""
    
    # 啟用錯誤日誌 (可選，用於 Streamlit 環境下的調試)
    # import logging
    # logging.basicConfig(level=logging.DEBUG)
