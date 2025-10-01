import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
from PIL import Image, ImageDraw, ImageFont # 引入圖像處理核心庫
from io import BytesIO
import numpy as np # 仍然保留部分基礎庫以防萬一

# 警告處理：隱藏 Pandas 或 TA-Lib 可能發出的未來警告
warnings.filterwarnings('ignore')

# =============================================================================
# 1. 頁面配置與全局設定
# =============================================================================

st.set_page_config(
    page_title="🖼️ IG 輪播圖生成器",
    page_icon="🎨", 
    layout="centered" # 改為 centered 讓圖片輸出更集中
)

# 圖像設定
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1080
LOGO_PATH = "LOGO.jpg" # 確保此檔案存在於專案根目錄
FONT_PATH = "NotoSansTC-Bold.otf" # 確保此檔案存在且支援繁體中文

# 顏色定義
COLOR_BACKGROUND = (255, 255, 255) # 白色背景
COLOR_PRIMARY = (255, 99, 71)      # 亮紅色
COLOR_SECONDARY = (65, 105, 225)   # 寶藍色
COLOR_TEXT_DARK = (50, 50, 50)     # 深灰文字
COLOR_TEXT_LIGHT = (150, 150, 150) # 淺灰文字

# 字體載入 (如果字體檔案不存在，Streamlit 可能無法載入或報錯，所以需要 try-except)
try:
    # 大部分文字使用 40 號字體
    FONT_NORMAL = ImageFont.truetype(FONT_PATH, 40)
    # 標題使用 60 號字體
    FONT_HEADER = ImageFont.truetype(FONT_PATH, 60)
    # 建議/訊號使用 90 號字體
    FONT_SIGNAL = ImageFont.truetype(FONT_PATH, 90)
    # 最小字體用於版權/提示
    FONT_SMALL = ImageFont.truetype(FONT_PATH, 24)
except Exception as e:
    st.error(f"字體載入失敗，請檢查檔案路徑：{FONT_PATH} ({e})")
    # 如果載入失敗，使用預設字體作為 fallback
    FONT_NORMAL = ImageFont.load_default()
    FONT_HEADER = ImageFont.load_default()
    FONT_SIGNAL = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()


# ==============================================================================
# 2. 圖像生成核心函數 (已修正 textsize -> textbbox)
# ==============================================================================

def generate_ig_image(page_name, data):
    """
    統一的圖片生成函數，根據頁面名稱繪製內容。
    **核心修正點：將 draw.textsize(...) 替換為 draw.textbbox(...)**
    """
    
    img = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), color=COLOR_BACKGROUND)
    draw = ImageDraw.Draw(img)
    center_x = IMAGE_WIDTH // 2
    
    # 嘗試加載 LOGO 作為浮水印
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        logo_w, logo_h = logo.size
        # 將 LOGO 縮小為 80x80
        logo = logo.resize((80, 80))
        # 放在右上角
        img.paste(logo, (IMAGE_WIDTH - logo.width - 40, 40), logo)
    except FileNotFoundError:
        draw.text((IMAGE_WIDTH - 200, 50), "LOGO.jpg 缺失", fill=COLOR_TEXT_LIGHT, font=FONT_SMALL)
    except Exception as e:
        draw.text((IMAGE_WIDTH - 200, 50), f"LOGO 錯誤: {e}", fill=COLOR_TEXT_LIGHT, font=FONT_SMALL)

    
    # Page 1: 標題頁
    if page_name == "Page 1":
        title_text = f"🔥 {data['symbol_name']} ({data['symbol']}) 分析報告"
        signal_text = data['signal_text']
        confidence_text = f"信賴度: {data['confidence']}"
        
        # 繪製主標題
        draw.text((center_x, 200), page_name, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_HEADER)
        
        # 繪製大標題
        # === 修正點 1: 使用 textbbox 替代 textsize ===
        bbox = draw.textbbox((0, 0), title_text, font=FONT_HEADER)
        text_h = bbox[3] - bbox[1]
        draw.text((center_x, 300), title_text, anchor="ms", fill=COLOR_TEXT_DARK, font=FONT_HEADER)
        
        # 繪製 AI 信號 (大字體)
        signal_color = COLOR_PRIMARY if "多頭" in signal_text else (50, 180, 50) if "空頭" in signal_text else COLOR_SECONDARY
        
        # === 修正點 2: 使用 textbbox 替代 textsize ===
        bbox = draw.textbbox((0, 0), signal_text, font=FONT_SIGNAL)
        text_h = bbox[3] - bbox[1]
        draw.text((center_x, 550), signal_text, anchor="ms", fill=signal_color, font=FONT_SIGNAL)

        # 繪製信賴度
        draw.text((center_x, 650), confidence_text, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)
        
        # 頁腳提示
        footer_text = "滑動查看: 交易建議 | 技術細節 | 量化回測"
        draw.text((center_x, IMAGE_HEIGHT - 100), footer_text, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)

    # Page 2: 交易建議與回測
    elif page_name == "Page 2":
        draw.text((center_x, 150), page_name, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_HEADER)
        draw.text((center_x, 250), "🎯 AI 綜合交易建議", anchor="ms", fill=COLOR_PRIMARY, font=FONT_HEADER)
        
        # 繪製交易建議框 (簡化版)
        y_start = 350
        draw.text((center_x, y_start + 50), f"入場參考價: {data['entry_price']}", anchor="ms", fill=COLOR_TEXT_DARK, font=FONT_NORMAL)
        draw.text((center_x, y_start + 120), f"止盈目標 (TP): {data['tp']}", anchor="ms", fill=COLOR_TEXT_DARK, font=FONT_NORMAL)
        draw.text((center_x, y_start + 190), f"止損價位 (SL): {data['sl']}", anchor="ms", fill=COLOR_TEXT_DARK, font=FONT_NORMAL)

        draw.line([(100, 600), (IMAGE_WIDTH - 100, 600)], fill=COLOR_TEXT_LIGHT, width=2)
        
        # 繪製回測結果
        draw.text((center_x, 650), "🤖 量化回測結果", anchor="ms", fill=COLOR_SECONDARY, font=FONT_HEADER)
        draw.text((center_x, 750), f"總報酬率: {data['return']}", anchor="ms", fill=COLOR_TEXT_DARK, font=FONT_NORMAL)
        draw.text((center_x, 820), f"勝率: {data['win_rate']}", anchor="ms", fill=COLOR_TEXT_DARK, font=FONT_NORMAL)
        draw.text((center_x, 890), f"最大回撤: {data['max_drawdown']}", anchor="ms", fill=COLOR_TEXT_DARK, font=FONT_NORMAL)
        
    # Page 3: 技術指標細節 (簡化版)
    elif page_name == "Page 3":
        draw.text((center_x, 150), page_name, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_HEADER)
        draw.text((center_x, 250), "🔬 關鍵技術指標細節", anchor="ms", fill=COLOR_PRIMARY, font=FONT_HEADER)
        
        y_pos = 350
        
        # 模擬指標表格，以文字形式呈現
        indicators = data['indicators']
        
        for name, detail in indicators.items():
            value_text = f"{name}: {detail['value']}"
            conclusion_text = f" -> {detail['conclusion']}"
            
            # 繪製指標名稱和值
            draw.text((150, y_pos), value_text, fill=COLOR_TEXT_DARK, font=FONT_NORMAL)
            
            # 根據結論設定顏色
            if "多頭" in detail['conclusion']:
                conclusion_color = COLOR_PRIMARY
            elif "空頭" in detail['conclusion']:
                conclusion_color = (50, 180, 50) # 綠色
            else:
                conclusion_color = COLOR_SECONDARY # 藍色
                
            # === 修正點 3: 使用 textbbox 替代 textsize ===
            # 先計算 value_text 的寬度，以便在右側對齊 conclusion_text
            bbox_value = draw.textbbox((0, 0), value_text, font=FONT_NORMAL)
            value_w = bbox_value[2] - bbox_value[0]
            
            # 在 value_text 結束後開始繪製 conclusion_text
            draw.text((150 + value_w + 30, y_pos), conclusion_text, fill=conclusion_color, font=FONT_NORMAL)
            
            y_pos += 80

        # 頁腳提示
        footer_text = f"分析週期: {data['period']} | {data['date']}"
        draw.text((center_x, IMAGE_HEIGHT - 100), footer_text, anchor="ms", fill=COLOR_TEXT_LIGHT, font=FONT_NORMAL)

    
    # 將 PIL Image 轉換為 PNG 格式的 BytesIO 對象，以便 Streamlit 下載按鈕使用
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ==============================================================================
# 3. Streamlit UI 
# ==============================================================================

# 模擬數據，因為我們移除了數據獲取和分析邏輯
# 這些數據將用於圖片生成，您可以根據實際分析結果替換
DUMMY_DATA = {
    'symbol': 'AAPL',
    'symbol_name': '蘋果公司',
    'signal_text': '✅ 多頭趨勢',
    'confidence': '85.0%',
    'entry_price': '$ 253.95',
    'tp': '$ 265.50',
    'sl': '$ 248.00',
    'return': '11.28%',
    'win_rate': '60.0%',
    'max_drawdown': '5.18%',
    'period': '30 分 (短期)',
    'date': '2025-09-30',
    'indicators': {
        'RSI (14)': {'value': '65.23', 'conclusion': '多頭強化'},
        'MACD (12, 26)': {'value': '1.50', 'conclusion': '多頭訊號'},
        'ATR (14)': {'value': '2.15', 'conclusion': '中性波動'},
        'Stoch (14, 3)': {'value': '85.00', 'conclusion': '空頭警告 (超買)'}
    }
}


st.markdown("<h1 style='text-align: center;'>🖼️ IG 輪播圖貼文生成器 🎨</h1>", unsafe_allow_html=True)
st.markdown("---")

# 由於移除了數據獲取，我們讓使用者直接輸入標的名稱和週期，用於顯示
col1, col2 = st.columns(2)
with col1:
    user_symbol = st.text_input("輸入股票/代碼 (e.g., AAPL)", value="AAPL")
with col2:
    user_period = st.selectbox("選擇分析週期", options=["30 分 (短期)", "4 小時 (波段)", "1 日 (中長線)", "1 週 (長期)"])

# 讓模擬數據使用用戶輸入的值
DUMMY_DATA['symbol'] = user_symbol
DUMMY_DATA['period'] = user_period
DUMMY_DATA['symbol_name'] = "模擬標的" # 由於沒法查，用模擬名稱

st.markdown("---")


st.subheader("🖼️ IG 輪播圖貼文生成 (3 頁模板)")

# 圖像生成與下載按鈕
try:
    # Page 1
    page1_bytes = generate_ig_image("Page 1", DUMMY_DATA)
    st.download_button(
        label="⬇️ 下載 Page 1 (標題頁)",
        data=page1_bytes,
        file_name=f"{user_symbol}_{user_period}_Page1.png",
        mime="image/png",
        key='dl_button_1'
    )
    
    # Page 2
    page2_bytes = generate_ig_image("Page 2", DUMMY_DATA)
    st.download_button(
        label="⬇️ 下載 Page 2 (建議/回測)",
        data=page2_bytes,
        file_name=f"{user_symbol}_{user_period}_Page2.png",
        mime="image/png",
        key='dl_button_2'
    )

    # Page 3
    page3_bytes = generate_ig_image("Page 3", DUMMY_DATA)
    st.download_button(
        label="⬇️ 下載 Page 3 (技術細節)",
        data=page3_bytes,
        file_name=f"{user_symbol}_{user_period}_Page3.png",
        mime="image/png",
        key='dl_button_3'
    )
    
    st.success("🎉 圖片已成功生成，請點擊上方按鈕下載！")

except Exception as e:
    st.error(f"""
    **IG 圖像生成失敗！** 程式碼已修復，但仍需您檢查以下檔案：
    
    - **LOGO 檔案：** 必須有一個名為 `{LOGO_PATH}` 的圖片檔（如 `.jpg` 或 `.png`）在程式碼相同目錄下。
    - **字體檔案：** 必須有一個名為 `{FONT_PATH}` 的繁體中文字體檔案在程式碼相同目錄下。

    **原始錯誤 (已修復但仍可能因檔案缺失而觸發其他錯誤):** {e}
    """)

st.markdown("---")
st.caption("ℹ️ 這是專注於 IG 圖像生成的精簡版。所有分析數據皆為模擬值。")
