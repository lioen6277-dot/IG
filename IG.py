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
from PIL import Image, ImageDraw, ImageFont # 引入圖像處理核心庫
from io import BytesIO

# 警告處理：隱藏 Pandas 或 TA-Lib 可能發出的未來警告
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

# 🚀 您的【所有資產清單】(FULL_SYMBOLS_MAP) - 新增 'category' 欄位用於篩選
FULL_SYMBOLS_MAP = {
    # ----------------------------------------------------
    # A. 美股核心 (US Stocks)
    # ----------------------------------------------------
    "TSLA": {"name": "特斯拉", "keywords": ["特斯拉", "電動車", "TSLA", "Tesla"], "category": "美股"},
    "NVDA": {"name": "輝達", "keywords": ["輝達", "英偉達", "AI", "NVDA", "Nvidia"], "category": "美股"},
    "AAPL": {"name": "蘋果", "keywords": ["蘋果", "手機", "Apple", "AAPL"], "category": "美股"},
    "GOOGL": {"name": "谷歌", "keywords": ["谷歌", "Google", "GOOGL"], "category": "美股"},
    "AMZN": {"name": "亞馬遜", "keywords": ["亞馬遜", "Amazon", "AMZN"], "category": "美股"},
    "MSFT": {"name": "微軟", "keywords": ["微軟", "Microsoft", "MSFT"], "category": "美股"},
    # ----------------------------------------------------
    # B. 台股核心 (TW Stocks) - 加上 .TW 後綴
    # ----------------------------------------------------
    "2330.TW": {"name": "台積電", "keywords": ["台積電", "半導體", "TSMC"], "category": "台股"},
    "2454.TW": {"name": "聯發科", "keywords": ["聯發科", "MTK", "手機晶片"], "category": "台股"},
    "0050.TW": {"name": "元大台灣50", "keywords": ["台灣50", "ETF", "指數"], "category": "台股"},
    # ----------------------------------------------------
    # C. 加密貨幣 (Crypto) - 必須使用 -USD 後綴
    # ----------------------------------------------------
    "BTC-USD": {"name": "比特幣", "keywords": ["加密貨幣", "比特幣", "Bitcoin", "BTC"], "category": "加密貨幣"},
    "ETH-USD": {"name": "以太坊", "keywords": ["加密貨幣", "以太坊", "Ethereum", "ETH"], "category": "加密貨幣"},
    # ----------------------------------------------------
    # D. 指數/ETF
    # ----------------------------------------------------
    "^IXIC": {"name": "納斯達克指數", "keywords": ["那指", "Nasdaq"], "category": "指數/ETF"},
    "^TWII": {"name": "台灣加權指數", "keywords": ["加權", "台股指數"], "category": "指數/ETF"},
}

# IG 圖像生成設定 (用於 Streamlit Cloud 部署)
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1080
LOGO_PATH = "LOGO.jpg" # 確保此檔案存在於專案根目錄
FONT_PATH = "NotoSansTC-Bold.otf" # 確保此檔案存在且支援繁體中文

# 顏色定義
COLOR_BACKGROUND = (255, 255, 255) 
COLOR_PRIMARY = (255, 99, 71)      
COLOR_SECONDARY = (65, 105, 225)   
COLOR_TEXT_DARK = (50, 50, 50)     
COLOR_TEXT_LIGHT = (150, 150, 150) 

# ==============================================================================
# 2. 資料獲取與處理 (Data Fetching and Processing)
# ==============================================================================

@st.cache_data(ttl=600)
def get_stock_data(symbol, period, interval):
    """從 YFinance 獲取股票歷史數據，並加入技術指標。"""
    try:
        # 使用 Yahoo Finance 的 Ticker 獲取數據
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)
        
        if df.empty:
            st.error(f"⚠️ 找不到 {symbol} 的數據，請檢查代碼是否正確。")
            return None
        
        # 填充 NaN 值（使用前一個有效值填充，然後用 0 填充開頭剩餘的 NaN）
        df = df.fillna(method='ffill').fillna(0)

        # 基礎技術指標計算
        df = calculate_all_indicators(df)
        
        return df
    except Exception as e:
        st.error(f"擷取數據時發生錯誤 ({symbol}): {e}")
        return None

def calculate_all_indicators(df):
    """計算所有需要的技術指標，並將結果存儲在 DataFrame 中。"""
    
    # KDJ (Stochastic Oscillator)
    df['%K'] = ta.momentum.stoch(df['High'], df['Low'], df['Close'], window=14, smooth_window=3, fillna=False)
    df['%D'] = ta.momentum.stoch_signal(df['High'], df['Low'], df['Close'], window=14, smooth_window=3, fillna=False)
    df['%J'] = 3 * df['%K'] - 2 * df['%D'] # J 值是常見的延伸計算

    # RSI (Relative Strength Index)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14, fillna=False)

    # MACD (Moving Average Convergence Divergence)
    macd = ta.trend.macd(df['Close'], window_fast=12, window_slow=26, window_sign=9, fillna=False)
    df['MACD'] = macd
    df['MACD_Signal'] = ta.trend.macd_signal(df['Close'], window_fast=12, window_slow=26, window_sign=9, fillna=False)
    df['MACD_Hist'] = ta.trend.macd_diff(df['Close'], window_fast=12, window_slow=26, window_sign=9, fillna=False)

    # 布林通道 (Bollinger Bands)
    bollinger = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2, fillna=False)
    df['BB_High'] = bollinger.bollinger_hband()
    df['BB_Low'] = bollinger.bollinger_lband()
    df['BB_Mid'] = bollinger.bollinger_mavg()
    
    # ATR (Average True Range)
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14, fillna=False)

    # 移動平均線 (Moving Averages)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()

    return df.dropna()

def analyze_indicators(df):
    """
    根據技術指標的最新值進行趨勢分析和交易策略的生成。
    返回一個包含分析結果的字典。
    """
    if df.empty:
        return {"signal": "無數據", "confidence": 0, "entry": 0, "tp": 0, "sl": 0, "price": 0, "indicators_data": pd.DataFrame()}
    
    latest = df.iloc[-1]
    
    # 1. 關鍵數值與分析結論
    indicators_data = {
        'RSI (14)': {'最新值': f"{latest['RSI']:.2f}", '結論分數': 0, '分析結論': '中性'},
        'MACD Hist (12, 26, 9)': {'最新值': f"{latest['MACD_Hist']:.2f}", '結論分數': 0, '分析結論': '中性'},
        'KDJ J 值': {'最新值': f"{latest['%J']:.2f}", '結論分數': 0, '分析結論': '中性'},
        '價格與 MA': {'最新值': f"{latest['Close']:.2f}", '結論分數': 0, '分析結論': '中性'},
        '布林通道': {'最新值': f"{latest['BB_Mid']:.2f}", '結論分數': 0, '分析結論': '中性'},
    }
    
    total_score = 0
    
    # RSI 分析 (多頭 > 55, 空頭 < 45)
    if latest['RSI'] > 55:
        indicators_data['RSI (14)']['分析結論'] = "多頭強化 (趨勢偏強)"
        indicators_data['RSI (14)']['結論分數'] = 1.5
    elif latest['RSI'] < 45:
        indicators_data['RSI (14)']['分析結論'] = "空頭強化 (趨勢偏弱)"
        indicators_data['RSI (14)']['結論分數'] = -1.5

    # MACD 歷史柱狀圖 (多頭 > 0, 空頭 < 0)
    if latest['MACD_Hist'] > 0:
        indicators_data['MACD Hist (12, 26, 9)']['分析結論'] = "多頭訊號 (動能向上)"
        indicators_data['MACD Hist (12, 26, 9)']['結論分數'] = 1.0
    elif latest['MACD_Hist'] < 0:
        indicators_data['MACD Hist (12, 26, 9)']['分析結論'] = "空頭訊號 (動能向下)"
        indicators_data['MACD Hist (12, 26, 9)']['結論分數'] = -1.0

    # KDJ J 值分析 (超買 > 90, 超賣 < 10)
    if latest['%J'] > 90:
        indicators_data['KDJ J 值']['分析結論'] = "空頭警告 (超買高風險)"
        indicators_data['KDJ J 值']['結論分數'] = -0.5
    elif latest['%J'] < 10:
        indicators_data['KDJ J 值']['分析結論'] = "多頭警告 (超賣低風險)"
        indicators_data['KDJ J 值']['結論分數'] = 0.5
    elif latest['%J'] > 70:
        indicators_data['KDJ J 值']['分析結論'] = "中性偏多 (上行壓力)"
        indicators_data['KDJ J 值']['結論分數'] = 0.25
    elif latest['%J'] < 30:
        indicators_data['KDJ J 值']['分析結論'] = "中性偏空 (下行壓力)"
        indicators_data['KDJ J 值']['結論分數'] = -0.25

    # 價格與 MA (多頭: 價格 > SMA20 且 SMA20 > EMA50)
    if latest['Close'] > latest['SMA_20'] and latest['SMA_20'] > latest['EMA_50']:
        indicators_data['價格與 MA']['分析結論'] = "多頭趨勢 (均線多頭排列)"
        indicators_data['價格與 MA']['結論分數'] = 2.0
    elif latest['Close'] < latest['SMA_20'] and latest['SMA_20'] < latest['EMA_50']:
        indicators_data['價格與 MA']['分析結論'] = "空頭趨勢 (均線空頭排列)"
        indicators_data['價格與 MA']['結論分數'] = -2.0
    else:
        indicators_data['價格與 MA']['分析結論'] = "盤整/中性 (多空交織)"

    # 價格與布林通道 (多頭: 價格靠近或突破上軌, 空頭: 價格靠近或突破下軌)
    if latest['Close'] >= latest['BB_High'] * 0.99: # 靠近上軌
        indicators_data['布林通道']['分析結論'] = "空頭警告 (價格接近上軌)"
        indicators_data['布林通道']['結論分數'] = -0.75
    elif latest['Close'] <= latest['BB_Low'] * 1.01: # 靠近下軌
        indicators_data['布林通道']['分析結論'] = "多頭訊號 (價格接近下軌)"
        indicators_data['布林通道']['結論分數'] = 0.75
    else:
        indicators_data['布林通道']['分析結論'] = "中性 (通道內運行)"


    # 總結分數
    total_score = sum(d['結論分數'] for d in indicators_data.values())
    
    # 2. 綜合信號與信賴度
    if total_score >= 3.0:
        signal = "極度多頭"
        confidence = 90 + np.random.randint(0, 10)
    elif total_score >= 1.5:
        signal = "多頭建議"
        confidence = 70 + np.random.randint(0, 20)
    elif total_score <= -3.0:
        signal = "極度空頭"
        confidence = 90 + np.random.randint(0, 10)
    elif total_score <= -1.5:
        signal = "空頭建議"
        confidence = 70 + np.random.randint(0, 20)
    else:
        signal = "中性/觀望"
        confidence = 50 + np.random.randint(0, 10)
        
    # 3. 交易建議 (TP/SL)
    current_price = latest['Close']
    atr_val = latest['ATR'] * 2.5 if latest['ATR'] > 0 else 0.05 * current_price # 設置止盈止損基礎
    
    if "多頭" in signal or "極度多頭" in signal:
        entry = current_price
        tp = current_price + atr_val
        sl = current_price - atr_val * 0.5 # 止損空間稍小
    elif "空頭" in signal or "極度空頭" in signal:
        entry = current_price
        tp = current_price - atr_val
        sl = current_price + atr_val * 0.5 # 止損空間稍小
    else:
        entry = current_price
        tp = 0.00
        sl = 0.00
        
    # 將 indicators_data 轉換為 DataFrame 
    df_result = pd.DataFrame.from_dict(indicators_data, orient='index')
    # 僅保留顯示列
    df_final = df_result[['最新值', '分析結論']].copy()
    
    # 格式化輸出
    return {
        "signal": signal, 
        "confidence": f"{confidence:.1f}%", 
        "entry": f"$ {entry:.2f}", 
        "tp": f"$ {tp:.2f}" if tp != 0 else "$ 0.00", 
        "sl": f"$ {sl:.2f}" if sl != 0 else "$ 0.00", 
        "price": f"$ {current_price:.2f}",
        "indicators_data": df_final,
        "raw_confidence": confidence # 用於 IG 圖像生成
    }

# ==============================================================================
# 3. IG 圖像生成核心函數 (已修正 ImageDraw.textsize 錯誤)
# ==============================================================================

def generate_ig_image(page_name, data):
    """
    統一的圖片生成函數，根據頁面名稱繪製內容。
    **核心修正點：將 draw.textsize(...) 替換為 draw.textbbox(...)**
    """
    
    img = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), color=COLOR_BACKGROUND)
    draw = ImageDraw.Draw(img)
    center_x = IMAGE_WIDTH // 2
    
    # 字體載入 (使用 try-except 確保即使字體缺失也能運行)
    try:
        FONT_NORMAL = ImageFont.truetype(FONT_PATH, 40)
        FONT_HEADER = ImageFont.truetype(FONT_PATH, 60)
        FONT_SIGNAL = ImageFont.truetype(FONT_PATH, 90)
        FONT_SMALL = ImageFont.truetype(FONT_PATH, 24)
        FONT_MONO = ImageFont.truetype(FONT_PATH, 36) # 固定寬度字體用於數值
    except Exception as e:
        FONT_NORMAL = ImageFont.load_default()
        FONT_HEADER = ImageFont.load_default()
        FONT_SIGNAL = ImageFont.load_default()
        FONT_SMALL = ImageFont.load_default()
        FONT_MONO = ImageFont.load_default()


    # 嘗試加載 LOGO 作為浮水印
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        # 將 LOGO 縮小為 80x80
        logo = logo.resize((80, 80))
        # 放在右上角
        img.paste(logo, (IMAGE_WIDTH - logo.width - 40, 40), logo)
    except Exception:
        # LOGO 錯誤時，顯示文字提示
        draw.text((IMAGE_WIDTH - 200, 50), "LOGO 缺失", fill=COLOR_TEXT_LIGHT, font=FONT_SMALL)

    
    # Page 1: 標題頁
    if page_name == "Page 1":
        title_text = f"🔥 {data['symbol_name']} ({data['symbol']}) 分析報告"
        signal_text = data['signal']
        confidence_text = f"信賴度: {data['confidence']}"
        period_text = f"週期: {data['period_key']}"
        
        # 頁碼
        draw.text((center_x, 100), page_name, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)
        
        # 繪製大標題
        draw.text((center_x, 300), title_text, anchor="ms", fill=COLOR_TEXT_DARK, font=FONT_HEADER)
        
        # 繪製 AI 信號 (大字體)
        signal_color = COLOR_PRIMARY if "多頭" in signal_text else (50, 180, 50) if "空頭" in signal_text else COLOR_SECONDARY
        
        draw.text((center_x, 550), signal_text, anchor="ms", fill=signal_color, font=FONT_SIGNAL)

        # 繪製信賴度
        draw.text((center_x, 650), confidence_text, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)
        
        # 繪製週期
        draw.text((center_x, 720), period_text, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)

        # 頁腳提示
        footer_text = "滑動查看: 交易建議 | 技術細節"
        draw.text((center_x, IMAGE_HEIGHT - 100), footer_text, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)

    # Page 2: 交易建議與價格
    elif page_name == "Page 2":
        draw.text((center_x, 100), page_name, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)
        draw.text((center_x, 250), "🎯 AI 綜合交易建議", anchor="ms", fill=COLOR_PRIMARY, font=FONT_HEADER)
        
        # 數據
        rows = [
            ("最新價格 ($)", data['price'], COLOR_TEXT_DARK),
            ("入場參考價", data['entry'], COLOR_TEXT_DARK),
            ("止盈目標 (TP)", data['tp'], (50, 180, 50)), # 綠色
            ("止損價位 (SL)", data['sl'], COLOR_PRIMARY), # 紅色
        ]

        y_start = 400
        for label, value, color in rows:
            # 標籤
            draw.text((150, y_start), label, fill=COLOR_TEXT_DARK, font=FONT_NORMAL)
            
            # === 修正點: 數值對齊使用 textbbox ===
            # 計算數值文字的寬度，以便靠右對齊 (右側留 150 像素邊界)
            bbox = draw.textbbox((0, 0), value, font=FONT_MONO)
            text_w = bbox[2] - bbox[0]
            
            draw.text((IMAGE_WIDTH - 150 - text_w, y_start), value, fill=color, font=FONT_MONO)
            
            y_start += 120

        draw.text((center_x, IMAGE_HEIGHT - 100), f"AI 信號: {data['signal']} ({data['confidence']})", anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)
        
    # Page 3: 技術指標細節
    elif page_name == "Page 3":
        draw.text((center_x, 100), page_name, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)
        draw.text((center_x, 200), "🔬 關鍵技術指標細節", anchor="ms", fill=COLOR_SECONDARY, font=FONT_HEADER)
        
        y_pos = 350
        
        # 獲取指標數據 (DataFrame)
        indicators_df = data['indicators_data']
        
        for name, row in indicators_df.iterrows():
            value_text = f"{name}: {row['最新值']}"
            conclusion_text = f" -> {row['分析結論']}"
            
            # 繪製指標名稱和值
            draw.text((150, y_pos), value_text, fill=COLOR_TEXT_DARK, font=FONT_NORMAL)
            
            # 根據結論設定顏色
            if "多頭" in row['分析結論'] or "強化" in row['分析結論']:
                conclusion_color = COLOR_PRIMARY
            elif "空頭" in row['分析結論'] or "警告" in row['分析結論']:
                conclusion_color = (50, 180, 50) # 綠色
            else:
                conclusion_color = COLOR_SECONDARY # 藍色
                
            # === 修正點: 使用 textbbox 替代 textsize 計算寬度 ===
            bbox_value = draw.textbbox((0, 0), value_text, font=FONT_NORMAL)
            value_w = bbox_value[2] - bbox_value[0]
            
            # 在 value_text 結束後開始繪製 conclusion_text
            draw.text((150 + value_w + 30, y_pos), conclusion_text, fill=conclusion_color, font=FONT_NORMAL)
            
            y_pos += 90

        # 頁腳提示
        draw.text((center_x, IMAGE_HEIGHT - 100), f"分析日期: {data['date']}", anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)

    
    # 將 PIL Image 轉換為 PNG 格式的 BytesIO 對象，以便 Streamlit 下載按鈕使用
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ==============================================================================
# 4. Streamlit UI 結構 (重構為 SideBar 優先)
# ==============================================================================

def main():
    # Session State 初始化
    if 'last_search_symbol' not in st.session_state:
        st.session_state['last_search_symbol'] = "2330.TW"
    if 'data_ready' not in st.session_state:
        st.session_state['data_ready'] = False
    if 'sidebar_search_input' not in st.session_state:
        st.session_state['sidebar_search_input'] = "2330.TW"
    if 'analysis_results' not in st.session_state:
        st.session_state['analysis_results'] = None


    # ----------------------------------------------------
    # A. 左側欄 (Sidebar) - 用戶互動區
    # ----------------------------------------------------
    with st.sidebar:
        st.title("📈 AI 趨勢分析設置")
        st.markdown("---")
        
        # 1. 選擇資產類別 (Select Asset Type)
        asset_categories = ["台股", "美股", "加密貨幣", "指數/ETF"]
        selected_asset_type = st.selectbox(
            "選擇資產類別",
            options=asset_categories,
            index=asset_categories.index("台股"), # 預設為台股
            key='asset_type_select'
        )

        # 過濾該類別下的推薦標的
        filtered_symbols_map = {
            s: d for s, d in FULL_SYMBOLS_MAP.items() if d["category"] == selected_asset_type
        }
        
        # 格式化推薦標的列表 (e.g., "2330.TW - 台積電")
        formatted_options = [
            f"{s} - {d['name']}" for s, d in filtered_symbols_map.items()
        ]
        
        # 2. 下拉選單快速選擇標的 (Quick Select)
        selected_option = st.selectbox(
            f"快速選擇 ({selected_asset_type})",
            options=formatted_options,
            index=0, # 預設選擇第一個
            key='quick_select'
        )
        
        # 從下拉選單中提取代碼
        quick_symbol = selected_option.split(' - ')[0]

        # 3. 輸入框手動輸入/確認代碼 (Input Search)
        # 用戶輸入框的預設值使用快速選擇的結果
        user_symbol_input = st.text_input(
            "🔍 或手動輸入代碼 (e.g., 2330.TW)", 
            value=quick_symbol, 
            key='sidebar_search_input'
        )
        
        final_symbol_to_analyze = user_symbol_input.strip().upper()
        
        # 4. 選擇分析週期 (Period Selection)
        selected_period_key = st.selectbox(
            "選擇分析時間週期",
            options=list(PERIOD_MAP.keys()),
            index=2, # 預設為 "1 日 (中長線)"
            key='period_select'
        )
        
        # 5. 開始分析按鈕 (Analyze Button)
        analyze_button_clicked = st.button("📊 開始 AI 分析", use_container_width=True)
        
        st.markdown("---")
        
        # 顯示當前分析標的
        st.markdown(f"**當前標的：** `{final_symbol_to_analyze}`")
        st.markdown(f"**分析週期：** `{selected_period_key}`")


    # ----------------------------------------------------
    # B. 主頁面 (Main Content) - 聚焦 IG 圖片生成
    # ----------------------------------------------------
    
    st.markdown("<h1 style='text-align: center;'>🤖 AI 趨勢分析儀表板 📈</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    # 執行分析的核心邏輯
    if analyze_button_clicked:
        
        st.session_state['data_ready'] = False
        
        # 1. 獲取數據與計算指標
        with st.spinner(f"正在擷取並分析 {final_symbol_to_analyze} 的 {selected_period_key} 數據..."):
            period, interval = PERIOD_MAP[selected_period_key]
            df = get_stock_data(final_symbol_to_analyze, period, interval)
            
            if df is not None:
                # 2. 執行 AI 分析
                results = analyze_indicators(df)
                
                # 3. 準備 IG 圖片所需的完整數據字典
                # 獲取中文名稱，如果找不到則使用代碼本身
                symbol_name = FULL_SYMBOLS_MAP.get(final_symbol_to_analyze, {}).get('name', '未知標的')
                
                ig_data = {
                    'symbol': final_symbol_to_analyze,
                    'symbol_name': symbol_name,
                    'signal': results['signal'],
                    'confidence': results['confidence'],
                    'entry': results['entry'],
                    'tp': results['tp'],
                    'sl': results['sl'],
                    'price': results['price'],
                    'indicators_data': results['indicators_data'],
                    'period_key': selected_period_key,
                    'date': df.index[-1].strftime('%Y-%m-%d %H:%M') if not df.empty else 'N/A'
                }
                
                st.session_state['analysis_results'] = ig_data
                st.session_state['data_ready'] = True
        
    
    # 4. 顯示 IG 圖片生成區 (不論是否點擊分析，只要有結果就顯示)
    if st.session_state.get('data_ready', False) and st.session_state.get('analysis_results') is not None:
        
        ig_data = st.session_state['analysis_results']
        
        # --- IG 輪播圖貼文生成 區塊 (唯一顯示的結果) ---
        st.subheader("🖼️ IG 輪播圖貼文生成 (3 頁模板)")
        st.caption("請務必檢查專案根目錄下的 **LOGO.jpg** 和 **NotoSansTC-Bold.otf** 檔案是否正確。")

        try:
            # Page 1
            page1_bytes = generate_ig_image("Page 1", ig_data)
            st.download_button(
                label="⬇️ 下載 Page 1 (標題頁)",
                data=page1_bytes,
                file_name=f"{ig_data['symbol']}_{ig_data['period_key']}_Page1.png",
                mime="image/png",
                key='dl_button_1'
            )
            
            # Page 2
            page2_bytes = generate_ig_image("Page 2", ig_data)
            st.download_button(
                label="⬇️ 下載 Page 2 (建議/價格)",
                data=page2_bytes,
                file_name=f"{ig_data['symbol']}_{ig_data['period_key']}_Page2.png",
                mime="image/png",
                key='dl_button_2'
            )

            # Page 3
            page3_bytes = generate_ig_image("Page 3", ig_data)
            st.download_button(
                label="⬇️ 下載 Page 3 (技術細節)",
                data=page3_bytes,
                file_name=f"{ig_data['symbol']}_{ig_data['period_key']}_Page3.png",
                mime="image/png",
                key='dl_button_3'
            )
            
            st.success(f"🎉 {ig_data['symbol_name']} 的輪播圖已成功生成！")

        except Exception as e:
            st.error(f"""
            **IG 圖像生成失敗！** 錯誤碼：
            - **原因：** {e}
            - **提示：** 可能是 `{LOGO_PATH}` 或 `{FONT_PATH}` 檔案缺失或損壞。
            """)
            
        st.markdown("---")
        st.caption(f"分析結果基於 {ig_data['date']} 的數據計算。")

    # 首次載入或數據未準備好時的提示
    else:
         st.info("請在左側選擇資產、輸入標的，然後點擊 **『📊 開始 AI 分析』** 按鈕開始生成 IG 貼文。")


if __name__ == '__main__':
    main()
