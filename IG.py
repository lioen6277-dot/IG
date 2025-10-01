import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import ta
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, SMAIndicator
import warnings
import time
import re
from datetime import datetime, timedelta

# 忽略ta庫在計算時可能發出的警告
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
    "TSLA": {"name": "特斯拉", "keywords": ["特斯拉", "電動車", "TSLA", "Tesla"], "category": "美股 (US)"},
    "NVDA": {"name": "輝達", "keywords": ["輝達", "英偉達", "AI", "NVDA", "Nvidia"], "category": "美股 (US)"},
    "AAPL": {"name": "蘋果", "keywords": ["蘋果", "iPhone", "AAPL", "Apple"], "category": "美股 (US)"},
    "MSFT": {"name": "微軟", "keywords": ["微軟", "雲端", "MSFT", "Microsoft"], "category": "美股 (US)"},

    # ----------------------------------------------------
    # B. 台股核心 (TW Stocks) - 個股
    # ----------------------------------------------------
    "2330.TW": {"name": "台積電", "keywords": ["台積電", "晶圓", "2330", "TSMC"], "category": "台股 (TW)"},
    "2454.TW": {"name": "聯發科", "keywords": ["聯發科", "IC設計", "2454", "MediaTek"], "category": "台股 (TW)"},
    "2317.TW": {"name": "鴻海", "keywords": ["鴻海", "iPhone", "2317", "Foxconn"], "category": "台股 (TW)"},

    # ----------------------------------------------------
    # C. 加密貨幣 (Crypto)
    # ----------------------------------------------------
    "BTC-USD": {"name": "比特幣", "keywords": ["比特幣", "BTC", "Bitcoin"], "category": "加密貨幣 (Crypto)"},
    "ETH-USD": {"name": "以太幣", "keywords": ["以太幣", "ETH", "Ethereum"], "category": "加密貨幣 (Crypto)"},
}

# 資產類別與熱門標的映射
CATEGORY_MAP = {
    "美股 (US)": ["TSLA", "NVDA", "AAPL"],
    "台股 (TW)": ["2330.TW", "2454.TW"],
    "加密貨幣 (Crypto)": ["BTC-USD", "ETH-USD"],
}


# ==============================================================================
# 2. 核心數據處理與技術分析函數
# ==============================================================================

# @st.cache_data(ttl=600)  # 註釋掉快取，以便於調試
def get_symbol_info(symbol):
    """獲取標的的基本資訊。"""
    if not symbol:
        return {}
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        return {
            "longName": info.get('longName', symbol),
            "exchange": info.get('exchange', 'N/A'),
            "currency": info.get('currency', 'N/A'),
            "website": info.get('website', 'N/A'),
            "industry": info.get('industry', 'N/A')
        }
    except Exception as e:
        # print(f"Error fetching info for {symbol}: {e}")
        return {"longName": symbol, "exchange": "N/A", "currency": "N/A", "website": "N/A", "industry": "N/A"}

@st.cache_data(ttl=600)
def get_data_from_yfinance(symbol: str, period_key: str) -> tuple[pd.DataFrame, dict]:
    """
    從 Yahoo Finance 獲取歷史價格數據。

    Args:
        symbol (str): 標的代碼 (e.g., 'TSLA', '2330.TW').
        period_key (str): 週期鍵名 (e.g., '1 日 (中長線)').

    Returns:
        tuple[pd.DataFrame, dict]: 歷史數據DataFrame 和 標的資訊字典。
    """
    if not symbol or symbol == "請輸入代碼/名稱":
        return pd.DataFrame(), {}
    
    # 確保 period_key 是有效的鍵，並從 PERIOD_MAP 中正確解包出 period 和 interval
    if period_key not in PERIOD_MAP:
        raise ValueError(f"無效的週期鍵: {period_key}")

    # **錯誤修復點**: 確保這裡正確地解包出 period 和 interval，它們是字串。
    # yfinance_period 和 yfinance_interval 必須是字串，以傳遞給 yf.download()。
    yfinance_period, yfinance_interval = PERIOD_MAP[period_key]

    try:
        # 使用 yfinance.download 獲取數據
        df = yf.download(
            symbol, 
            period=yfinance_period, 
            interval=yfinance_interval, 
            progress=False
        )
        
        # 獲取標的資訊
        info_summary = get_symbol_info(symbol)

        if df.empty:
            st.error(f"❌ 數據獲取失敗: 無法取得 {symbol} 在 {period_key} 週期下的數據。請檢查代碼或選擇更長的週期。")
            return pd.DataFrame(), {}

        # 重新命名列名以符合 ta 庫和 Plotly 的慣例
        df.columns = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        df = df.dropna()
        
        return df, info_summary

    except Exception as e:
        # 這裡捕獲了原始的 'tuple' object has no attribute 'replace' 錯誤
        # 由於我們已經在函數開頭修復了變數類型問題，如果再次出現，可能是 yfinance 內部或其他地方的錯誤。
        st.error(f"❌ 數據獲取過程中發生錯誤: {repr(e)}。無法取得 **{symbol}** 的數據。請檢查代碼或選擇更長的週期。")
        return pd.DataFrame(), {}


def calculate_indicators(df):
    """計算關鍵技術指標並新增到 DataFrame."""
    if df.empty:
        return df

    # 1. 趨勢指標 (Trend) - MACD
    macd = MACD(close=df['Close'], window_fast=12, window_slow=26, window_sign=9)
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Diff'] = macd.macd_diff()

    # 2. 動能指標 (Momentum) - RSI
    df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()

    # 3. 波動性指標 (Volatility) - Bollinger Bands
    bollinger = BollingerBands(close=df['Close'], window=20, window_dev=2)
    df['BBL'] = bollinger.bollinger_lband()
    df['BBM'] = bollinger.bollinger_mavg()
    df['BBH'] = bollinger.bollinger_hband()

    # 4. 簡單移動平均線 (SMA)
    df['SMA5'] = SMAIndicator(close=df['Close'], window=5).sma_indicator()
    df['SMA20'] = SMAIndicator(close=df['Close'], window=20).sma_indicator()

    # 5. 交易量指標 (Volume) - Volume Average (VMA)
    df['VMA20'] = df['Volume'].rolling(window=20).mean()

    return df.dropna()

def generate_key_indicators_table(df):
    """
    生成關鍵技術指標的分析表格 (Pandas DataFrame)。
    
    分析結論：
    - MACD: MACD線 > Signal線 = 多頭動能強 (紅色)；反之為空頭 (綠色)。
    - RSI: > 70 = 超買 (橙色)；< 30 = 超賣 (紅色)；30~70 = 中性 (綠色)。
    - Close vs SMA20: Close > SMA20 = 多頭趨勢 (紅色)；反之為空頭 (綠色)。
    - BB: Close > BBH = 強勢突破 (紅色)；Close < BBL = 弱勢跌破 (綠色)。
    """
    if df.empty or len(df) < 20: # 確保有足夠的數據來計算指標 (至少20天)
        return pd.DataFrame()

    latest = df.iloc[-1]
    
    # 初始化表格數據
    data = []
    
    # --- 1. MACD ---
    macd_val = latest['MACD_Diff']
    macd_color = '🟠'
    macd_conclusion = "中性/震盪"
    if macd_val > 0.1 * abs(latest['MACD_Signal']):
        macd_conclusion = "多頭動能：MACD上穿Signal (紅)"
        macd_color = '🔴'
    elif macd_val < -0.1 * abs(latest['MACD_Signal']):
        macd_conclusion = "空頭動能：MACD下穿Signal (綠)"
        macd_color = '🟢'
    data.append({
        "指標": "MACD", 
        "最新值": f"{macd_val:.2f}", 
        "分析結論": macd_conclusion,
        "__color__": macd_color
    })

    # --- 2. RSI ---
    rsi_val = latest['RSI']
    rsi_color = '🟢'
    rsi_conclusion = "中性：動能平衡"
    if rsi_val > 70:
        rsi_conclusion = "超買：短期回檔風險高 (橙)"
        rsi_color = '🟠'
    elif rsi_val < 30:
        rsi_conclusion = "超賣：短期反彈潛力大 (紅)"
        rsi_color = '🔴'
    data.append({
        "指標": "RSI (14)", 
        "最新值": f"{rsi_val:.2f}", 
        "分析結論": rsi_conclusion,
        "__color__": rsi_color
    })

    # --- 3. SMA20 趨勢 ---
    close = latest['Close']
    sma20 = latest['SMA20']
    sma_color = '🟢'
    sma_conclusion = "空頭趨勢：價格位於均線之下"
    if close > sma20:
        sma_conclusion = "多頭趨勢：價格位於均線之上 (紅)"
        sma_color = '🔴'
    data.append({
        "指標": "股價 vs SMA20", 
        "最新值": f"{close:.2f} / {sma20:.2f}", 
        "分析結論": sma_conclusion,
        "__color__": sma_color
    })

    # --- 4. 布林帶 (BB) 波動 ---
    bbl = latest['BBL']
    bbh = latest['BBH']
    bb_color = '🟠'
    bb_conclusion = "波動中性：價格在布林帶內"
    if close > bbh:
        bb_conclusion = "強勢突破：位於上軌之上 (紅)"
        bb_color = '🔴'
    elif close < bbl:
        bb_conclusion = "弱勢跌破：位於下軌之下 (綠)"
        bb_color = '🟢'
    data.append({
        "指標": "布林帶", 
        "最新值": f"H:{bbh:.2f} M:{latest['BBM']:.2f} L:{bbl:.2f}", 
        "分析結論": bb_conclusion,
        "__color__": bb_color
    })

    df_table = pd.DataFrame(data)
    
    # 刪除顏色標籤欄位，但Streamlit可以利用它來著色
    df_table.set_index("指標", inplace=True)
    return df_table


def create_comprehensive_chart(df, symbol_name, period_key):
    """創建包含 K 線圖、RSI、MACD 的綜合 Plotly 圖表。"""
    if df.empty:
        return go.Figure()

    # 設置子圖
    fig = make_subplots(
        rows=4, 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        row_heights=[0.6, 0.15, 0.15, 0.1], # 價格/交易量/RSI/MACD
        # 命名子圖的 Y 軸
        row_titles=[
            f'{symbol_name} - 價格 K 線 ({period_key})', 
            '交易量', 
            '相對強弱指標 (RSI)', 
            '移動平均線聚合/離散 (MACD)'
        ]
    )

    # --- Row 1: K 線圖 ---
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='K線',
        increasing_line_color='#FF0055',  # 紅色上漲
        decreasing_line_color='#00AA66'   # 綠色下跌
    ), row=1, col=1)

    # 移動平均線 (SMA5 & SMA20)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA5'], line=dict(color='#FFA500', width=1.5), name='SMA 5'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], line=dict(color='#1E90FF', width=2), name='SMA 20'), row=1, col=1)
    
    # 布林帶
    fig.add_trace(go.Scatter(x=df.index, y=df['BBH'], line=dict(color='rgba(255,165,0,0.5)', width=1, dash='dot'), name='BB 上軌'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BBL'], line=dict(color='rgba(255,165,0,0.5)', width=1, dash='dot'), name='BB 下軌'), row=1, col=1)
    
    # --- Row 2: 交易量 ---
    colors = ['#FF0055' if c >= o else '#00AA66' for o, c in zip(df['Open'], df['Close'])]
    fig.add_trace(go.Bar(
        x=df.index, 
        y=df['Volume'], 
        name='交易量', 
        marker_color=colors,
        opacity=0.8
    ), row=2, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['VMA20'], line=dict(color='#A0A0A0', width=1), name='VMA 20'), row=2, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1, tickformat=".2s", showgrid=False)

    # --- Row 3: RSI ---
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='#9400D3', width=2), name='RSI'), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#FF4136", row=3, col=1) # 超買線
    fig.add_hline(y=30, line_dash="dash", line_color="#2ECC40", row=3, col=1) # 超賣線
    fig.update_yaxes(range=[0, 100], row=3, col=1, showgrid=False)

    # --- Row 4: MACD ---
    histogram_colors = ['#FF0055' if val > 0 else '#00AA66' for val in df['MACD_Diff']]
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Diff'], name='Histogram', marker_color=histogram_colors, opacity=0.7), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], line=dict(color='#FFD700', width=2), name='MACD'), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], line=dict(color='#00BFFF', width=1), name='Signal'), row=4, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="#808080", row=4, col=1)
    fig.update_yaxes(showgrid=False, row=4, col=1)

    # --- 整體佈局設定 ---
    fig.update_layout(
        title={
            'text': f"**{symbol_name} ({symbol_name}) 趨勢分析圖表**",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        height=900,
        xaxis_tickformat='%Y-%m-%d',
        hovermode="x unified",
        template="plotly_dark",
        margin=dict(l=20, r=20, t=100, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # 隱藏除底部以外的 x 軸
    fig.update_xaxes(showgrid=False, rangeslider_visible=False) 
    fig.update_xaxes(row=4, col=1, showgrid=True) 

    # 隱藏右側的 y 軸
    fig.update_yaxes(showticklabels=True, title_standoff=0, row=1, col=1)
    fig.update_yaxes(showticklabels=True, title_standoff=0, row=2, col=1)
    fig.update_yaxes(showticklabels=True, title_standoff=0, row=3, col=1)
    fig.update_yaxes(showticklabels=True, title_standoff=0, row=4, col=1)
    
    return fig


# ==============================================================================
# 3. Streamlit UI 介面
# ==============================================================================

def main_app():
    """主應用程式邏輯與 UI 結構。"""
    
    st.title("🤖 AI 投資趨勢分析儀表板 📈")
    st.markdown("---")

    # ==========================================================================
    # 側邊欄 (Sidebar) - 輸入與設定
    # ==========================================================================
    st.sidebar.header("🛠️ 分析參數設定")
    
    # 1. 資產類別選擇
    selected_category = st.sidebar.selectbox(
        "選擇資產類別:",
        list(CATEGORY_MAP.keys()),
        key='selected_category'
    )
    
    # 根據資產類別更新快速選擇列表
    available_quick_symbols = CATEGORY_MAP.get(selected_category, [])
    
    # 2. 快速選擇標的
    quick_symbols_options = ["請選擇"] + available_quick_symbols
    selected_quick_symbol = st.sidebar.selectbox(
        f"快速選擇標的 (推薦):",
        quick_symbols_options,
        index=0,
        key='selected_quick_symbol'
    )
    
    # 3. 手動輸入代碼/名稱
    default_input = ""
    # 如果使用者選擇了快速標的，將其設定為輸入框的預設值
    if selected_quick_symbol != "請選擇":
        default_input = selected_quick_symbol
    elif st.session_state.get('last_search_symbol') and st.session_state['last_search_symbol'] not in available_quick_symbols and st.session_state['last_search_symbol'] != "請輸入代碼/名稱":
        # 如果上次搜尋的不是當前類別的快速標的，則保留上次的輸入
        default_input = st.session_state['last_search_symbol']
    
    sidebar_search_input = st.sidebar.text_input(
        "或手動輸入代碼/名稱 (如 2330.TW, NVDA, BTC-USD):",
        value=default_input,
        key='sidebar_search_input'
    )

    # 確定最終要分析的標的
    if selected_quick_symbol != "請選擇":
        final_symbol_to_analyze = selected_quick_symbol.strip().upper()
    else:
        final_symbol_to_analyze = sidebar_search_input.strip().upper()
    
    # 4. 週期選擇
    selected_period_key = st.sidebar.selectbox(
        "選擇分析週期:",
        list(PERIOD_MAP.keys()),
        key='selected_period_key'
    )
    
    # 5. 執行按鈕
    analyze_button_clicked = st.sidebar.button("📊 執行AI分析", type="primary")

    # ==========================================================================
    # 主面板 (Main Panel) - 輸出結果
    # ==========================================================================

    if analyze_button_clicked and final_symbol_to_analyze and final_symbol_to_analyze != "請輸入代碼/名稱":
        # 更新 session state
        st.session_state['last_search_symbol'] = final_symbol_to_analyze
        st.session_state['data_ready'] = False # 重置數據狀態
        
        with st.spinner(f"正在為 {final_symbol_to_analyze} 獲取數據與執行 AI 分析..."):
            try:
                # 執行資料獲取 (這裡包含了 **錯誤修復** 後的 get_data_from_yfinance)
                df, info_summary = get_data_from_yfinance(final_symbol_to_analyze, selected_period_key)

                if not df.empty:
                    # 2. 計算技術指標
                    df = calculate_indicators(df)
                    st.session_state['df'] = df
                    st.session_state['info_summary'] = info_summary
                    st.session_state['data_ready'] = True
                    st.session_state['final_symbol_to_analyze'] = final_symbol_to_analyze
                    st.session_state['selected_period_key'] = selected_period_key
                    
                    st.success(f"✅ 成功獲取 **{info_summary['longName']} ({final_symbol_to_analyze})** 的數據！正在生成分析報告...")
                    
                else:
                    # 如果 df 為空，get_data_from_yfinance 已經顯示錯誤信息
                    st.session_state['data_ready'] = False

            except Exception as e:
                # 捕獲所有其他未預期的錯誤
                st.session_state['data_ready'] = False
                st.error(f"❌ 發生意外錯誤: {repr(e)}。請檢查輸入代碼或聯繫開發者。")
                print(f"DEBUG: Unhandled error during analysis: {e}")
    
    # 顯示分析結果
    if st.session_state.get('data_ready', False):
        df = st.session_state['df']
        info_summary = st.session_state['info_summary']
        final_symbol_to_analyze = st.session_state['final_symbol_to_analyze']
        selected_period_key = st.session_state['selected_period_key']

        st.header(f"📈 {info_summary['longName']} ({final_symbol_to_analyze}) 趨勢分析報告")
        st.caption(f"分析週期: **{selected_period_key}** | 交易所: **{info_summary['exchange']}** | 貨幣: **{info_summary['currency']}**")
        st.markdown("---\n")
        
        # --- 關鍵技術指標表格 ---
        st.subheader(f"🔍 關鍵技術指標判讀")
        indicators_df = generate_key_indicators_table(df)

        if not indicators_df.empty:
            # 應用顏色樣式 (使用 Streamlit 的內建列配置)
            st.dataframe(
                indicators_df.style.applymap(
                    lambda x: 'background-color: #F0A0A0' if '紅' in str(x) else 
                              'background-color: #A0FFA0' if '綠' in str(x) else 
                              'background-color: #FFDDA0' if '橙' in str(x) else '',
                    subset=pd.IndexSlice[:, ['分析結論']]
                ),
                column_config={
                    "最新值": st.column_config.Column("最新數值", help="技術指標的最新計算值"),
                    "分析結論": st.column_config.Column("趨勢/動能判讀", help="基於數值範圍的專業解讀"),
                },
                use_container_width=True
            )
            st.caption("ℹ️ **設計師提示:** 表格顏色會根據指標的趨勢/風險等級自動變化（**紅色=多頭/強化信號**（類似低風險買入），**綠色=空頭/削弱信號**（類似高風險賣出），**橙色=中性/警告**）。")

        else:
            st.info("無足夠數據生成關鍵技術指標表格。")

        st.markdown("---\n")
        
        # --- 完整技術分析圖表 ---
        st.subheader(f"📊 完整技術分析圖表")
        chart = create_comprehensive_chart(df, info_summary['longName'], selected_period_key)
        
        st.plotly_chart(chart, use_container_width=True, key=f"plotly_chart_{final_symbol_to_analyze}_{selected_period_key}")

    elif not st.session_state.get('data_ready', False) and not analyze_button_clicked:
          st.info("請在左側選擇或輸入標的，然後點擊 **『📊 執行AI分析』** 開始。")

    elif analyze_button_clicked and (not final_symbol_to_analyze or final_symbol_to_analyze == "請輸入代碼/名稱"):
          st.warning("⚠️ 請在左側輸入有效的標的代碼或名稱。")


if __name__ == '__main__':
    # Streamlit Session State 初始化，確保變數存在
    if 'last_search_symbol' not in st.session_state:
        st.session_state['last_search_symbol'] = "TSLA"
    if 'data_ready' not in st.session_state:
        st.session_state['data_ready'] = False
    if 'sidebar_search_input' not in st.session_state:
        st.session_state['sidebar_search_input'] = ""
    if 'df' not in st.session_state:
        st.session_state['df'] = pd.DataFrame()
    if 'info_summary' not in st.session_state:
        st.session_state['info_summary'] = {}
        
    main_app()
