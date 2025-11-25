import sys
from typing import List, Dict

# --- 1. 固定參數設定 ---
# 投資標的代號與比例 (對應表格 A, B 欄)
STOCKS_ALLOCATION: List[Dict] = [
    {"code": "009813", "weight": 0.50},
    {"code": "0050", "weight": 0.30},
    {"code": "00878", "weight": 0.20},
]

# 手續費率 (對應表格 F 欄)
FEE_RATE: float = 0.001425  # 0.1425%
MIN_FEE: int = 1  # 零股手續費最低 1 元

def get_user_input(prompt: str, data_type=float):
    """取得使用者輸入並確保資料類型正確"""
    while True:
        try:
            user_input = input(prompt).strip()
            if not user_input:
                raise ValueError("輸入不能為空。")
            return data_type(user_input)
        except ValueError as e:
            print(f"輸入錯誤: {e}，請重新輸入。")
        except KeyboardInterrupt:
            print("\n程式終止。")
            sys.exit(0)

def calculate_shares(total_budget: float, stock_prices: Dict[str, float]):
    """根據預算和價格，計算每個標的建議買入的股數和成本"""
    
    results: List[Dict] = []
    total_spent: float = 0.0

    print("\n--- 🛒 計算結果 ---")
    print(f"{'代號':<8} {'比例':<8} {'現價':<8} {'分配金額':<10} {'建議股數':<10} {'預估手續費':<10} {'總成本':<10}")
    print("-" * 75)

    for stock in STOCKS_ALLOCATION:
        code = stock['code']
        weight = stock['weight']
        price = stock_prices.get(code, 0.0)
        
        # 1. 計算分配金額 (對應表格 D 欄)
        allocated_budget = total_budget * weight

        shares_to_buy = 0
        estimated_fee = 0
        total_cost = 0.0
        
        if price > 0:
            # 2. 計算建議買入股數 (對應表格 E 欄)
            # 邏輯: 確保花費不會超過分配預算
            # 股數 = INT(分配金額 / (價格 * (1 + 費率)))
            shares_to_buy = int(allocated_budget / (price * (1 + FEE_RATE)))

            # 3. 計算預估手續費 (對應表格 F 欄)
            # 邏輯: MAX(1, ROUND(價格 * 股數 * 費率))
            fee_calculated = price * shares_to_buy * FEE_RATE
            estimated_fee = max(MIN_FEE, round(fee_calculated))
            
            # 4. 重新確認總成本
            total_cost = (shares_to_buy * price) + estimated_fee

        # 5. 輸出結果
        results.append({
            "代號": code,
            "比例": f"{weight*100:.0f}%",
            "現價": price,
            "分配金額": allocated_budget,
            "建議股數": shares_to_buy,
            "預估手續費": estimated_fee,
            "總成本": total_cost,
        })
        total_spent += total_cost

        # 格式化輸出
        print(
            f"{code:<8} {stock['比例']:<8} {price:<8.2f} {allocated_budget:<10.2f} "
            f"{shares_to_buy:<10} {estimated_fee:<10} {total_cost:<10.2f}"
        )

    print("-" * 75)
    print(f"{'總計花費':>55} {total_spent:<10.2f}")
    print(f"{'剩餘預算':>55} {total_budget - total_spent:<10.2f}")
    print("-----------------------------------")


def main():
    """主程序邏輯"""
    print("--- 零股投資預算計算機 (V1.0) ---")
    print(f"  * 手續費率: {FEE_RATE*100:.4f}% (最低 {MIN_FEE} 元)")
    
    # 取得投資總預算
    total_budget = get_user_input("請輸入本月總投資預算金額: ", data_type=float)
    
    # 取得各標的當前價格
    stock_prices = {}
    print("\n--- 請輸入各標的當前價格 ---")
    for stock in STOCKS_ALLOCATION:
        price = get_user_input(f"請輸入 {stock['code']} 價格 (C欄): ", data_type=float)
        stock_prices[stock['code']] = price

    # 執行計算並輸出結果
    calculate_shares(total_budget, stock_prices)

if __name__ == "__main__":
    main()
