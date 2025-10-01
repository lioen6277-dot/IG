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
import io # 新增：用於圖像處理
from PIL import Image, ImageDraw, ImageFont # 新增：用於圖像生成

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

# 🚀 您的【所有資產清單】
FULL_SYMBOLS_MAP = {
    # A. 美股核心 (US Stocks)
    "TSLA": {"name": "特斯拉", "keywords": ["特斯拉", "電動車", "TSLA", "Tesla"]},
    "NVDA": {"name": "輝達", "keywords": ["輝達", "英偉達", "AI", "NVDA", "Nvidia"]},
    "AAPL": {"name": "蘋果", "keywords": ["蘋果", "Apple", "AAPL"]},
    "GOOGL": {"name": "谷歌/Alphabet", "keywords": ["谷歌", "Alphabet", "GOOGL", "GOOG"]},
    "MSFT": {"name": "微軟", "keywords": ["微軟", "Microsoft", "MSFT"]},
    "AMZN": {"name": "亞馬遜", "keywords": ["亞馬遜", "Amazon", "AMZN"]},
    "META": {"name": "Meta/臉書", "keywords": ["臉書", "Meta", "FB", "META"]},
    "NFLX": {"name": "網飛", "keywords": ["網飛", "Netflix", "NFLX"]},
    "ADBE": {"name": "Adobe", "keywords": ["Adobe", "ADBE"]},
    "CRM": {"name": "Salesforce", "keywords": ["Salesforce", "CRM"]},
    "ORCL": {"name": "甲骨文", "keywords": ["甲骨文", "Oracle", "ORCL"]},
    "COST": {"name": "好市多", "keywords": ["好市多", "Costco", "COST"]},
    "JPM": {"name": "摩根大通", "keywords": ["摩根大通", "JPMorgan", "JPM"]},
    "V": {"name": "Visa", "keywords": ["Visa", "V"]},
    "WMT": {"name": "沃爾瑪", "keywords": ["沃爾瑪", "Walmart", "WMT"]},
    "PG": {"name": "寶潔", "keywords": ["寶潔", "P&G", "PG"]},
    "KO": {"name": "可口可樂", "keywords": ["可口可樂", "CocaCola", "KO"]},
    "PEP": {"name": "百事", "keywords": ["百事", "Pepsi", "PEP"]},
    "MCD": {"name": "麥當勞", "keywords": ["麥當勞", "McDonalds", "MCD"]},
    "QCOM": {"name": "高通", "keywords": ["高通", "Qualcomm", "QCOM"]},
    "INTC": {"name": "英特爾", "keywords": ["英特爾", "Intel", "INTC"]},
    "AMD": {"name": "超微", "keywords": ["超微", "AMD"]},
    "LLY": {"name": "禮來", "keywords": ["禮來", "EliLilly", "LLY"]},
    "UNH": {"name": "聯合健康", "keywords": ["聯合健康", "UNH"]},
    "HD": {"name": "家得寶", "keywords": ["家得寶", "HomeDepot", "HD"]},
    "CAT": {"name": "開拓重工", "keywords": ["開拓重工", "Caterpillar", "CAT"]},
    # B. 美股指數/ETF 
    "^GSPC": {"name": "S&P 500 指數", "keywords": ["標普", "S&P500", "^GSPC", "SPX"]},
    "^IXIC": {"name": "NASDAQ 綜合指數", "keywords": ["納斯達克", "NASDAQ", "^IXIC"]},
    "^DJI": {"name": "道瓊工業指數", "keywords": ["道瓊", "DowJones", "^DJI"]},
    "SPY": {"name": "SPDR 標普500 ETF", "keywords": ["SPY", "標普ETF"]},
    "QQQ": {"name": "Invesco QQQ Trust", "keywords": ["QQQ", "納斯達克ETF"]},
    "VOO": {"name": "Vanguard 標普500 ETF", "keywords": ["VOO", "Vanguard"]},
    # C. 台灣市場 (TW Stocks/ETFs/Indices)
    "2330.TW": {"name": "台積電", "keywords": ["台積電", "2330", "TSMC"]},
    "2317.TW": {"name": "鴻海", "keywords": ["鴻海", "2317", "Foxconn"]},
    "2454.TW": {"name": "聯發科", "keywords": ["聯發科", "2454", "MediaTek"]},
    "2308.TW": {"name": "台達電", "keywords": ["台達電", "2308", "Delta"]},
    "3017.TW": {"name": "奇鋐", "keywords": ["奇鋐", "3017", "散熱"]},
    "3231.TW": {"name": "緯創", "keywords": ["緯創", "3231"]},
    "2382.TW": {"name": "廣達", "keywords": ["廣達", "2382"]},
    "2379.TW": {"name": "瑞昱", "keywords": ["瑞昱", "2379"]},
    "2881.TW": {"name": "富邦金", "keywords": ["富邦金", "2881"]},
    "2882.TW": {"name": "國泰金", "keywords": ["國泰金", "2882"]},
    "2603.TW": {"name": "長榮", "keywords": ["長榮", "2603", "航運"]},
    "2609.TW": {"name": "陽明", "keywords": ["陽明", "2609", "航運"]},
    "2615.TW": {"name": "萬海", "keywords": ["萬海", "2615", "航運"]},
    "2891.TW": {"name": "中信金", "keywords": ["中信金", "2891"]},
    "1101.TW": {"name": "台泥", "keywords": ["台泥", "1101"]},
    "1301.TW": {"name": "台塑", "keywords": ["台塑", "1301"]},
    "2357.TW": {"name": "華碩", "keywords": ["華碩", "2357"]},
    "0050.TW": {"name": "元大台灣50", "keywords": ["台灣50", "0050", "台灣五十"]},
    "0056.TW": {"name": "元大高股息", "keywords": ["高股息", "0056"]},
    "00878.TW": {"name": "國泰永續高股息", "keywords": ["00878", "國泰永續"]},
    "^TWII": {"name": "台股指數", "keywords": ["台股指數", "加權指數", "^TWII"]},
    # D. 加密貨幣 (Crypto)
    "BTC-USD": {"name": "比特幣", "keywords": ["比特幣", "BTC", "bitcoin", "BTC-USDT"]},
    "ETH-USD": {"name": "以太坊", "keywords": ["以太坊", "ETH", "ethereum", "ETH-USDT"]},
    "SOL-USD": {"name": "Solana", "keywords": ["Solana", "SOL", "SOL-USDT"]},
    "BNB-USD": {"name": "幣安幣", "keywords": ["幣安幣", "BNB", "BNB-USDT"]},
    "DOGE-USD": {"name": "狗狗幣", "keywords": ["狗狗幣", "DOGE", "DOGE-USDT"]},
    "XRP-USD": {"name": "瑞波幣", "keywords": ["瑞波幣", "XRP", "XRP-USDT"]},
    "ADA-USD": {"name": "Cardano", "keywords": ["Cardano", "ADA", "ADA-USDT"]},
    "AVAX-USD": {"name": "Avalanche", "keywords": ["Avalanche", "AVAX", "AVAX-USDT"]},
    "DOT-USD": {"name": "Polkadot", "keywords": ["Polkadot", "DOT", "DOT-USDT"]},
    "LINK-USD": {"name": "Chainlink", "keywords": ["Chainlink", "LINK", "LINK-USDT"]},
    "PEPE-USD": {"name": "佩佩幣", "keywords": ["佩佩幣", "PEPE", "PEPE-USDT"]},
}

# 建立第二層選擇器映射
CATEGORY_MAP = {
    "美股 (US) - 個股/ETF/指數": [c for c in FULL_SYMBOLS_MAP.keys() if not (c.endswith(".TW") or c.endswith("-USD") or c.startswith("^TWII"))],
    "台股 (TW) - 個股/ETF/指數": [c for c in FULL_SYMBOLS_MAP.keys() if c.endswith(".TW") or c.startswith("^TWII")],
    "加密貨幣 (Crypto)": [c for c in FULL_SYMBOLS_MAP.keys() if c.endswith("-USD")],
}

CATEGORY_HOT_OPTIONS = {}
for category, codes in CATEGORY_MAP.items():
    options = {}
    sorted_codes = sorted(codes) 
    for code in sorted_codes:
        info = FULL_SYMBOLS_MAP.get(code)
        if info:
            options[f"{code} - {info['name']}"] = code
    CATEGORY_HOT_OPTIONS[category] = options
    
    
# ==============================================================================
# 1.1 IG 圖像設計參數 (新增區塊)
# ==============================================================================
# ⚠️ 請確保 LOGO.jpg 和 NotoSansTC-Bold.otf 檔案已上傳至 GitHub 根目錄
LOGO_PATH = "LOGO.jpg" 
FONT_PATH = "NotoSansTC-Bold.otf"

# 顏色定義 (深色科技風)
BACKGROUND_COLOR = '#0B172A'  # 深藍色背景
PRIMARY_COLOR = '#FFFFFF'     # 白色文字
TREND_BLUE = '#00A3FF'        # 趨勢藍 (買入/多頭信號/CTA色)
ALERT_ORANGE = '#FF4D00'      # 警示橙 (賣出/止損信號)
COLOR_MAP_HEX = { # 用於 Page 2 顏色轉換：從 Streamlit 顏色名稱到 HEX
    'red': TREND_BLUE,      # 多頭強化 (紅色在 Streamlit 常用於漲幅)
    'green': ALERT_ORANGE,  # 空頭警示 (綠色在 Streamlit 常用於跌幅)
    'orange': '#FFCC00',    # 中性/警告
    'blue': '#A0C4FF',      # 中性
    'grey': PRIMARY_COLOR
}


@st.cache_resource
def get_font(size, font_path=FONT_PATH):
    """嘗試載入指定的字體，並使用 Streamlit 資源快取"""
    try:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
        else:
            return ImageFont.load_default(size)
    except Exception as e:
        return ImageFont.load_default(size)

# 載入所有需要的字體大小
FONT_SUPERTITLE = get_font(120) # 專門用於 Page 1 核心結論
FONT_TITLE = get_font(80) 
FONT_DATA = get_font(40)
FONT_LABEL = get_font(32)
FONT_SMALL = get_font(24)

# ==============================================================================
# 2. 輔助函式定義
# ==============================================================================

# ... (get_symbol_from_query, get_stock_data, get_company_info, get_currency_symbol, calculate_technical_indicators 保持不變) ...

def get_symbol_from_query(query: str) -> str:
    """ 🎯 進化後的代碼解析函數：同時檢查 FULL_SYMBOLS_MAP """
    query = query.strip()
    query_upper = query.upper()
    for code, data in FULL_SYMBOLS_MAP.items():
        if query_upper == code: return code
        if any(query_upper == kw.upper() for kw in data["keywords"]): return code 
    for code, data in FULL_SYMBOLS_MAP.items():
        if query == data["name"]: return code
    if re.fullmatch(r'\d{4,6}', query) and not any(ext in query_upper for ext in ['.TW', '.HK', '.SS', '-USD']):
        tw_code = f"{query}.TW"
        if tw_code in FULL_SYMBOLS_MAP: return tw_code
        return tw_code
    return query

@st.cache_data(ttl=3600, show_spinner="正在從 Yahoo Finance 獲取數據...")
def get_stock_data(symbol, period, interval):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        
        if df.empty: return pd.DataFrame()
        
        # 統一列名格式
        df.columns = [col.capitalize() for col in df.columns] 
        df.index.name = 'Date'
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        
        # 確保數據時間戳是唯一的 (防止高頻數據重複)
        df = df[~df.index.duplicated(keep='first')]
        # 刪除最後一行（通常是未完成的當前 K 線）
        df = df.iloc[:-1] 
        
        if df.empty: return pd.DataFrame() # 再次檢查是否為空
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_company_info(symbol):
    info = FULL_SYMBOLS_MAP.get(symbol, {})
    if info:
        if symbol.endswith(".TW") or symbol.startswith("^TWII"): category, currency = "台股 (TW)", "TWD"
        elif symbol.endswith("-USD"): category, currency = "加密貨幣 (Crypto)", "USD"
        else: category, currency = "美股 (US)", "USD"
        return {"name": info['name'], "category": category, "currency": currency}
    
    try:
        ticker = yf.Ticker(symbol)
        yf_info = ticker.info
        name = yf_info.get('longName') or yf_info.get('shortName') or symbol
        currency = yf_info.get('currency') or "USD"
        category = "未分類"
        if symbol.endswith(".TW"): category = "台股 (TW)"
        elif symbol.endswith("-USD"): category = "加密貨貨幣 (Crypto)"
        elif symbol.startswith("^"): category = "指數"
        elif currency == "USD": category = "美股 (US)"
        return {"name": name, "category": category, "currency": currency}
    except:
        return {"name": symbol, "category": "未分類", "currency": "USD"}
    
@st.cache_data
def get_currency_symbol(symbol):
    currency_code = get_company_info(symbol).get('currency', 'USD')
    if currency_code == 'TWD': return 'NT$'
    elif currency_code == 'USD': return '$'
    elif currency_code == 'HKD': return 'HK$'
    else: return currency_code + ' '

def calculate_technical_indicators(df):
    
    # 進階移動平均線 (MA)
    df['EMA_10'] = ta.trend.ema_indicator(df['Close'], window=10) # 短線趨勢
    df['EMA_50'] = ta.trend.ema_indicator(df['Close'], window=50) # 長線趨勢
    df['EMA_200'] = ta.trend.ema_indicator(df['Close'], window=200) # 濾鏡
    
    # MACD (進階設定: 快線 8, 慢線 17, 信號線 9)
    macd_instance = ta.trend.MACD(df['Close'], window_fast=8, window_slow=17, window_sign=9)
    df['MACD_Line'] = macd_instance.macd()
    df['MACD_Signal'] = macd_instance.macd_signal()
    df['MACD'] = macd_instance.macd_diff() # MACD 柱狀圖
    
    # RSI (進階設定: 週期 9)
    df['RSI'] = ta.momentum.rsi(df['Close'], window=9)
    
    # 經典布林通道 (20, 2)
    df['BB_High'] = ta.volatility.bollinger_hband(df['Close'], window=20, window_dev=2)
    df['BB_Low'] = ta.volatility.bollinger_lband(df['Close'], window=20, window_dev=2)
    
    # ATR (進階設定: 週期 9) - 風險控制的基石
    df['ATR'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=9)
    
    # ADX (進階設定: 週期 9) - 趨勢強度的濾鏡
    df['ADX'] = ta.trend.adx(df['High'], df['Low'], df['Close'], window=9)
    
    # 增加 SMA 20 (用於回測基準)
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20) 
    
    return df

def get_technical_data_df(df):
    """獲取最新的技術指標數據和AI結論，並根據您的進階原則進行判讀。"""
    
    if df.empty or len(df) < 200: return pd.DataFrame()

    df_clean = df.dropna().copy()
    if df_clean.empty: return pd.DataFrame()

    last_row = df_clean.iloc[-1]
    prev_row = df_clean.iloc[-2] if len(df_clean) >= 2 else last_row 

    indicators = {}
    
    indicators['價格 vs. EMA 10/50/200'] = last_row['Close']
    indicators['RSI (9) 動能'] = last_row['RSI']
    indicators['MACD (8/17/9) 柱狀圖'] = last_row['MACD']
    indicators['ADX (9) 趨勢強度'] = last_row['ADX']
    indicators['ATR (9) 波動性'] = last_row['ATR']
    indicators['布林通道 (BB: 20/2)'] = last_row['Close']
    
    data = []
    
    for name, value in indicators.items():
        conclusion, color = "", "grey"
        
        if 'EMA 10/50/200' in name:
            ema_10 = last_row['EMA_10']
            ema_50 = last_row['EMA_50']
            ema_200 = last_row['EMA_200']

            # 採用進階的多頭排列判斷 (10 > 50 > 200)
            if ema_10 > ema_50 and ema_50 > ema_200:
                conclusion, color = f"**強多頭：MA 多頭排列** (10>50>200)", "red"
            elif ema_10 < ema_50 and ema_50 < ema_200:
                conclusion, color = f"**強空頭：MA 空頭排列** (10<50<200)", "green"
            elif last_row['Close'] > ema_50 and last_row['Close'] > ema_200:
                conclusion, color = f"中長線偏多：價格站上 EMA 50/200", "orange"
            else:
                conclusion, color = "中性：MA 糾結或趨勢發展中", "blue"
        
        elif 'RSI' in name:
            # 進階判斷: RSI > 50 多頭, < 50 空頭。70/30 為超買超賣
            if value > 70:
                conclusion, color = "警告：超買區域 (70)，潛在回調", "green" 
            elif value < 30:
                conclusion, color = "強化：超賣區域 (30)，潛在反彈", "red"
            elif value > 50:
                conclusion, color = "多頭：RSI > 50，位於強勢區間", "red"
            else:
                conclusion, color = "空頭：RSI < 50，位於弱勢區間", "green"


        elif 'MACD' in name:
            # 判斷 MACD 柱狀圖是否放大
            if value > 0 and value > prev_row['MACD']:
                conclusion, color = "強化：多頭動能增強 (紅柱放大)", "red"
            elif value < 0 and value < prev_row['MACD']:
                conclusion, color = "削弱：空頭動能增強 (綠柱放大)", "green"
            else:
                conclusion, color = "中性：動能盤整 (柱狀收縮)", "orange"
        
        elif 'ADX' in name:
              # ADX > 25 確認強趨勢
            if value >= 40:
                conclusion, color = "強趨勢：極強勢趨勢 (多或空)", "red"
            elif value >= 25:
                conclusion, color = "強趨勢：確認強勢趨勢 (ADX > 25)", "orange"
            else:
                conclusion, color = "盤整：弱勢或橫盤整理 (ADX < 25)", "blue"

        elif 'ATR' in name:
            avg_atr = df_clean['ATR'].iloc[-30:].mean() if len(df_clean) >= 30 else df_clean['ATR'].mean()
            if value > avg_atr * 1.5:
                conclusion, color = "警告：極高波動性 (1.5x 平均)", "green"
            elif value < avg_atr * 0.7:
                conclusion, color = "中性：低波動性 (醞釀突破)", "orange"
            else:
                conclusion, color = "中性：正常波動性", "blue"

        elif '布林通道' in name:
            high = last_row['BB_High']
            low = last_row['BB_Low']
            range_pct = (high - low) / last_row['Close'] * 100
            
            if value > high:
                conclusion, color = f"警告：價格位於上軌外側 (>{high:,.2f})", "red"
            elif value < low:
                conclusion, color = f"強化：價格位於下軌外側 (<{low:,.2f})", "green"
            else:
                conclusion, color = f"中性：在上下軌間 ({range_pct:.2f}% 寬度)", "blue"
        
        data.append([name, value, conclusion, color])

    technical_df = pd.DataFrame(data, columns=['指標名稱', '最新值', '分析結論', '顏色'])
    technical_df = technical_df.set_index('指標名稱')
    return technical_df

def run_backtest(df, initial_capital=100000, commission_rate=0.001):
    """
    執行基於 SMA 20 / EMA 50 交叉的簡單回測。
    策略: 黃金交叉買入 (做多)，死亡交叉清倉 (賣出)。
    """
    
    if df.empty or len(df) < 51:
        return {"total_return": 0, "win_rate": 0, "max_drawdown": 0, "total_trades": 0, "message": "數據不足 (少於 51 週期) 或計算錯誤。"}

    data = df.copy()
    
    # 黃金/死亡交叉信號
    data['Prev_MA_State'] = (data['SMA_20'].shift(1) > data['EMA_50'].shift(1))
    data['Current_MA_State'] = (data['SMA_20'] > data['EMA_50'])
    data['Signal'] = np.where(
        (data['Current_MA_State'] == True) & (data['Prev_MA_State'] == False), 
        1, # Buy
        0 
    )
    data['Signal'] = np.where(
        (data['Current_MA_State'] == False) & (data['Prev_MA_State'] == True), 
        -1, 
        data['Signal'] # Sell
    )

    data = data.dropna()
    if data.empty: return {"total_return": 0, "win_rate": 0, "max_drawdown": 0, "total_trades": 0, "message": "指標計算後數據不足。"}

    # --- 模擬交易邏輯 ---
    capital = [initial_capital]
    position = 0
    buy_price = 0
    trades = []

    for i in range(1, len(data)):
        current_close = data['Close'].iloc[i]

        # 1. Buy Signal
        if data['Signal'].iloc[i] == 1 and position == 0:
            position = 1
            buy_price = current_close
            initial_capital -= initial_capital * commission_rate 

        # 2. Sell Signal (清倉)
        elif data['Signal'].iloc[i] == -1 and position == 1:
            sell_price = current_close
            profit = (sell_price - buy_price) / buy_price
            trades.append({
                'entry_date': data.index[i],
                'exit_date': data.index[i],
                'profit_pct': profit,
                'is_win': profit > 0
            })
            initial_capital *= (1 + profit)
            initial_capital -= initial_capital * commission_rate
            position = 0

        current_value = initial_capital
        if position == 1:
            current_value = initial_capital * (current_close / buy_price)
        capital.append(current_value) 

    # 3. Handle open position (計算未平倉損益)
    if position == 1:
        sell_price = data['Close'].iloc[-1]
        profit = (sell_price - buy_price) / buy_price
        trades.append({
            'entry_date': data.index[-1],
            'exit_date': data.index[-1],
            'profit_pct': profit,
            'is_win': profit > 0
        })
        # Note: 這裡不改變 initial_capital，只為計算報酬率
    
    if capital:
        # 使用最新的 capital 計算報酬率
        final_capital = initial_capital * (1 + profit) if position == 1 else initial_capital
        total_return = ((final_capital - 100000) / 100000) * 100
    else:
        total_return = 0

    # --- 計算回測結果 ---
    total_trades = len([t for t in trades if t['is_win'] is not None])
    win_rate = (sum(1 for t in trades if t.get('is_win') == True) / total_trades) * 100 if total_trades > 0 else 0

    capital_series = pd.Series(capital)
    max_value = capital_series.expanding(min_periods=1).max()
    drawdown = (capital_series - max_value) / max_value
    max_drawdown = abs(drawdown.min()) * 100

    return {
        "total_return": round(total_return, 2),
        "win_rate": round(win_rate, 2),
        "max_drawdown": round(max_drawdown, 2),
        "total_trades": total_trades,
        "message": f"回測區間 {data.index[0].strftime('%Y-%m-%d')} 到 {data.index[-1].strftime('%Y-%m-%d')}。",
        "capital_curve": capital_series
    }

def calculate_fundamental_rating(symbol):
    """ 融合了 '基本面的判斷標準'，特別是 ROE > 15%、PE 估值、以及現金流/負債健康度。 """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        # 排除指數和加密貨幣
        if symbol.startswith('^') or symbol.endswith('-USD'):
            return {
                "Combined_Rating": 0.0,
                "Message": "不適用：指數或加密貨幣無標準基本面數據。",
                "Details": None
            }

        roe = info.get('returnOnEquity', 0)
        trailingPE = info.get('trailingPE', 99)
        freeCashFlow = info.get('freeCashflow', 0)
        totalCash = info.get('totalCash', 0)
        totalDebt = info.get('totalDebt', 0)
        
        # 1. 成長與效率評分 (ROE) (總分 3)
        roe_score = 0
        if roe > 0.20: # 20%
            roe_score = 3
        elif roe >= 0.15: # 15% (您的主要標準)
            roe_score = 2
        elif roe >= 0.10: # 10%
            roe_score = 1
            
        # 2. 估值評分 (PE) (總分 3) - 採用市場平均PE 20 作為基準
        pe_score = 0
        if 0 < trailingPE <= 15:
            pe_score = 3 # 低估
        elif 15 < trailingPE <= 25:
            pe_score = 2 # 合理
        elif 25 < trailingPE <= 40:
            pe_score = 1 # 略高
        # PE > 40 或 PE < 0 (虧損) 則為 0 分
        
        # 3. 財務健康度評分 (FCF vs. Debt) (總分 3)
        health_score = 0
        cash_vs_debt = (totalCash / totalDebt) if totalDebt > 0 else 99
        
        if freeCashFlow > 0 and cash_vs_debt > 1.5:
            health_score = 3 # 現金充沛，負債低
        elif freeCashFlow > 0 and cash_vs_debt > 1.0:
            health_score = 2 # 現金流健康，現金足夠覆蓋負債
        elif freeCashFlow > 0:
            health_score = 1 # 至少 FCF 為正
        
        # 4. 總評分 (滿分 9 分)
        total_score = roe_score + pe_score + health_score
        
        # 轉換為 0-5.0 星級評分
        combined_rating = round((total_score / 9) * 5, 1)

        message = f"✅ 評分成功。ROE分數: {roe_score}，PE分數: {pe_score}，健康分數: {health_score}。"
        
        return {
            "Combined_Rating": combined_rating,
            "Message": message,
            "Details": {
                "ROE": roe, 
                "Trailing PE": trailingPE,
                "Cash/Debt Ratio": cash_vs_debt,
                "Total Score": total_score
            }
        }

    except Exception as e:
        return {
            "Combined_Rating": 0.0, 
            "Message": f"基本面數據獲取失敗或不適用：{e}", 
            "Details": None
        }

def create_comprehensive_chart(df, symbol, period):
    """創建包含 K線、交易量、RSI 和 MACD 的綜合圖表。"""
    
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="無足夠數據繪製圖表",
                           xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False,
                           font=dict(size=20, color="white"))
        fig.update_layout(height=600, template='plotly_dark')
        return fig
        
    # 定義子圖 (K線/MA + 交易量 + RSI + MACD)
    fig = make_subplots(rows=4, cols=1, 
                        shared_xaxes=True, 
                        vertical_spacing=0.03,
                        row_heights=[0.5, 0.15, 0.15, 0.20]) 
    
    # ------------------ Row 1: K線圖 & MA ------------------
    
    # K線圖
    fig.add_trace(go.Candlestick(x=df.index,
                                open=df['Open'],
                                high=df['High'],
                                low=df['Low'],
                                close=df['Close'],
                                name='K線'), row=1, col=1)
    
    # EMA 10 (短線)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_10'], mode='lines', 
                             name='EMA 10', line=dict(color='yellow', width=1.5)), row=1, col=1)
    # EMA 50 (中長線)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_50'], mode='lines', 
                             name='EMA 50', line=dict(color=TREND_BLUE, width=1.5)), row=1, col=1)
    # EMA 200 (濾鏡)
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA_200'], mode='lines', 
                             name='EMA 200', line=dict(color='orange', width=1.5)), row=1, col=1)

    # 布林通道
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], mode='lines', 
                             name='BB High', line=dict(color='grey', width=1, dash='dot')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], mode='lines', 
                             name='BB Low', line=dict(color='grey', width=1, dash='dot')), row=1, col=1)
    
    # ------------------ Row 2: 交易量 ------------------
    colors = ['#1A890E' if row['Open'] < row['Close'] else '#CC3939' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='交易量', marker_color=colors), row=2, col=1)
    
    # ------------------ Row 3: RSI ------------------
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI (9)', line=dict(color='purple')), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="grey", row=3, col=1, opacity=0.5)
    fig.add_hline(y=30, line_dash="dash", line_color="grey", row=3, col=1, opacity=0.5)

    # ------------------ Row 4: MACD ------------------
    
    # MACD 柱狀圖
    macd_colors = ['red' if val > 0 else 'green' for val in df['MACD']]
    fig.add_trace(go.Bar(x=df.index, y=df['MACD'], name='MACD 柱', marker_color=macd_colors), row=4, col=1)
    # MACD Line & Signal
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Line'], mode='lines', name='MACD Line', line=dict(color=TREND_BLUE, width=1.5)), row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], mode='lines', name='MACD Signal', line=dict(color='yellow', width=1.5)), row=4, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="white", row=4, col=1, opacity=0.5)

    # ------------------ 佈局優化 ------------------
    fig.update_layout(
        title=f"**{symbol}** - {get_company_info(symbol)['name']} | 週期: {period}",
        xaxis_rangeslider_visible=False,
        template='plotly_dark',
        hovermode="x unified",
        legend=dict(orientation="h", y=1.02, x=0.3),
        height=900
    )
    
    # 隱藏非 K線圖的 X 軸標籤
    fig.update_xaxes(showticklabels=True, row=4, col=1)
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(showticklabels=False, row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=3, col=1)
    
    # 調整 Y 軸，避免圖表重疊
    fig.update_yaxes(title_text="價格", row=1, col=1, fixedrange=False)
    fig.update_yaxes(title_text="交易量", row=2, col=1, fixedrange=True)
    fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100], fixedrange=True)
    fig.update_yaxes(title_text="MACD", row=4, col=1, fixedrange=True)
    
    return fig

# ==============================================================================
# 2.1 AI 綜合信號判定與 TP/SL 計算 (新增核心邏輯)
# ==============================================================================
def determine_ai_signal_and_risk(df, technical_df, symbol):
    """
    結合技術指標和 ATR，決定最終交易信號、信心度、TP 和 SL。
    """
    
    if df.empty or technical_df.empty or 'ATR' not in df.columns:
        return {'signal': '數據不足', 'confidence': 0, 'price': 0, 'entry': 0, 'tp': 0, 'sl': 0}

    last_row = df.iloc[-1]
    
    # ------------------ 1. 綜合信號分數 ------------------
    score = 0
    
    # 權重：EMA (2), RSI (1), MACD (1)
    
    # EMA 判斷
    ema_conclusion = technical_df.loc['價格 vs. EMA 10/50/200', '分析結論']
    if '強多頭' in ema_conclusion: score += 2
    elif '強空頭' in ema_conclusion: score -= 2
    elif '偏多' in ema_conclusion: score += 1
    
    # RSI 判斷
    rsi_conclusion = technical_df.loc['RSI (9) 動能', '分析結論']
    if '多頭' in rsi_conclusion: score += 1
    elif '空頭' in rsi_conclusion: score -= 1
    
    # MACD 判斷
    macd_conclusion = technical_df.loc['MACD (8/17/9) 柱狀圖', '分析結論']
    if '多頭動能增強' in macd_conclusion: score += 1
    elif '空頭動能增強' in macd_conclusion: score -= 1
    
    # ADX 判斷 (趨勢濾鏡: ADX < 25 趨勢弱，削弱信心)
    adx_value = technical_df.loc['ADX (9) 趨勢強度', '最新值']
    if adx_value < 25 and abs(score) > 0:
        score = score / 2 # 盤整行情，降低信號強度
        
    # ------------------ 2. 確定信號與信心度 ------------------
    if score >= 1.5:
        signal = "買入"
        confidence = min(100.0, 65.0 + score * 7)
    elif score <= -1.5:
        signal = "賣出"
        confidence = min(100.0, 65.0 + abs(score) * 7)
    else:
        signal = "中性/觀望"
        confidence = 50.0 + abs(score) * 5
        
    # ------------------ 3. 計算 TP/SL (基於 ATR) ------------------
    atr_value = last_row['ATR']
    current_price = last_row['Close']
    
    # 採用 ATR 策略： TP = 2.5 x ATR, SL = 1.5 x ATR
    if signal == '買入':
        tp = current_price + (atr_value * 2.5) 
        sl = current_price - (atr_value * 1.5) 
        entry = current_price
    elif signal == '賣出':
        # 做空：TP 在下方，SL 在上方
        tp = current_price - (atr_value * 2.5) 
        sl = current_price + (atr_value * 1.5)
        entry = current_price
    else:
        # 中性信號：不提供交易參數
        tp, sl, entry = 0.0, 0.0, current_price
        
    
    return {
        'symbol': symbol,
        'signal': signal,
        'confidence': round(confidence, 1),
        'price': round(current_price, 4),
        'entry': round(entry, 4),
        'tp': round(tp, 4),
        'sl': round(sl, 4),
    }

# ==============================================================================
# 3. 圖像生成核心函式 - 3 頁輪播圖 (新增區塊)
# ==============================================================================

# ------------------------------------------------------------------------------
# 3.1 圖像生成核心函式 A: Page 1 (趨勢信號卡 - 結論頁)
# ------------------------------------------------------------------------------
def generate_signal_card(symbol, signal, confidence, price, tp, sl, period):
    """根據數據生成 Page 1 圖片，強調 AI 結論和 CTA。"""
    width, height = 1080, 1350
    img = Image.new('RGB', (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    signal_text = f"AI 建議 {signal}"
    signal_color = TREND_BLUE if signal == '買入' else ALERT_ORANGE if signal == '賣出' else PRIMARY_COLOR
    
    # --- A. LOGO 嵌入 ---
    # (可選：如果您有 LOGO 圖片，可在此處加入浮水印)

    # --- B. 繪製標題與週期 ---
    draw.text((50, 80), f"{symbol}", PRIMARY_COLOR, font=FONT_TITLE)
    draw.text((50, 170), f"週期: {period}", TREND_BLUE, font=FONT_LABEL)

    # --- C. 繪製核心信號 (放大突出) ---
    draw.text((50, 280), signal_text, signal_color, font=FONT_SUPERTITLE)

    # --- D. 繪製數據列表 (交易指令單) ---
    data_y_start = 550
    
    # 數值格式化
    price_str = f"{price:,.2f}"
    entry_str = f"{price:,.2f}"
    tp_str = f"{tp:,.2f}" if tp > 0 else "N/A"
    sl_str = f"{sl:,.2f}" if sl > 0 else "N/A"
    confidence_str = f"{confidence:.1f}%"
    
    data_points = [
        ("策略信賴度:", confidence_str, TREND_BLUE),
        ("最新價格:", price_str, PRIMARY_COLOR),
        ("入場參考:", entry_str, PRIMARY_COLOR),
        ("止盈目標 (TP):", tp_str, TREND_BLUE),
        ("止損價位 (SL):", sl_str, ALERT_ORANGE),
    ]

    for i, (label, value, value_color) in enumerate(data_points):
        y = data_y_start + i * 120
        draw.text((50, y), label, PRIMARY_COLOR, font=FONT_DATA)
        # 居右對齊 (需計算文字寬度)
        text_w, _ = draw.textsize(str(value), font=FONT_DATA)
        draw.text((width - 50 - text_w, y), str(value), value_color, font=FONT_DATA)
            
    # --- E. 底部 CTA 提示 (趨勢藍) ---
    cta_text = "詳情見 App，請向左滑動 →"
    text_width, _ = draw.textsize(cta_text, font=FONT_TITLE)
    draw.text(((width - text_width) / 2, 1200), cta_text, TREND_BLUE, font=FONT_TITLE)

    byte_io = io.BytesIO()
    img.save(byte_io, 'PNG')
    byte_io.seek(0)
    return byte_io


# ------------------------------------------------------------------------------
# 3.2 圖像生成核心函式 B: Page 2 (數據驗證卡 - 信任頁)
# ------------------------------------------------------------------------------
def generate_data_validation_card(symbol, period, technical_data):
    """生成 Page 2 數據驗證卡，模擬 Streamlit 技術指標表格。"""
    width, height = 1080, 1350
    img = Image.new('RGB', (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    
    # 標題
    draw.text((50, 80), f"{symbol} - 關鍵技術指標", PRIMARY_COLOR, font=FONT_TITLE)
    draw.text((50, 170), f"週期: {period}", TREND_BLUE, font=FONT_LABEL)
    
    draw.text((50, 300), "AI 判讀的數據支撐", PRIMARY_COLOR, font=FONT_DATA)

    # 模擬表格 Header
    header_y = 420
    draw.text((50, header_y), "指標名稱", TREND_BLUE, font=FONT_DATA)
    draw.text((400, header_y), "趨勢結論", TREND_BLUE, font=FONT_DATA)
    draw.text((800, header_y), "數值", TREND_BLUE, font=FONT_DATA)
    
    # 模擬分隔線
    draw.line([(50, 470), (1030, 470)], fill=PRIMARY_COLOR, width=3)
    
    # 繪製技術指標數據
    data_y_start = 500
    for i, (name, conclusion, color, value) in enumerate(technical_data):
        y = data_y_start + i * 100
        
        # 指標名稱
        draw.text((50, y), name, PRIMARY_COLOR, font=FONT_DATA)
        # 結論
        draw.text((400, y), conclusion, color, font=FONT_DATA)
        # 數值
        text_w, _ = draw.textsize(str(value), font=FONT_DATA)
        draw.text((width - 50 - text_w, y), value, color, font=FONT_DATA) # 居右對齊

    # 底部 CTA 提示
    cta_text = "更多回測與細節，請向左滑動 →"
    text_width, _ = draw.textsize(cta_text, font=FONT_TITLE)
    draw.text(((width - text_width) / 2, 1200), cta_text, TREND_BLUE, font=FONT_TITLE)
    
    byte_io = io.BytesIO()
    img.save(byte_io, 'PNG')
    byte_io.seek(0)
    return byte_io


# ------------------------------------------------------------------------------
# 3.3 圖像生成核心函式 C: Page 3 (CTA 導流專頁 - 獲利關鍵)
# ------------------------------------------------------------------------------
def generate_cta_card(app_link="[您的 Streamlit App 連結]"):
    """生成 Page 3 強力導流頁。"""
    width, height = 1080, 1350
    img = Image.new('RGB', (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    # --- A. 大標題 (CTA) ---
    title_text = "想驗證 AI 策略？"
    subtitle_text = "前往 APP 立即回測！"
    
    # 居中計算
    title_w, _ = draw.textsize(title_text, font=FONT_TITLE)
    subtitle_w, _ = draw.textsize(subtitle_text, font=FONT_TITLE)
    
    draw.text(((width - title_w) / 2, 200), title_text, PRIMARY_COLOR, font=FONT_TITLE)
    draw.text(((width - subtitle_w) / 2, 350), subtitle_text, TREND_BLUE, font=FONT_TITLE)
    
    # --- B. 視覺引導 (LOGO + 箭頭) ---
    
    arrow_text = "⬇️"
    link_text = f"點擊主頁連結 {app_link}"
    
    # 箭頭
    arrow_w, _ = draw.textsize(arrow_text, font=FONT_SUPERTITLE)
    draw.text(((width - arrow_w) / 2, 600), arrow_text, PRIMARY_COLOR, font=FONT_SUPERTITLE)
    
    # 連結文字
    link_w, _ = draw.textsize(link_text, font=FONT_DATA)
    draw.text(((width - link_w) / 2, 800), link_text, TREND_BLUE, font=FONT_DATA)
    
    # --- C. 免責聲明 ---
    disclaimer = "⚠️ 免責聲明：所有分析僅供參考，不構成任何投資建議。投資有風險，入市需謹慎。"
    disclaimer_font = get_font(30)
    disclaimer_w, _ = draw.textsize(disclaimer, font=disclaimer_font)
    draw.text(((width - disclaimer_w) / 2, 1280), disclaimer, ALERT_ORANGE, font=disclaimer_font)

    byte_io = io.BytesIO()
    img.save(byte_io, 'PNG')
    byte_io.seek(0)
    return byte_io

# ==============================================================================
# 4. Streamlit 應用程式主邏輯 (整合分析與 IG 圖像生成)
# ==============================================================================

# ... (Sidebar 側邊欄邏輯保持不變) ...

# 側邊欄：資產選擇
st.sidebar.title("🔍 選擇分析標的")

selected_category = st.sidebar.selectbox("1. 選擇資產類別", list(CATEGORY_HOT_OPTIONS.keys()))

hot_options = CATEGORY_HOT_OPTIONS[selected_category]
selected_option_key = st.sidebar.selectbox("2. 選擇熱門標的 (或手動輸入)", list(hot_options.keys()))
default_symbol = hot_options[selected_option_key]

# 允許用戶輸入
search_symbol = st.sidebar.text_input(
    "3. 或手動輸入代碼/名稱", 
    value=default_symbol, 
    key='sidebar_search_input'
)

# 週期選擇
selected_period_key = st.sidebar.selectbox("4. 選擇分析週期", list(PERIOD_MAP.keys()))

# 執行分析按鈕
analyze_button_clicked = st.sidebar.button("📊 執行 AI 分析", type="primary")

# 獲取最終分析代碼
final_symbol_to_analyze = get_symbol_from_query(search_symbol)


# 主介面
st.title("🤖 AI 趨勢分析儀表板 📈")
st.markdown("---")


# 執行分析
if analyze_button_clicked:
    st.session_state['data_ready'] = False
    with st.spinner(f"正在分析 {final_symbol_to_analyze} ({selected_period_key}) 的數據..."):
        period, interval = PERIOD_MAP[selected_period_key]
        df = get_stock_data(final_symbol_to_analyze, period, interval)
        
        if not df.empty and len(df) >= 200:
            df = calculate_technical_indicators(df)
            technical_df = get_technical_data_df(df)
            backtest_results = run_backtest(df)
            fundamental_rating = calculate_fundamental_rating(final_symbol_to_analyze)
            
            # 將結果存入 Session State
            st.session_state['df'] = df
            st.session_state['technical_df'] = technical_df
            st.session_state['backtest_results'] = backtest_results
            st.session_state['fundamental_rating'] = fundamental_rating
            st.session_state['final_symbol'] = final_symbol_to_analyze
            st.session_state['period_key'] = selected_period_key
            st.session_state['data_ready'] = True
            
            st.toast(f"{final_symbol_to_analyze} 分析完成！", icon="✅")
        else:
            st.error(f"無法獲取或數據不足以分析 {final_symbol_to_analyze} 的 {selected_period_key} 數據。")
            st.session_state['data_ready'] = False


# 顯示分析結果
if st.session_state.get('data_ready', False):
    df = st.session_state['df']
    technical_df = st.session_state['technical_df']
    backtest_results = st.session_state['backtest_results']
    fundamental_rating = st.session_state['fundamental_rating']
    final_symbol_to_analyze = st.session_state['final_symbol']
    selected_period_key = st.session_state['period_key']
    
    info = get_company_info(final_symbol_to_analyze)
    currency_symbol = get_currency_symbol(final_symbol_to_analyze)

    st.subheader(f"✅ {info['name']} ({final_symbol_to_analyze}) - {selected_period_key} 分析報告")
    
    # 1. 核心指標顯示
    current_price = df['Close'].iloc[-1]
    
    # 執行 IG 專用 AI 綜合信號計算 (新邏輯)
    ai_results = determine_ai_signal_and_risk(df, technical_df, final_symbol_to_analyze)
    
    st.metric(
        label=f"最新價格 ({currency_symbol})", 
        value=f"{current_price:,.2f}", 
        delta=f"AI 信號: {ai_results['signal']}", 
        delta_color="off"
    )

    # 顯示 AI 信號和 TP/SL
    st.markdown("---")
    st.subheader(f"🎯 AI 綜合交易建議 ({ai_results['signal']} 信賴度: {ai_results['confidence']}%)")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("入場參考價", f"{currency_symbol} {ai_results['entry']:,.2f}")
    col_b.metric("止盈目標 (TP)", f"{currency_symbol} {ai_results['tp']:,.2f}", delta_color="inverse" if ai_results['signal']=='賣出' else "normal")
    col_c.metric("止損價位 (SL)", f"{currency_symbol} {ai_results['sl']:,.2f}", delta_color="inverse" if ai_results['signal']=='買入' else "normal")

    # 2. 基本面評級
    st.markdown("---")
    st.subheader(f"🌟 基本面評級 (總評分 {fundamental_rating['Combined_Rating']:.1f} / 5.0)")
    st.markdown(f"**{fundamental_rating['Message']}**")
    
    if fundamental_rating['Details']:
        details = fundamental_rating['Details']
        st.markdown(f"**ROE**: {details['ROE']:.2%} | **PE**: {details['Trailing PE']:.1f} | **現金/負債比**: {details['Cash/Debt Ratio']:.2f}")

    # 3. 量化回測結果
    st.markdown("---")
    st.subheader("🤖 量化回測結果 (SMA 20/EMA 50 策略基準)")
    
    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
    col_r1.metric("總報酬率", f"{backtest_results['total_return']:,.2f}%", delta_color="normal" if backtest_results['total_return'] > 0 else "inverse")
    col_r2.metric("勝率", f"{backtest_results['win_rate']:,.1f}%")
    col_r3.metric("最大回撤", f"{backtest_results['max_drawdown']:,.2f}%", delta_color="inverse")
    col_r4.metric("交易次數", f"{backtest_results['total_trades']}")

    # 4. 關鍵技術指標表格
    st.markdown("---")
    st.subheader(f"🔬 關鍵技術指標細節 ({df.index[-1].strftime('%Y-%m-%d')} 收盤)")
    
    # 轉換顏色欄位讓 Streamlit 顯示
    display_technical_df = technical_df.reset_index().drop(columns=['顏色'])

    st.dataframe(
        display_technical_df, 
        use_container_width=True, 
        key=f"technical_df_{final_symbol_to_analyze}_{selected_period_key}",
        column_config={
            "最新值": st.column_config.Column("最新數值", help="技術指標的最新計算值"),
            "分析結論": st.column_config.Column("趨勢/動能判讀", help="基於數值範圍的專業解讀"),
        }
    )
    st.caption("ℹ️ **設計師提示:** 表格顏色會根據指標的趨勢/風險等級自動變化（**紅色=多頭/強化信號**，**綠色=空頭/削弱信號**，**橙色=中性/警告**）。")

    # 5. 完整技術分析圖表
    st.markdown("---")
    st.subheader(f"📊 完整技術分析圖表")
    chart = create_comprehensive_chart(df, final_symbol_to_analyze, selected_period_key) 
    st.plotly_chart(chart, use_container_width=True, key=f"plotly_chart_{final_symbol_to_analyze}_{selected_period_key}")

    
    # --------------------------------------------------------------------------
    # 6. IG 輪播圖生成與下載 (新功能區塊)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader(f"🖼️ IG 輪播圖貼文生成 (3 頁模板)")
    st.caption("點擊下方按鈕，分別下載 Page 1, Page 2, Page 3 圖片！")
    
    # 準備 Page 2 數據 (將 DataFrame 轉換為列表 for PIL)
    page2_data_list = []
    for index, row in technical_df.iterrows():
        name = index
        conclusion = row['分析結論'].replace("**", "") # 移除 Streamlit markdown 標記
        color_key = row['顏色']
        value = f"{row['最新值']:,.2f}"
        page2_data_list.append((name, conclusion, COLOR_MAP_HEX.get(color_key, PRIMARY_COLOR), value))

    # 圖像生成
    try:
        # Page 1: 信號卡 (使用 ai_results 的真實 TP/SL 和信心度)
        page1_bytes = generate_signal_card(
            symbol=ai_results['symbol'],
            signal=ai_results['signal'],
            confidence=ai_results['confidence'],
            price=ai_results['price'],
            tp=ai_results['tp'],
            sl=ai_results['sl'],
            period=selected_period_key
        )
        
        # Page 2: 數據驗證 (使用 technical_df 的真實指標數據)
        page2_bytes = generate_data_validation_card(
            symbol=final_symbol_to_analyze, 
            period=selected_period_key, 
            technical_data=page2_data_list
        )
        
        # Page 3: 導流 CTA (請將 YOUR_APP_URL 替換為您的實際 Streamlit App 連結)
        YOUR_APP_URL = "https://share.streamlit.io/your-app-link" 
        page3_bytes = generate_cta_card(app_link=YOUR_APP_URL) 

        # 下載按鈕與預覽
        col_dl1, col_dl2, col_dl3 = st.columns(3)
        
        with col_dl1:
            st.download_button(
                label="📥 Page 1: 信號卡 (PNG)",
                data=page1_bytes,
                file_name=f"IG_P1_{ai_results['symbol']}_{ai_results['signal']}.png",
                mime="image/png"
            )
            st.image(page1_bytes, caption=f"Page 1 預覽: {ai_results['signal']}", width=250)
            
        with col_dl2:
            st.download_button(
                label="📥 Page 2: 數據驗證 (PNG)",
                data=page2_bytes,
                file_name=f"IG_P2_{ai_results['symbol']}_Data.png",
                mime="image/png"
            )
            st.image(page2_bytes, caption="Page 2 預覽: 數據證明", width=250)

        with col_dl3:
            st.download_button(
                label="📥 Page 3: 導流 CTA (PNG)",
                data=page3_bytes,
                file_name=f"IG_P3_CTA.png",
                mime="image/png"
            )
            st.image(page3_bytes, caption="Page 3 預覽: 前往 App", width=250)


    except Exception as e:
        st.error(f"IG 圖像生成失敗，請檢查 LOGO 或字體檔案（LOGO.jpg 和 NotoSansTC-Bold.otf）是否存在於程式碼相同目錄下：{e}")


# 首次載入或數據未準備好時的提示
elif not st.session_state.get('data_ready', False) and not analyze_button_clicked:
     st.info("請在左側選擇或輸入標的，然後點擊 **『執行AI分析』** 開始。")

if __name__ == '__main__':
    # Streamlit Session State 初始化，確保變數存在
    if 'last_search_symbol' not in st.session_state:
        st.session_state['last_search_symbol'] = "2330.TW"
    if 'data_ready' not in st.session_state:
        st.session_state['data_ready'] = False
    if 'sidebar_search_input' not in st.session_state:
        st.session_state['sidebar_search_input'] = "2330.TW"
