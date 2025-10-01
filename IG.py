import streamlit as st
import os
import io
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import numpy as np
# 這裡可以加入您原有的其他 import，例如 yfinance 或其他數據處理函式庫

# ==============================================================================
# 1. 圖像生成核心功能區
#    目標：生成 Page 1 趨勢信號卡
# ==============================================================================
# ⚠️ 請將 LOGO.jpg 和 NotoSansTC-Bold.otf 上傳至 GitHub
LOGO_PATH = "LOGO.jpg" 
FONT_PATH = "NotoSansTC-Bold.otf"

# 顏色定義 (深色科技風)
BACKGROUND_COLOR = '#0B172A'  # 深藍色背景
PRIMARY_COLOR = '#FFFFFF'     # 白色文字
TREND_BLUE = '#00A3FF'        # 趨勢藍 (買入/多頭信號)
ALERT_ORANGE = '#FF4D00'      # 警示橙 (賣出/止損信號)

# ------------------------------------------------------------------------------
# 1.1 字體載入與處理
# ------------------------------------------------------------------------------
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
FONT_TITLE = get_font(80) 
FONT_DATA = get_font(40)
FONT_LABEL = get_font(32)

# ------------------------------------------------------------------------------
# 1.2 圖像生成核心函式
# ------------------------------------------------------------------------------
def generate_signal_card(symbol, signal, confidence, price, tp, sl, period):
    """根據數據生成 IG 垂直信號卡圖片，返回 BytesIO 物件。"""
    width, height = 1080, 1350
    img = Image.new('RGB', (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    # A. LOGO 嵌入 (右下角浮水印)
    if os.path.exists(LOGO_PATH):
        try:
            logo_img = Image.open(LOGO_PATH).convert("RGBA")
            scale_factor = 200 / logo_img.width
            new_logo_size = (200, int(logo_img.height * scale_factor))
            logo_img = logo_img.resize(new_logo_size)
            alpha = logo_img.split()[3].point(lambda p: p * 0.3)
            logo_img.putalpha(alpha)
            
            logo_x = width - new_logo_size[0] - 30
            logo_y = height - new_logo_size[1] - 30
            img.paste(logo_img, (logo_x, logo_y), logo_img)
        except Exception:
            pass

    # B. 繪製標題與週期
    draw.text((50, 80), f"{symbol}", PRIMARY_COLOR, font=FONT_TITLE)
    draw.text((50, 170), f"週期: {period}", TREND_BLUE, font=FONT_LABEL)

    # C. 繪製核心信號 (最醒目)
    signal_text = f"AI 建議 {signal}"
    signal_color = TREND_BLUE if signal == '買入' else ALERT_ORANGE if signal == '賣出' else PRIMARY_COLOR
    draw.text((50, 300), signal_text, signal_color, font=FONT_TITLE)

    # D. 繪製數據列表
    data_y_start = 550
    
    # 數值格式化
    try:
        price_str = f"{price:.2f}"
        tp_str = f"{tp:.2f}"
        sl_str = f"{sl:.2f}"
        confidence_str = f"{confidence:.1f}%"
    except (TypeError, ValueError):
        price_str, tp_str, sl_str, confidence_str = "N/A", "N/A", "N/A", "N/A"
    
    data_points = [
        ("策略信賴度:", confidence_str, TREND_BLUE),
        ("最新價格:", price_str, PRIMARY_COLOR),
        ("入場參考:", price_str, PRIMARY_COLOR),
        ("止盈目標 (TP):", tp_str, TREND_BLUE),
        ("止損價位 (SL):", sl_str, ALERT_ORANGE),
    ]

    for i, (label, value, value_color) in enumerate(data_points):
        y = data_y_start + i * 120
        draw.text((50, y), label, PRIMARY_COLOR, font=FONT_DATA)
        draw.text((700, y), str(value), value_color, font=FONT_DATA)
            
    # E. 輸出為 BytesIO
    byte_io = io.BytesIO()
    img.save(byte_io, 'PNG')
    byte_io.seek(0)
    return byte_io

# ==============================================================================
# 2. Streamlit 應用程式主邏輯 (替換您的 IG.py 內容)
# ==============================================================================

st.set_page_config(layout="wide", page_title="趨勢代碼 AI 分析儀表板")
st.title("📈 趨勢代碼 AI 數據分析")
st.markdown("---")


# ⚠️ 這裡的 DUMMY 數據僅為展示，您必須用您的 AI 邏輯計算出的實際數據替換！
DUMMY_DATA = {
    'symbol': 'TSLA',
    'signal': '買入',
    'confidence': 92.5,
    'price': 254.30,
    'tp': 275.50,
    'sl': 230.10,
    'period': '1 日 (中長線)'
}

# ------------------------------------------------------------------------------
# 2.1 數據輸入與分析區塊 (請用您的實際分析邏輯替換此區塊)
# ------------------------------------------------------------------------------
col1, col2, col3 = st.columns([1, 1, 2])

with col1:
    symbol_input = st.text_input("輸入股票/資產代碼", value=DUMMY_DATA['symbol'])
with col2:
    period_input = st.selectbox("選擇分析週期", ['1 日 (中長線)', '4 小時 (短線)', '1 週 (長線)'])
with col3:
    st.markdown("---") # 為了對齊，這裡留空

analyze_button = st.button("運行 AI 趨勢分析", type="primary")

# 這裡是一個模擬的數據 DataFrame
df = pd.DataFrame({'Close': [DUMMY_DATA['price']] * 5}) 

if analyze_button:
    # ⚠️ 在這裡加入您的 AI 分析、數據獲取和圖表繪製邏輯
    st.success(f"已完成 {symbol_input} 的 AI 分析！")

    # --------------------------------------------------------------------------
    # 2.2 圖像生成與下載按鈕 (整合區)
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📸 IG 貼文內容一鍵生成 (Page 1)")
    st.caption("點擊下方按鈕，自動生成 Page 1 的 AI 趨勢信號卡圖片！")

    try:
        # --- 傳遞數據給圖像生成函式 ---
        ig_image_bytes = generate_signal_card(
            symbol_input, 
            DUMMY_DATA['signal'], 
            DUMMY_DATA['confidence'], 
            DUMMY_DATA['price'], 
            DUMMY_DATA['tp'], 
            DUMMY_DATA['sl'], 
            period_input
        )

        # --- Streamlit 下載按鈕 ---
        download_file_name = f"IG_Page1_{symbol_input}_{DUMMY_DATA['signal']}.png"
        st.download_button(
            label="📥 下載 Page 1 信號卡 (PNG)",
            data=ig_image_bytes,
            file_name=download_file_name,
            mime="image/png"
        )
        
        st.image(ig_image_bytes, caption="AI 趨勢信號卡預覽", width=400)

    except Exception as e:
        st.error(f"圖像生成失敗，請檢查 LOGO 或字體檔案路徑是否正確：{e}")

# ==============================================================================
# 3. 關於 OCR 截圖數據提取的說明
# ==============================================================================
st.markdown("---")
st.subheader("💡 關於『截圖數據提取』的說明")
st.markdown(
    """
您提到的 **「生成式 AI 需要依照截圖內容去獲得數據並代入模板中」** 是自動化流程的終極目標。
這項功能需要強大的 **OCR（光學字符識別）** 技術。

在目前的單一 Streamlit 檔案架構中，最可靠且不需額外付費 API 的流程是：
1.  **計算優先：** 讓您的 AI 模型在 `IG.py` **計算**出所有數據 (例如止盈價 TP)。
2.  **自動傳遞：** 將這些計算出的數據 **直接傳遞** 給 `generate_signal_card()` 函式。

**如果堅持使用截圖：** 則您需要使用 **Google Gemini API** 或 **Google Cloud Vision API** 來進行 OCR 圖像辨識，這會增加程式碼複雜度和運行成本。建議先以 **「計算-生成」** 的流程來穩定您的內容輸出。
"""
)
