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
    "GOOGL": {"name": "谷歌", "keywords": ["谷歌", "搜尋", "GOOGL", "Google"]},
    "MSFT": {"name": "微軟", "keywords": ["微軟", "雲端", "MSFT", "Microsoft"]},
    # ----------------------------------------------------
    # B. 台股核心 (TW Stocks) - 個股
    # ----------------------------------------------------
    "2330.TW": {"name": "台積電", "keywords": ["台積電", "晶圓", "2330", "TSMC"]},
    "2454.TW": {"name": "聯發科", "keywords": ["聯發科", "手機晶片", "2454", "MediaTek"]},
    "2317.TW": {"name": "鴻海", "keywords": ["鴻海", "富士康", "2317", "Foxconn"]},
    # ----------------------------------------------------
    # C. 加密貨幣 (Crypto)
    # ----------------------------------------------------
    "BTC-USD": {"name": "比特幣", "keywords": ["比特幣", "BTC", "Bitcoin"]},
    "ETH-USD": {"name": "以太幣", "keywords": ["以太幣", "ETH", "Ethereum"]},
    # ----------------------------------------------------
    # D. 指數/ETF
    # ----------------------------------------------------
    "^GSPC": {"name": "標普500", "keywords": ["標普500", "S&P 500", "GSPC"]},
    "^TWII": {"name": "台灣加權指數", "keywords": ["台灣加權", "TWII", "加權指數"]},
}

# ==============================================================================
# 2. 數據下載與處理函式
# ==============================================================================

@st.cache_data(ttl=600) # 數據緩存 10 分鐘
def download_data(symbol, period, interval):
    """
    從 Yahoo Finance 下載歷史價格數據。
    """
    try:
        data = yf.download(symbol, period=period, interval=interval, progress=False)
        
        if data.empty:
            st.error(f"❌ 錯誤: 找不到標的代碼 {symbol} 的數據或數據不足。請確認代碼是否正確。")
            return pd.DataFrame() # 返回空 DataFrame
            
        data.index.name = 'Date'
        # 移除任何有 NaN 值的列以確保指標計算的準確性
        data = data.dropna()
        
        # 確保有足夠的數據行（例如至少 30 筆數據才能計算大部分指標）
        if len(data) < 30:
            st.error(f"⚠️ 數據不足: 至少需要 30 筆數據才能進行完整的技術分析。目前只有 {len(data)} 筆數據。")
            return pd.DataFrame()
            
        return data.reset_index()
    except Exception as e:
        st.error(f"❌ 數據下載失敗: {e}")
        return pd.DataFrame()

# ==============================================================================
# 3. 技術指標計算與分析函式
# ==============================================================================

def calculate_technical_indicators(df):
    """
    計算一系列關鍵技術指標並增加分析結論。
    """
    if df.empty:
        return df

    # --- 趨勢/動能指標 ---
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['RSI_14'] = ta.momentum.rsi(df['Close'], window=14)
    df['MACD_Line'] = ta.trend.macd_diff(df['Close']) # 直接用 MACD 柱狀圖線
    df['ATR_14'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
    df['BB_High'] = ta.volatility.bollinger_hband(df['Close'], window=20, window_dev=2)
    df['BB_Low'] = ta.volatility.bollinger_lband(df['Close'], window=20, window_dev=2)

    # --- 整理成表格所需的最新指標值和分析 ---
    latest = df.iloc[-1]
    
    analysis_data = {
        "指標名稱": ["收盤價", "20日均線 (SMA)", "相對強弱指數 (RSI)", "MACD 動能線", "平均真實波動幅度 (ATR)", "布林帶 (BB) 上軌", "布林帶 (BB) 下軌"],
        "最新值": [
            f"{latest['Close']:.2f}",
            f"{latest['SMA_20']:.2f}",
            f"{latest['RSI_14']:.2f}",
            f"{latest['MACD_Line']:.4f}",
            f"{latest['ATR_14']:.2f}",
            f"{latest['BB_High']:.2f}",
            f"{latest['BB_Low']:.2f}",
        ],
        "分析結論": [
            "當前價格",
            "趨勢方向",
            "超買/超賣",
            "動能強度",
            "波動性",
            "壓力位",
            "支撐位",
        ],
        "顏色標籤": ["Neutral"] * 7, # 預設中性
        "原始數值": [
            latest['Close'],
            latest['SMA_20'],
            latest['RSI_14'],
            latest['MACD_Line'],
            latest['ATR_14'],
            latest['BB_High'],
            latest['BB_Low'],
        ]
    }
    
    # --- 根據最新值進行專業解讀 ---
    
    # 1. 收盤價相對於 SMA_20
    if latest['Close'] > latest['SMA_20']:
        analysis_data["分析結論"][1] = "多頭趨勢 (價格在均線之上)"
        analysis_data["顏色標籤"][1] = "Bullish"
    elif latest['Close'] < latest['SMA_20']:
        analysis_data["分析結論"][1] = "空頭趨勢 (價格在均線之下)"
        analysis_data["顏色標籤"][1] = "Bearish"
    else:
        analysis_data["分析結論"][1] = "中性/盤整"
        analysis_data["顏色標籤"][1] = "Neutral"

    # 2. RSI (超買/超賣)
    if latest['RSI_14'] > 70:
        analysis_data["分析結論"][2] = "超買 (賣出警示)"
        analysis_data["顏色標籤"][2] = "Bearish"
    elif latest['RSI_14'] < 30:
        analysis_data["分析結論"][2] = "超賣 (買入警示)"
        analysis_data["顏色標籤"][2] = "Bullish"
    else:
        analysis_data["分析結論"][2] = "中性動能"
        analysis_data["顏色標籤"][2] = "Neutral"

    # 3. MACD Line (動能強度)
    if latest['MACD_Line'] > 0:
        analysis_data["分析結論"][3] = "多頭動能增強 (柱狀圖在零軸上)"
        analysis_data["顏色標籤"][3] = "Bullish"
    elif latest['MACD_Line'] < 0:
        analysis_data["分析結論"][3] = "空頭動能增強 (柱狀圖在零軸下)"
        analysis_data["顏色標籤"][3] = "Bearish"
    else:
        analysis_data["分析結論"][3] = "動能趨緩"
        analysis_data["顏色標籤"][3] = "Neutral"
        
    # 4. ATR (波動性) - 簡單判斷
    # ATR本身不判斷方向，只判斷波動大小，故常設為中性
    analysis_data["分析結論"][4] = f"高波動區 ({latest['ATR_14']:.2f})" if latest['ATR_14'] > df['ATR_14'].mean() else f"低波動區 ({latest['ATR_14']:.2f})"
    analysis_data["顏色標籤"][4] = "Warning" if latest['ATR_14'] > df['ATR_14'].mean() else "Neutral"


    # 5. 收盤價相對於布林帶
    if latest['Close'] > latest['BB_High']:
        analysis_data["分析結論"][5] = "極端強勢 (高風險區)"
        analysis_data["顏色標籤"][5] = "Bearish" # 價格穿出上軌視為反轉警示 (賣壓)
    else:
        analysis_data["分析結論"][5] = "正常壓力位"
        analysis_data["顏色標籤"][5] = "Neutral"

    if latest['Close'] < latest['BB_Low']:
        analysis_data["分析結論"][6] = "極端弱勢 (低風險區)"
        analysis_data["顏色標籤"][6] = "Bullish" # 價格穿出下軌視為反轉警示 (買盤)
    else:
        analysis_data["分析結論"][6] = "正常支撐位"
        analysis_data["顏色標籤"][6] = "Neutral"

    
    final_df = pd.DataFrame(analysis_data)
    
    # 應用顏色函式
    def color_rows(row):
        color = row['顏色標籤']
        if color == "Bullish":
            # 趨勢強化、低風險買入 (紅色 - 股價向上趨勢)
            return ['background-color: rgba(255, 99, 132, 0.4)'] * len(row) # 柔和紅
        elif color == "Bearish":
            # 趨勢削弱、高風險賣出 (綠色 - 股價向下趨勢)
            return ['background-color: rgba(75, 192, 192, 0.4)'] * len(row) # 柔和綠
        elif color == "Warning":
            # 警告/中性 (橙色)
            return ['background-color: rgba(255, 206, 86, 0.4)'] * len(row) # 柔和橙
        else:
            return [''] * len(row)

    styled_df = final_df[["指標名稱", "最新值", "分析結論"]].style.apply(color_rows, axis=1)
    
    return df, styled_df

# ==============================================================================
# 4. 圖表繪製函式
# ==============================================================================

def create_comprehensive_chart(df, symbol, period_key):
    """
    創建一個包含K線圖、成交量、RSI和MACD的綜合圖表。
    """
    if df.empty:
        return go.Figure()

    # 設置子圖
    # 1. K線圖 + MA (主要圖)
    # 2. 成交量 (第二圖)
    # 3. RSI (第三圖)
    # 4. MACD (第四圖)
    fig = make_subplots(
        rows=4, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.08,
        row_heights=[0.5, 0.15, 0.15, 0.2]
    )

    # --- 1. K線圖 (Row 1) ---
    fig.add_trace(go.Candlestick(
        x=df['Date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='K線',
        showlegend=True,
        increasing_line_color='red', 
        decreasing_line_color='green'
    ), row=1, col=1)

    # 增加均線 (SMA_20)
    fig.add_trace(go.Scatter(
        x=df['Date'], 
        y=df['SMA_20'], 
        line=dict(color='#8B008B', width=1.5), 
        name='SMA-20',
        opacity=0.7,
        showlegend=True
    ), row=1, col=1)
    
    # 增加布林帶
    fig.add_trace(go.Scatter(
        x=df['Date'], 
        y=df['BB_High'], 
        line=dict(color='rgba(255, 165, 0, 0.5)', width=1), 
        name='BB Upper',
        showlegend=False
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=df['Date'], 
        y=df['BB_Low'], 
        line=dict(color='rgba(255, 165, 0, 0.5)', width=1), 
        name='BB Lower',
        showlegend=False,
        fill='tonexty', # 填充上下軌之間的區域
        fillcolor='rgba(255, 165, 0, 0.1)'
    ), row=1, col=1)

    # --- 2. 成交量 (Row 2) ---
    fig.add_trace(go.Bar(
        x=df['Date'], 
        y=df['Volume'], 
        name='成交量',
        marker_color='rgba(128, 128, 128, 0.7)',
        showlegend=False
    ), row=2, col=1)

    # --- 3. RSI (Row 3) ---
    fig.add_trace(go.Scatter(
        x=df['Date'], 
        y=df['RSI_14'], 
        line=dict(color='blue', width=1.5), 
        name='RSI',
        showlegend=False
    ), row=3, col=1)
    
    # RSI 超買/超賣線
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5, row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", opacity=0.5, row=3, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=3, col=1)

    # --- 4. MACD (Row 4) ---
    # MACD 柱狀圖 (Histogram)
    macd_hist_color = np.where(df['MACD_Line'] > 0, 'red', 'green')
    fig.add_trace(go.Bar(
        x=df['Date'], 
        y=df['MACD_Line'], 
        name='MACD Hist',
        marker_color=macd_hist_color,
        showlegend=False
    ), row=4, col=1)
    
    # MACD 零軸
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5, row=4, col=1)
    fig.update_yaxes(title_text="MACD", row=4, col=1)


    # --- 佈局設置 ---
    fig.update_layout(
        title=f"📈 **{symbol}** - {period_key} 綜合技術分析圖",
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        template="plotly_white", # 使用白色背景模板
        height=800,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # 隱藏子圖的 X 軸標籤，只保留最底部的
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=3, col=1)
    fig.update_xaxes(showticklabels=True, row=4, col=1)
    
    # 調整 Y 軸，隱藏成交量軸的標籤 (看起來更簡潔)
    fig.update_yaxes(title_text="價格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", showticklabels=False, row=2, col=1)


    return fig

# ==============================================================================
# 5. 主應用程式邏輯
# ==============================================================================

def main_app():
    # 檢查並確保所有必要的 Session State 變數存在
    if 'last_search_symbol' not in st.session_state:
        st.session_state['last_search_symbol'] = "2330.TW"
    if 'data_ready' not in st.session_state:
        st.session_state['data_ready'] = False
    if 'sidebar_search_input' not in st.session_state:
        st.session_state['sidebar_search_input'] = st.session_state['last_search_symbol']
    if 'selected_period' not in st.session_state:
         st.session_state['selected_period'] = "1 日 (中長線)"
    if 'selected_category' not in st.session_state:
        st.session_state['selected_category'] = "台股"
        
    # --- 側邊欄配置 ---
    st.sidebar.title("🛠️ 參數配置")

    # 1. 資產類別選擇
    category = st.sidebar.selectbox(
        "選擇資產類別:",
        ["美股", "台股", "加密貨幣", "指數/ETF"],
        key='selected_category'
    )

    # 2. 熱門標的選擇 (根據類別過濾)
    category_symbols = {
        "美股": [s for s, d in FULL_SYMBOLS_MAP.items() if s in ["TSLA", "NVDA", "AAPL", "GOOGL", "MSFT"]],
        "台股": [s for s, d in FULL_SYMBOLS_MAP.items() if s in ["2330.TW", "2454.TW", "2317.TW"]],
        "加密貨幣": [s for s, d in FULL_SYMBOLS_MAP.items() if s in ["BTC-USD", "ETH-USD"]],
        "指數/ETF": [s for s, d in FULL_SYMBOLS_MAP.items() if s in ["^GSPC", "^TWII"]],
    }.get(category, [])
    
    options_list = [f"{s} ({FULL_SYMBOLS_MAP[s]['name']})" for s in category_symbols]
    options_list.insert(0, "--- 或自訂輸入 ---")
    
    selected_symbol_option = st.sidebar.selectbox(
        "快速選擇熱門標的:",
        options_list,
        index=0
    )
    
    default_symbol_input = ""
    if selected_symbol_option != "--- 或自訂輸入 ---":
        # 解析選中的代碼
        default_symbol_input = selected_symbol_option.split(' ')[0]
        st.session_state['sidebar_search_input'] = default_symbol_input

    # 3. 自訂輸入框
    search_input = st.sidebar.text_input(
        "輸入標的代碼或名稱 (例如: NVDA, 2330.TW):", 
        value=st.session_state.get('sidebar_search_input', st.session_state['last_search_symbol']),
        key='sidebar_search_input'
    )
    
    # 4. 週期選擇
    selected_period_key = st.sidebar.selectbox(
        "選擇分析週期:",
        list(PERIOD_MAP.keys()),
        key='selected_period'
    )

    # 5. 執行按鈕
    analyze_button_clicked = st.sidebar.button("📊 執行AI分析", type="primary", use_container_width=True)

    # --- 處理分析邏輯 ---
    if analyze_button_clicked:
        st.session_state['last_search_symbol'] = search_input
        st.session_state['data_ready'] = False # 重新開始數據獲取

    final_symbol_to_analyze = st.session_state['last_search_symbol'].upper().strip()

    # **************************************************************************
    # * 這裡是最可能出現 'return' outside function 錯誤的地方 (主體邏輯的開頭) *
    # **************************************************************************
    
    # 如果按鈕被點擊或數據已準備好 (觸發重繪)
    if final_symbol_to_analyze and (analyze_button_clicked or st.session_state.get('data_ready', False)):
        
        # 從 Session State 取得週期參數
        selected_period_key = st.session_state['selected_period']
        period, interval = PERIOD_MAP[selected_period_key]
        
        # 顯示載入狀態
        with st.spinner(f"正在下載 {final_symbol_to_analyze} 的 {selected_period_key} 數據..."):
            df = download_data(final_symbol_to_analyze, period, interval)
        
        # --- 數據驗證：這裡可能就是原先第 482 行 'return' 的位置 ---
        if df.empty:
            st.session_state['data_ready'] = False
            # ** 修正：用 st.stop() 替換原本的 return **
            st.warning("數據載入失敗或數據不足，請檢查標的代碼或稍後再試。")
            st.stop() # 停止 Streamlit 繼續執行後續分析邏輯
            
        # 數據已準備好，儲存到 Session State
        st.session_state['data_ready'] = True
        st.session_state['df'] = df # 儲存 DataFrame 以便重複使用

        # --- 執行分析與渲染 ---
        
        # 標題與簡介
        st.title(f"🚀 {final_symbol_to_analyze} AI 趨勢分析儀表板")
        st.markdown(f"**分析週期:** {selected_period_key} | **時間範圍:** {period} | **數據間隔:** {interval}")
        st.caption(f"數據時間範圍: {df['Date'].min().strftime('%Y-%m-%d')} 至 {df['Date'].max().strftime('%Y-%m-%d')}")
        st.markdown(\"\"\"
        <style>
        .st-emotion-cache-1r6c2qf {{ font-weight: bold; font-size: 1.1em; }}
        </style>
        \"\"\", unsafe_allow_html=True)
        
        st.markdown("---")

        # 1. 關鍵技術指標表格
        with st.spinner("正在計算與解讀關鍵技術指標..."):
            df, styled_tech_df = calculate_technical_indicators(df)

        st.subheader(f"🔍 關鍵技術指標一覽 (最新數據)")

        if not df.empty:
            # 確保 df 中有所有需要的列 (避免 KeyError)
            # 因為 styled_tech_df 已經是 style 物件，直接顯示
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
        
        # 2. 完整圖表
        st.subheader(f"📊 完整技術分析圖表")
        chart = create_comprehensive_chart(df, final_symbol_to_analyze, selected_period_key)
        
        st.plotly_chart(chart, use_container_width=True, key=f"plotly_chart_{final_symbol_to_analyze}_{selected_period_key}")

    elif not st.session_state.get('data_ready', False) and not analyze_button_clicked:
          st.info(\"\"\"
          <h4 style='color: #4A90E2; font-weight: bold;'>歡迎使用 AI 趨勢分析儀表板！</h4>
          請在左側選擇或輸入標的（例如 **TSLA**、**2330.TW**、**BTC-USD**），然後點擊 <span style='color: #FA8072; font-weight: bold;'>『📊 執行AI分析』</span> 按鈕開始。
          \"\"\", unsafe_allow_html=True)
          
          st.markdown("---")
          
          st.subheader("📝 使用步驟：")
          st.markdown("1. **選擇資產類別**：在左側欄選擇 `美股`、`台股` 或 `加密貨幣`。")
          st.markdown("2. **選擇標的**：使用下拉選單快速選擇熱門標的，或直接在輸入框中鍵入代碼或名稱。")
          st.markdown("3. **選擇週期**：決定分析的長度（例如：`30 分`、`4 小時`、`1 日`、`1 周`）。")
          st.markdown(f"4. **執行分析**：點擊 <span style='color: #FA8072; font-weight: bold;'>『📊 執行AI分析』**</span>，AI將融合基本面與技術面指標提供交易策略。", unsafe_allow_html=True)
          
          st.markdown("---")


if __name__ == '__main__':
    main_app()
