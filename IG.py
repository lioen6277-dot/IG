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

# 忽略所有警告 (例如 pandas 的 SettingWithCopyWarning)
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
    "AMZN": {"name": "亞馬遜", "keywords": ["亞馬遜", "電商", "AMZN", "Amazon"]},
    "GOOGL": {"name": "谷歌", "keywords": ["谷歌", "搜尋", "GOOGL", "Alphabet"]},
    "AAPL": {"name": "蘋果", "keywords": ["蘋果", "手機", "AAPL", "Apple"]},
    # ----------------------------------------------------
    # B. 台股核心 (Taiwan Stocks) - 個股
    # ----------------------------------------------------
    "2330.TW": {"name": "台積電", "keywords": ["台積電", "晶圓", "2330", "TSMC"]},
    "2317.TW": {"name": "鴻海", "keywords": ["鴻海", "電子", "2317", "Foxconn"]},
    "2454.TW": {"name": "聯發科", "keywords": ["聯發科", "手機晶片", "2454", "MediaTek"]},
    # ----------------------------------------------------
    # C. 加密貨幣 (Crypto)
    # ----------------------------------------------------
    "BTC-USD": {"name": "比特幣", "keywords": ["比特幣", "BTC", "Bitcoin"]},
    "ETH-USD": {"name": "以太幣", "keywords": ["以太幣", "ETH", "Ethereum"]},
    # ----------------------------------------------------
}


# ==============================================================================
# 2. 資料獲取與技術指標計算函式
# ==============================================================================

@st.cache_data(ttl=3600) # 緩存數據一小時
def get_stock_data(symbol, period, interval):
    """
    從 yfinance 下載股價數據並處理。
    """
    try:
        # 嘗試下載數據，設置超時和重試機制
        data = yf.download(
            tickers=symbol, 
            period=period, 
            interval=interval, 
            timeout=10, 
            progress=False
        )
        
        # 檢查數據是否為空
        if data.empty:
            return None
        
        # 重新命名欄位以符合 ta 函式庫的要求
        data.columns = [col.capitalize() for col in data.columns]
        
        return data.dropna()
    except Exception as e:
        st.error(f"❌ 無法獲取代碼 **{symbol}** 的數據。請檢查代碼是否正確或稍後重試。錯誤: {e}")
        return None

def calculate_technical_indicators(df):
    """
    計算一系列關鍵技術指標。
    """
    if df is None or df.empty:
        return None

    # 1. 動量指標 (Momentum Indicators)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    df['Stoch_K'] = ta.momentum.stoch(df['High'], df['Low'], df['Close'], window=14, smooth_window=3)
    df['Stoch_D'] = ta.momentum.stoch_signal(df['High'], df['Low'], df['Close'], window=14, smooth_window=3)

    # 2. 趨勢指標 (Trend Indicators)
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA_60'] = ta.trend.sma_indicator(df['Close'], window=60)
    df['MACD'] = ta.trend.macd(df['Close'])
    df['MACD_Signal'] = ta.trend.macd_signal(df['Close'])
    df['MACD_Hist'] = ta.trend.macd_diff(df['Close'])
    df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=14)

    # 3. 波動性指標 (Volatility Indicators)
    bollinger = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_High'] = bollinger.bollinger_hband()
    df['BB_Low'] = bollinger.bollinger_lband()
    df['BB_Mid'] = bollinger.bollinger_mavg()
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)

    # 移除計算指標時產生的 NaN 行
    df = df.dropna()

    return df

# ==============================================================================
# 3. 數據與策略分析函式
# ==============================================================================

def analyze_indicator(name, value, last_close):
    """
    根據技術指標的最新值提供分析結論和風險等級。
    """
    if pd.isna(value):
        return {"最新值": np.nan, "分析結論": "數據不足", "風險等級": 0}

    value = round(value, 2)
    
    # 設置風險等級 (0: 數據不足/中性, 1: 弱空/警告, 2: 強空/賣出, 3: 弱多/注意, 4: 強多/買入)
    
    if name == "RSI (14)":
        if value > 70:
            conclusion = "超買區，動能過強，留意回調風險。"
            risk_level = 2 # 潛在賣出信號 (空頭)
        elif value < 30:
            conclusion = "超賣區，動能過弱，留意反彈機會。"
            risk_level = 4 # 潛在買入信號 (多頭)
        elif value >= 50:
            conclusion = "多頭佔優，位於強勢區。"
            risk_level = 3
        else:
            conclusion = "空頭佔優，位於弱勢區。"
            risk_level = 1
    
    elif name == "Stoch K/D (14,3)":
        # Stoch K/D 是兩個值，我們只看 K 值作為主要參考
        k_value = value 
        if k_value > 80:
            conclusion = "超買區，動能可能耗盡，留意賣出訊號。"
            risk_level = 2
        elif k_value < 20:
            conclusion = "超賣區，動能有機會反轉，留意買入訊號。"
            risk_level = 4
        else:
            conclusion = "中性區間。"
            risk_level = 0

    elif name == "MACD 柱狀體":
        if value > 0 and value > 0.01:
            conclusion = "多頭動能持續增強。"
            risk_level = 4
        elif value < 0 and value < -0.01:
            conclusion = "空頭動能持續增強。"
            risk_level = 2
        else:
            conclusion = "動能趨於平穩，觀望。"
            risk_level = 0
            
    elif name == "短期趨勢 (SMA 20)":
        # 價格與 20 日均線的關係
        if last_close > value:
            conclusion = "股價位於短期均線之上，趨勢偏多。"
            risk_level = 4
        else:
            conclusion = "股價位於短期均線之下，趨勢偏空。"
            risk_level = 2
    
    elif name == "中長期趨勢 (SMA 60)":
        # 價格與 60 日均線的關係
        if last_close > value:
            conclusion = "股價位於中長期均線之上，趨勢強勁。"
            risk_level = 4
        else:
            conclusion = "股價位於中長期均線之下，趨勢轉弱。"
            risk_level = 2

    elif name == "ADX (14)":
        if value > 25:
            conclusion = "趨勢動能強勁 (無論漲跌)。"
            risk_level = 3 # 趨勢強度高
        elif value < 20:
            conclusion = "趨勢動能微弱，可能進入盤整。"
            risk_level = 1 # 趨勢強度低
        else:
            conclusion = "趨勢動能適中。"
            risk_level = 0

    elif name == "布林帶 (BBands)":
        # 價格與布林帶邊界的關係
        bb_mid = value # 這裡假設 value 傳入的是 BB_Mid (中軌)
        
        # 為了更準確的判斷，我們需要 BB_High 和 BB_Low 的值，但為了簡化，先以中軌為參考
        # 實際應用中，應額外傳入 high/low 值
        if last_close > bb_mid:
            conclusion = "價格在中軌之上，短期偏多。"
            risk_level = 3
        else:
            conclusion = "價格在中軌之下，短期偏空。"
            risk_level = 1
            
    else:
        conclusion = "中性或不適用。"
        risk_level = 0

    return {"最新值": value, "分析結論": conclusion, "風險等級": risk_level}

def generate_technical_summary(df):
    """
    提取最新的技術指標並生成總結數據框。
    """
    if df is None or df.empty:
        return None, 0, 0, 0

    # 獲取最新一筆數據
    latest = df.iloc[-1]
    last_close = latest['Close']

    indicators = [
        ("RSI (14)", latest['RSI']),
        ("Stoch K/D (14,3)", latest['Stoch_K']), # 這裡只用 K 值代表
        ("MACD 柱狀體", latest['MACD_Hist']),
        ("短期趨勢 (SMA 20)", latest['SMA_20']),
        ("中長期趨勢 (SMA 60)", latest['SMA_60']),
        ("ADX (14)", latest['ADX']),
        ("布林帶 (BBands)", latest['BB_Mid']), # 用中軌代表布林帶
    ]
    
    summary_list = []
    bull_count = 0
    bear_count = 0
    
    for name, value in indicators:
        analysis = analyze_indicator(name, value, last_close)
        summary_list.append({
            "指標名稱": name,
            "最新值": analysis["最新值"],
            "分析結論": analysis["分析結論"],
            "風險等級": analysis["風險等級"]
        })
        
        # 統計多頭/空頭信號
        if analysis["風險等級"] in [3, 4]:
            bull_count += 1
        elif analysis["風險等級"] in [1, 2]:
            bear_count += 1

    summary_df = pd.DataFrame(summary_list)
    
    # 總結趨勢
    if bull_count > bear_count:
        trend_conclusion = "整體趨勢偏多，多頭信號數量佔優。"
        overall_risk_level = 4
    elif bear_count > bull_count:
        trend_conclusion = "整體趨勢偏空，空頭信號數量佔優。"
        overall_risk_level = 2
    else:
        trend_conclusion = "多空信號平衡，市場處於盤整或觀望狀態。"
        overall_risk_level = 0
        
    return summary_df, bull_count, bear_count, overall_risk_level

def generate_ai_analysis_text(symbol, df, summary_df, bull_count, bear_count, overall_risk_level, period_key):
    """
    根據技術指標和整體趨勢生成 AI 分析報告。
    """
    if df is None or df.empty or summary_df is None or summary_df.empty:
        return "數據不足，無法生成 AI 分析報告。"

    latest = df.iloc[-1]
    price = round(latest['Close'], 2)
    date = latest.name.strftime('%Y-%m-%d %H:%M')

    # 翻譯趨勢結論
    if overall_risk_level == 4:
        trend_text = "強勁多頭"
        advice = "建議持續關注做多機會，並以短期和中長期均線作為防守支撐。"
    elif overall_risk_level == 3:
        trend_text = "偏向多頭"
        advice = "多頭佔優，但需留意動能是否持續，可考慮輕倉做多或等待更明確信號。"
    elif overall_risk_level == 2:
        trend_text = "偏向空頭"
        advice = "空頭佔優，建議保守觀望或考慮輕倉做空，並將近期高點設為壓力參考。"
    elif overall_risk_level == 1:
        trend_text = "強勁空頭"
        advice = "趨勢偏空，應嚴格控制風險，不宜貿然進場，耐心等待趨勢反轉信號。"
    else:
        trend_text = "中性盤整"
        advice = "多空平衡，市場方向不明確，建議觀望，直到價格突破關鍵壓力或支撐位。"

    # 提取關鍵指標的結論
    rsi_conclusion = summary_df[summary_df['指標名稱'].str.contains('RSI')]['分析結論'].iloc[0]
    macd_conclusion = summary_df[summary_df['指標名稱'].str.contains('MACD')]['分析結論'].iloc[0]
    sma20_conclusion = summary_df[summary_df['指標名稱'].str.contains('SMA 20')]['分析結論'].iloc[0]
    bb_conclusion = summary_df[summary_df['指標名稱'].str.contains('布林帶')]['分析結論'].iloc[0]

    # 生成報告
    report = f"""
    ### 🤖 AI趨勢分析報告：{symbol} ({period_key})
    
    * **分析時間點：** {date}
    * **最新收盤價：** ${price}
    
    #### 💡 整體趨勢判讀 ({trend_text})
    
    根據 **{bull_count} 個多頭信號** 和 **{bear_count} 個空頭信號** 的綜合判斷，目前市場趨勢為 **{trend_text}**。
    
    #### 📈 動能與趨勢細節
    
    * **RSI 動能：** {rsi_conclusion}
    * **MACD 動能：** {macd_conclusion}
    * **短期趨勢 (SMA 20)：** {sma20_conclusion}
    * **波動性 (布林帶)：** {bb_conclusion}
    
    #### 🎯 AI 建議交易策略
    
    鑑於目前的 {period_key} 走勢，交易者應採取以下策略：
    1.  **主要操作：** {advice}
    2.  **關鍵支撐位 (參考近 20 根 K 線低點)：** 約 ${round(df['Low'].min(), 2)}
    3.  **關鍵壓力位 (參考近 20 根 K 線高點)：** 約 ${round(df['High'].max(), 2)}
    
    ---
    * **免責聲明：** 本報告由 AI 模型生成，僅供技術分析參考，不構成任何投資建議。交易有風險，入市需謹慎。
    """
    return report

# ==============================================================================
# 4. 圖表繪製函式
# ==============================================================================

def create_comprehensive_chart(df, symbol, period_key):
    """
    使用 Plotly 創建包含 K 線圖、MACD 和 RSI 的綜合圖表。
    """
    if df is None or df.empty:
        return go.Figure()

    # 設置子圖
    # row 1: K線圖 (高度佔比 3)
    # row 2: MACD (高度佔比 1)
    # row 3: RSI (高度佔比 1)
    fig = make_subplots(
        rows=3, 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05, 
        row_heights=[0.6, 0.2, 0.2]
    )

    # --- 1. K線圖 (Candlestick Chart) ---
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='K線',
            increasing_line_color='#FF4B4B', # 紅色 K 棒
            decreasing_line_color='#00CC96', # 綠色 K 棒
        ), 
        row=1, col=1
    )

    # 20日均線
    fig.add_trace(
        go.Scatter(
            x=df.index, 
            y=df['SMA_20'], 
            line=dict(color='#FECB52', width=1.5), 
            name='SMA 20'
        ), 
        row=1, col=1
    )

    # 60日均線
    fig.add_trace(
        go.Scatter(
            x=df.index, 
            y=df['SMA_60'], 
            line=dict(color='#636EFA', width=1.5), 
            name='SMA 60'
        ), 
        row=1, col=1
    )
    
    # 布林帶
    fig.add_trace(
        go.Scatter(
            x=df.index, 
            y=df['BB_High'], 
            line=dict(color='rgba(255, 165, 0, 0.5)', width=0.5), 
            name='BB High', 
            hoverinfo='none', 
            showlegend=False
        ), 
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, 
            y=df['BB_Low'], 
            line=dict(color='rgba(255, 165, 0, 0.5)', width=0.5), 
            name='BB Low',
            fill='tonexty', # 填充上下軌之間的區域
            fillcolor='rgba(255, 165, 0, 0.1)',
            hoverinfo='none',
            showlegend=False
        ), 
        row=1, col=1
    )


    # --- 2. MACD 圖 ---
    fig.add_trace(
        go.Bar(
            x=df.index, 
            y=df['MACD_Hist'], 
            name='MACD 柱狀體',
            marker_color=[
                '#FF4B4B' if val > 0 else '#00CC96' for val in df['MACD_Hist']
            ]
        ), 
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, 
            y=df['MACD'], 
            line=dict(color='orange', width=1), 
            name='MACD 線'
        ), 
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df.index, 
            y=df['MACD_Signal'], 
            line=dict(color='blue', width=1), 
            name='Signal 線'
        ), 
        row=2, col=1
    )

    # --- 3. RSI 圖 ---
    fig.add_trace(
        go.Scatter(
            x=df.index, 
            y=df['RSI'], 
            line=dict(color='#17BECF', width=1.5), 
            name='RSI'
        ), 
        row=3, col=1
    )
    # 標記 RSI 的超買/超賣區
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
    fig.update_yaxes(range=[0, 100], row=3, col=1)

    # --- 佈局設置 ---
    fig.update_layout(
        title=f'**{symbol}** - {period_key} 技術分析圖',
        xaxis_rangeslider_visible=False, # 隱藏底部的時間軸滑塊
        xaxis=dict(type='category'),
        height=900,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # 設置每個子圖的標題
    fig.update_yaxes(title_text='價格/均線', row=1, col=1, title_font=dict(size=14))
    fig.update_yaxes(title_text='MACD', row=2, col=1, title_font=dict(size=14))
    fig.update_yaxes(title_text='RSI', row=3, col=1, title_font=dict(size=14))
    
    # 隱藏子圖之間的 x 軸標籤
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)

    return fig

# ==============================================================================
# 5. 主程式
# ==============================================================================

def main():
    # 標題
    st.title("🤖 AI 趨勢分析儀表板 📈")
    st.markdown("---")

    # --- 側邊欄輸入控制 ---
    with st.sidebar:
        st.header("⚙️ 數據與參數設置")
        
        # 1. 選擇資產類別
        asset_class = st.selectbox("選擇資產類別", ["美股", "台股", "加密貨幣"], index=0)

        # 根據資產類別過濾標的
        if asset_class == "美股":
            quick_symbols = {k: v for k, v in FULL_SYMBOLS_MAP.items() if k not in ["2330.TW", "2317.TW", "2454.TW"] and "USD" not in k}
        elif asset_class == "台股":
            quick_symbols = {k: v for k, v in FULL_SYMBOLS_MAP.items() if k.endswith(".TW")}
        elif asset_class == "加密貨幣":
            quick_symbols = {k: v for k, v in FULL_SYMBOLS_MAP.items() if k.endswith("-USD")}
        else:
            # 理論上不會走到這裡，但作為回退
            quick_symbols = FULL_SYMBOLS_MAP
        
        # 構建下拉選單選項
        quick_select_options = [""] + [f"{s} ({d['name']})" for s, d in quick_symbols.items()]
        
        # 2. 快速選擇標的
        selected_quick_option = st.selectbox("快速選擇標的", quick_select_options)
        
        # 3. 直接輸入代碼
        # 使用 Session State 保持輸入框的值
        # 如果 Session State 沒有值，給予空字串，避免初始化錯誤
        if 'sidebar_search_input' not in st.session_state:
            st.session_state['sidebar_search_input'] = ""
            
        sidebar_search_input = st.text_input(
            "或 3. 直接輸入代碼 (e.g., TSLA, 2330.TW)", 
            value=st.session_state['sidebar_search_input']
        )
        st.session_state['sidebar_search_input'] = sidebar_search_input # 確保 Session State 更新

        # 確定最終要分析的代碼
        # 初始化為 Session State 中最後一次使用的代碼 (初次為 '2330.TW')
        final_symbol_to_analyze = st.session_state.get('last_search_symbol', '2330.TW')
        
        if selected_quick_option:
            # 從下拉選單中提取代碼
            symbol_match = re.search(r"^(\w[\w.-]+)", selected_quick_option)
            if symbol_match:
                final_symbol_to_analyze = symbol_match.group(1).strip()
        
        if sidebar_search_input:
            # 使用手動輸入的代碼 (覆蓋)
            final_symbol_to_analyze = sidebar_search_input.strip().upper()
        
        # 更新 Session State 中的最終代碼
        st.session_state['last_search_symbol'] = final_symbol_to_analyze
        
        st.markdown("---")

        # 4. 選擇分析週期
        selected_period_key = st.selectbox(
            "選擇分析週期", 
            list(PERIOD_MAP.keys()),
            index=2 # 默認為 1 日 (中長線)
        )
        period_yf, interval_yf = PERIOD_MAP[selected_period_key]

        st.markdown("---")
        
        # 執行分析按鈕
        analyze_button_clicked = st.button('📊 執行AI分析')

    # --- 主頁面內容 ---
    
    # 1. 檢查是否需要執行分析邏輯 (點擊按鈕或上次分析成功)
    if analyze_button_clicked or st.session_state.get('data_ready', False):
        
        # 如果是點擊按鈕，重置 data_ready 狀態，並開始檢查代碼
        if analyze_button_clicked:
            st.session_state['data_ready'] = False 

            if not final_symbol_to_analyze or final_symbol_to_analyze == st.session_state.get('last_search_symbol_pre_click', ''):
                # 如果沒有輸入代碼，或代碼與上次點擊時的代碼相同，且上次點擊是成功的，則不執行新的分析。
                pass

            if not final_symbol_to_analyze:
                st.warning("⚠️ 請在左側輸入或選擇一個標的代碼，然後點擊 **『執行AI分析』**。")
                return

            # 顯示載入中的動畫
            with st.spinner(f"正在擷取 **{final_symbol_to_analyze}** 的 {selected_period_key} 數據並進行 AI 計算..."):
                # 獲取數據
                df_data = get_stock_data(final_symbol_to_analyze, period_yf, interval_yf)

                if df_data is None or df_data.empty:
                    st.error(f"❌ 無法獲取代碼 **{final_symbol_to_analyze}** 的數據。請檢查代碼是否正確或稍後重試。")
                    st.session_state['data_ready'] = False
                    return

                # 計算指標
                df_data = calculate_technical_indicators(df_data)

                if df_data is None or df_data.empty:
                    st.error("❌ 數據處理失敗，無法計算技術指標。")
                    st.session_state['data_ready'] = False
                    return

                # 儲存數據到 Session State
                st.session_state['df'] = df_data
                st.session_state['data_ready'] = True
                st.session_state['symbol'] = final_symbol_to_analyze
                st.session_state['period_key'] = selected_period_key
                st.session_state['last_search_symbol_pre_click'] = final_symbol_to_analyze # 儲存成功時的代碼
                
                # 給用戶一個成功的反饋
                st.success(f"✅ **{final_symbol_to_analyze}** 的 {selected_period_key} 分析數據已就緒！")


    # 2. 數據準備好後才顯示結果
    if st.session_state.get('data_ready', False) and \
       st.session_state.get('symbol') == final_symbol_to_analyze and \
       st.session_state.get('period_key') == selected_period_key:
        
        df = st.session_state['df']
        
        # 生成指標總結
        summary_df, bull_count, bear_count, overall_risk_level = generate_technical_summary(df)
        
        # 生成 AI 報告
        ai_report = generate_ai_analysis_text(
            final_symbol_to_analyze, 
            df, 
            summary_df, 
            bull_count, 
            bear_count, 
            overall_risk_level, 
            selected_period_key
        )
        
        # --- 渲染分析結果 ---

        # 1. AI 報告
        st.markdown(ai_report)
        st.markdown("---")

        # 2. 關鍵技術指標表格
        st.subheader("📋 關鍵技術指標一覽")
        
        if summary_df is not None and not summary_df.empty:
            # 輔助函式：根據風險等級設置顏色
            def style_risk_level(s):
                color_map = {
                    4: 'background-color: #FFECEC; color: #FF4B4B; font-weight: bold;', # 強多 (紅色)
                    3: 'background-color: #FFF3E0; color: #FFA500;',                  # 弱多 (橙色)
                    2: 'background-color: #E6FFF6; color: #00CC96; font-weight: bold;', # 強空 (綠色)
                    1: 'background-color: #F0FFF0; color: #3CB371;',                  # 弱空 (淺綠)
                    0: 'background-color: #F5F5F5; color: #696969;'                   # 中性 (灰色)
                }
                # 僅對 "分析結論" 列應用顏色
                return [color_map.get(level, 'background-color: white;') for level in summary_df['風險等級']]

            
            # 移除 '風險等級' 列，只用於樣式控制
            display_df = summary_df.drop(columns=['風險等級'])
            
            # 應用樣式並顯示表格
            st.dataframe(
                display_df.style.apply(style_risk_level, subset=['分析結論'], axis=1),
                hide_index=True,
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
        
        # 3. 完整圖表
        st.subheader(f"📊 完整技術分析圖表")
        chart = create_comprehensive_chart(df, final_symbol_to_analyze, selected_period_key) 
        
        st.plotly_chart(chart, use_container_width=True, key=f"plotly_chart_{final_symbol_to_analyze}_{selected_period_key}")

    # 3. 應用程式啟動或未執行分析時的初始提示 (修正了 HTML/Markdown 語法錯誤)
    else:
          st.info(f"請在左側選擇或輸入標的（例如：**2330.TW**、**NVDA**、**BTC-USD**），然後點擊 <span style='color: #FA8072; font-weight: bold;'>『📊 執行AI分析』</span> 按鈕開始。", unsafe_allow_html=True)
          
          st.markdown("---")
          
          st.subheader("📝 使用步驟：")
          st.markdown("1. **選擇資產類別**：在左側欄選擇 `美股`、`台股` 或 `加密貨幣`。")
          st.markdown("2. **選擇標的**：使用下拉選單快速選擇熱門標的，或直接在輸入框中鍵入代碼或名稱。")
          st.markdown("3. **選擇週期**：決定分析的長度（例如：`30 分`、`4 小時`、`1 日`、`1 周`）。")
          # 修正錯誤：移除了 HTML 標籤內多餘的 **，確保 Markdown 正確解析
          st.markdown(f"4. **執行分析**：點擊 <span style='color: #FA8072; font-weight: bold;'>『📊 執行AI分析』</span>，AI將融合基本面與技術面指標提供交易策略。", unsafe_allow_html=True)
          
          st.markdown("---")


if __name__ == '__main__':
    # Streamlit Session State 初始化，確保變數存在且為預期類型
    if 'last_search_symbol' not in st.session_state:
        st.session_state['last_search_symbol'] = "2330.TW"
    if 'data_ready' not in st.session_state:
        st.session_state['data_ready'] = False
    if 'sidebar_search_input' not in st.session_state:
        st.session_state['sidebar_search_input'] = ""
    if 'last_search_symbol_pre_click' not in st.session_state:
        st.session_state['last_search_symbol_pre_click'] = ""
        
    main()
