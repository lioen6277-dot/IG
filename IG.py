import streamlit as st
import pandas as pd
import sys

# --- 1. 固定參數與配置 ---

# 設定頁面標題和佈局
st.set_page_config(
    page_title="零股投資計算機",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 手續費率 (F欄下方)
FEE_RATE_DEFAULT: float = 0.001425  # 0.1425%
MIN_FEE: int = 1  # 零股手續費最低 1 元

# 預設標的資料 (A, B, C 欄的初始值)
DEFAULT_STOCKS = pd.DataFrame({
    "標的代號": ["009813", "0050", "00878"],
    "設定比例": [0.50, 0.30, 0.20],
    "當前價格 (請輸入)": [10.00, 60.00, 21.00]  # 初始範例價格
})

# --- 2. 側邊欄輸入區 (Sidebar Inputs) ---

st.sidebar.header("🎯 投資參數設定")

# 總投資額 (對應您的表格 '投資預算')
total_budget = st.sidebar.number_input(
    "每月投資總預算 (TWD)",
    min_value=1000,
    value=20000,
    step=1000,
    format="%d"
)

# 手續費率 (可調整)
fee_rate = st.sidebar.number_input(
    "手續費率 (0.xxxx)",
    min_value=0.0001,
    max_value=0.01,
    value=FEE_RATE_DEFAULT,
    format="%.6f"
)

st.sidebar.caption(f"手續費最低 {MIN_FEE} 元 / 筆")

# --- 3. 主要內容區 (Main Content) ---

st.title("📈 Streamlit 零股投資分配計算機")
st.markdown("---")

st.subheader("價格輸入與比例調整 (C欄)")
st.caption("請直接在表格中編輯『當前價格』欄位的數值")

# 使用 data_editor 讓使用者編輯價格
edited_df = st.data_editor(
    DEFAULT_STOCKS,
    hide_index=True,
    column_config={
        "當前價格 (請輸入)": st.column_config.NumberColumn(
            "當前價格 (請輸入)",
            min_value=0.01,
            format="%.2f"
        )
    },
    num_rows="fixed"
)

# 檢查輸入比例總和
if edited_df['設定比例'].sum() != 1.0:
    st.error(f"⚠️ 警告：設定比例總和必須為 100% (目前為 {edited_df['設定比例'].sum()*100:.0f}%)，請調整。")
    st.stop()


# --- 4. 計算核心邏輯 ---

results_list = []
total_spent = 0.0

for index, row in edited_df.iterrows():
    code = row["標的代號"]
    weight = row["設定比例"]
    price = row["當前價格 (請輸入)"]

    # 1. 分配金額 (D欄)
    allocated_budget = total_budget * weight

    shares_to_buy = 0
    estimated_fee = 0
    total_cost = 0.0

    if price > 0:
        # 2. 建議買入股數 (E欄)
        # 確保總成本不超支 (價格 * (1 + 費率))
        shares_to_buy = int(allocated_budget / (price * (1 + fee_rate)))

        # 3. 預估手續費 (F欄)
        # 邏輯: MAX(1, ROUND(價格 * 股數 * 費率))
        fee_calculated = price * shares_to_buy * fee_rate
        estimated_fee = max(MIN_FEE, round(fee_calculated))

        # 4. 總成本
        total_cost = (shares_to_buy * price) + estimated_fee

    total_spent += total_cost

    results_list.append({
        "標的代號": code,
        "設定比例": f"{weight*100:.0f}%",
        "當前價格 (TWD)": price,
        "分配金額 (D)": allocated_budget,
        "建議買入股數 (E)": shares_to_buy,
        "預估手續費 (F)": estimated_fee,
        "總成本 (G)": total_cost,
    })

# --- 5. 輸出結果 ---

results_df = pd.DataFrame(results_list)

st.subheader("✅ 建議投資分配與結果")
st.dataframe(
    results_df,
    hide_index=True,
    column_config={
        "分配金額 (D)": st.column_config.NumberColumn(format="TWD %d"),
        "總成本 (G)": st.column_config.NumberColumn(format="TWD %d"),
        "當前價格 (TWD)": st.column_config.NumberColumn(format="TWD %.2f")
    }
)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="💰 總投資預算", value=f"TWD {total_budget:,.0f}")

with col2:
    st.metric(label="💸 預估總花費", value=f"TWD {total_spent:,.0f}")

with col3:
    st.metric(label="🎁 剩餘預算", value=f"TWD {total_budget - total_spent:,.0f}")

st.markdown("---")
st.caption("計算邏輯依據：優先確保買入股數最大化，且總花費不超過預算；手續費最低 1 元計算。")
