<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IG 輪播圖 (3 頁) 專業原型</title>
    <!-- 載入 Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap" rel="stylesheet">
    <style>
        /* 自定義顏色和字體，確保符合 IG 的視覺衝擊力 */
        :root {
            --bg-deep-navy: #0B172A; /* 基礎深色科技背景 */
            --color-blue: #00A3FF; /* 趨勢藍 */
            --color-orange: #FF4D00; /* 警示橙 */
        }
        
        .ig-slide {
            width: 400px; /* 固定寬度 */
            height: 600px; /* 4:5 垂直比例，模擬 IG 貼文最佳尺寸 */
            background-color: var(--bg-deep-navy);
            font-family: 'Inter', sans-serif;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
            margin: 20px auto; /* 居中顯示 */
            border-radius: 12px;
            overflow: hidden;
            position: relative;
            transform-style: preserve-3d;
            transition: transform 0.5s ease-in-out, opacity 0.5s ease-in-out;
            border: 1px solid rgba(255, 255, 255, 0.1);
            display: none; /* 預設隱藏，由 JS 控制顯示 */
        }

        .ig-slide.active {
            display: flex;
            opacity: 1;
        }

        /* 自定義 utility class */
        .bg-deep-navy { background-color: var(--bg-deep-navy); }
        .text-trend-blue { color: var(--color-blue); }
        .bg-trend-blue { background-color: var(--color-blue); }
        .text-alert-orange { color: var(--color-orange); }
        .text-pure-white { color: #FFFFFF; }
        .text-shadow-glow { text-shadow: 0 0 5px rgba(0, 163, 255, 0.7), 0 0 10px rgba(0, 163, 255, 0.5); }
        .cta-glow { box-shadow: 0 0 15px rgba(255, 77, 0, 0.8); }

        /* 浮水印樣式 */
        .watermark {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-20deg);
            color: rgba(255, 255, 255, 0.05); /* 極輕微融入背景 */
            font-size: 8rem;
            font-weight: 900;
            user-select: none;
            pointer-events: none;
            z-index: 0;
        }

        /* 模擬 Streamlit 截圖 */
        .screenshot-placeholder {
            width: 90%;
            height: 250px;
            background-color: #2D3748; /* 模擬深色應用程式介面 */
            border: 1px solid #4A5568;
            border-radius: 8px;
            overflow: hidden;
            position: relative;
        }

        .screenshot-watermark {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: rgba(255, 255, 255, 0.15); /* 截圖上更明顯的 LOGO */
            font-size: 3rem;
            font-weight: 700;
        }
    </style>
</head>
<body class="bg-gray-800 p-8">

    <h1 class="text-3xl font-bold text-white text-center mb-6">🤖 AI 交易信號 IG 輪播圖原型</h1>
    <div id="carousel-container" class="flex flex-col items-center">
        <!-- 輪播圖導航按鈕 -->
        <div class="flex space-x-4 mb-6">
            <button onclick="showSlide(0)" id="btn-0" class="px-4 py-2 rounded-full text-sm font-semibold bg-gray-700 text-white transition hover:bg-gray-600">Page 1: 結論</button>
            <button onclick="showSlide(1)" id="btn-1" class="px-4 py-2 rounded-full text-sm font-semibold bg-gray-700 text-white transition hover:bg-gray-600">Page 2: 驗證</button>
            <button onclick="showSlide(2)" id="btn-2" class="px-4 py-2 rounded-full text-sm font-semibold bg-gray-700 text-white transition hover:bg-gray-600">Page 3: CTA</button>
        </div>
        
        <!-- -------------------------------------------------- -->
        <!-- Page 1: 趨勢信號卡 (結論頁) -->
        <!-- -------------------------------------------------- -->
        <div id="slide-0" class="ig-slide flex-col justify-between p-6">
            <div class="watermark">AI EYE</div> <!-- 浮水印品牌識別 -->

            <!-- 頂部資訊：標的名稱與代碼 -->
            <header class="z-10">
                <p class="text-sm font-light text-gray-400">AI 趨勢分析 | 1 日 (中長線)</p>
                <h2 class="text-4xl font-extrabold text-pure-white mt-1">特斯拉</h2>
                <span class="text-lg font-mono text-pure-white">$TSLA</span>
            </header>

            <!-- 核心目標：AI 結論極致突出 (BUY/SELL) -->
            <main class="text-center z-10 -mt-8">
                <div class="text-sm font-bold tracking-wider text-gray-300 uppercase">AI Final Conclusion</div>
                <!-- 根據 conclusion 動態調整顏色和樣式 -->
                <h1 id="conclusion-text" class="text-8xl font-black mt-2 leading-none text-trend-blue text-shadow-glow">
                    買入
                </h1>
                <p class="text-xl font-semibold text-gray-300 mt-2">潛在多頭趨勢確立</p>
            </main>

            <!-- 交易參數：交易指令單 -->
            <footer class="z-10">
                <div class="bg-gray-800/50 backdrop-blur-sm p-4 rounded-xl space-y-2">
                    <div class="flex justify-between border-b border-gray-700 pb-1">
                        <span class="text-sm text-gray-400">最新價格 (Last)</span>
                        <span id="latest-price" class="text-lg font-bold text-pure-white">$195.88</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-400">入場參考 (Entry)</span>
                        <span id="entry-price" class="text-base font-semibold text-trend-blue">$194.50</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-400">止盈點 (TP)</span>
                        <span id="tp-price" class="text-base font-semibold text-green-400">$210.00</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-sm text-gray-400">止損點 (SL)</span>
                        <span id="sl-price" class="text-base font-semibold text-alert-orange">$188.00</span>
                    </div>
                </div>
                <!-- 導流提示 -->
                <p class="text-center text-sm font-semibold text-trend-blue mt-4">詳情見 App，請向左滑動 →</p>
            </footer>
        </div>

        <!-- -------------------------------------------------- -->
        <!-- Page 2: 儀表板數據驗證 (信任頁) -->
        <!-- -------------------------------------------------- -->
        <div id="slide-1" class="ig-slide flex-col justify-between p-6">
            <div class="watermark">DATA</div> <!-- 浮水印品牌識別 -->

            <!-- 頂部資訊：標題與引導文案 -->
            <header class="z-10">
                <h2 class="text-3xl font-extrabold text-pure-white">數據為證。AI 絕非臆測。</h2>
                <p class="text-sm font-light text-gray-400 mt-2">AI 判讀背後的數據支撐：MACD 黃金交叉，RSI 動能強勁。</p>
            </header>

            <!-- 核心內容：Streamlit 截圖模擬 -->
            <main class="flex justify-center z-10 flex-col items-center">
                <div class="screenshot-placeholder">
                    <div class="screenshot-watermark">AI EYE 驗證截圖</div>
                    <!-- 模擬 Streamlit 關鍵指標表格截圖 -->
                    <img id="app-screenshot" src="https://placehold.co/400x250/2D3748/A0AEC0?text=Streamlit+App+關鍵指標截圖" onerror="this.src='https://placehold.co/400x250/2D3748/A0AEC0?text=Streamlit+App+關鍵指標截圖';" alt="Streamlit 關鍵指標截圖" class="w-full h-full object-cover opacity-75">
                    
                    <!-- 模擬突出顯示的 MACD/RSI -->
                    <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-4/5 p-2 bg-black/50 rounded-lg">
                        <p class="text-xs text-white font-mono flex justify-between">
                            <span class="text-gray-400">MACD 黃金交叉:</span>
                            <span class="text-green-400 font-bold">+0.55</span>
                        </p>
                        <p class="text-xs text-white font-mono flex justify-between">
                            <span class="text-gray-400">RSI 多頭動能:</span>
                            <span class="text-green-400 font-bold">68.21</span>
                        </p>
                    </div>
                </div>
                <!-- 模擬 Streamlit 表格數據 -->
                <div id="indicator-list" class="mt-4 w-11/12 text-sm text-gray-300">
                    <!-- JS 會在此處生成指標列表 -->
                </div>
            </main>

            <!-- 導流提示 -->
            <footer class="z-10">
                <p class="text-center text-sm font-semibold text-trend-blue mt-4">更多回測與細節，請向左滑動 →</p>
            </footer>
        </div>

        <!-- -------------------------------------------------- -->
        <!-- Page 3: 行動呼籲專頁 (獲利導流頁) -->
        <!-- -------------------------------------------------- -->
        <div id="slide-2" class="ig-slide flex-col justify-around items-center p-6 text-center">
            <div class="watermark">CTA</div> <!-- 浮水印品牌識別 -->
            
            <!-- 標題 (CTA) 強力指令 -->
            <header class="z-10">
                <h1 class="text-4xl md:text-5xl font-black text-pure-white leading-tight">
                    想驗證 AI 策略？
                </h1>
                <h2 class="text-5xl md:text-6xl font-black text-alert-orange cta-glow">
                    立即行動！
                </h2>
            </header>

            <!-- 核心視覺導航指引 -->
            <main class="z-10 space-y-6">
                <div class="text-pure-white">
                    <!-- 趨勢代碼 LOGO 模擬 (使用 SVG/Emoji) -->
                    <svg class="w-20 h-20 mx-auto text-trend-blue animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                    </svg>
                    <p class="text-xl font-bold mt-2 text-pure-white">$TSLA | 專屬 AI 策略</p>
                </div>

                <!-- 點擊主頁連結指令 -->
                <div class="p-3 rounded-full bg-alert-orange hover:bg-red-600 transition duration-300">
                    <p class="text-lg font-bold text-pure-white tracking-widest">
                        點擊主頁連結 [您的 App 連結]
                    </p>
                </div>
                
                <!-- 醒目的箭頭 指向 Instagram Bio 連結的方向 -->
                <div class="text-4xl text-pure-white animate-bounce">
                    ⬇️ (IG Bio 在下方!)
                </div>
            </main>
            
            <!-- 免責聲明風險提示 -->
            <footer class="z-10">
                <p class="text-xs text-red-400 font-semibold mt-4">
                    ⚠️ 免責聲明：所有策略僅供參考，不構成投資建議。投資涉及風險。
                </p>
            </footer>
        </div>
    </div>

    <script>
        // 模擬 Streamlit App 產生的數據
        const MOCK_DATA = {
            symbol: "TSLA",
            name: "特斯拉",
            period: "1 日 (中長線)",
            conclusion: "BUY", // 可以是 "BUY" 或 "SELL"
            latestPrice: 195.88,
            entryPrice: 194.50,
            tp: 210.00,
            sl: 188.00,
            updateTime: "2025/10/01 09:30 UTC+8",
            // 模擬 Streamlit App 的指標輸出 (對應 app2.0.py 的 st.dataframe)
            indicators: [
                { indicator: "MACD (12, 26, 9)", latestValue: "+0.55", conclusion: "黃金交叉 / 動能強化", signal: "strong_buy" },
                { indicator: "RSI (14)", latestValue: "68.21", conclusion: "強勢區 / 多頭動能", signal: "buy" },
                { indicator: "KDJ (9, 3, 3)", latestValue: "K: 85.3, D: 79.1", conclusion: "超買區 / 警告訊號", signal: "warning" },
                { indicator: "SMA (50)", latestValue: "180.12", conclusion: "價格位於均線上方", signal: "neutral" },
            ],
            // 由於無法載入本地截圖，這裡使用一個預設圖片作為演示
            appScreenshotUrl: "https://placehold.co/400x250/2D3748/A0AEC0?text=Streamlit+App+關鍵指標截圖", 
            appLink: "https://your.app.link"
        };

        let currentSlide = 0;
        const slides = document.querySelectorAll('.ig-slide');
        const totalSlides = slides.length;

        /**
         * 根據 MOCK_DATA 初始化頁面 1 和頁面 2 的動態內容。
         */
        function initializeContent() {
            // --- Page 1 Initialization ---
            const conclusion = MOCK_DATA.conclusion.toUpperCase();
            const colorClass = conclusion === 'BUY' ? 'text-trend-blue' : 'text-alert-orange';
            const conclusionText = conclusion === 'BUY' ? '買入' : '賣出';
            const actionText = conclusion === 'BUY' ? '潛在多頭趨勢確立' : '警示空頭趨勢確立';

            document.getElementById('conclusion-text').textContent = conclusionText;
            document.getElementById('conclusion-text').className = `text-8xl font-black mt-2 leading-none text-pure-white text-shadow-glow ${colorClass}`;
            document.querySelector('#slide-0 main p').textContent = actionText;
            
            document.getElementById('latest-price').textContent = `$${MOCK_DATA.latestPrice.toFixed(2)}`;
            document.getElementById('entry-price').textContent = `$${MOCK_DATA.entryPrice.toFixed(2)}`;
            document.getElementById('tp-price').textContent = `$${MOCK_DATA.tp.toFixed(2)}`;
            document.getElementById('sl-price').textContent = `$${MOCK_DATA.sl.toFixed(2)}`;

            document.querySelector('#slide-0 header h2').textContent = MOCK_DATA.name;
            document.querySelector('#slide-0 header span').textContent = `$${MOCK_DATA.symbol}`;
            document.querySelector('#slide-0 header p').textContent = `AI 趨勢分析 | ${MOCK_DATA.period}`;

            // --- Page 2 Initialization (指標列表) ---
            const indicatorList = document.getElementById('indicator-list');
            indicatorList.innerHTML = MOCK_DATA.indicators.map(item => {
                let valColor = 'text-gray-400';
                if (item.signal.includes('buy') || item.signal === 'strong_buy') {
                    valColor = 'text-green-400'; // 模擬 Streamlit 紅色=強化信號
                } else if (item.signal.includes('warning') || item.signal === 'sell') {
                    valColor = 'text-red-400'; // 模擬 Streamlit 綠色=削弱信號
                }
                
                return `
                    <div class="flex justify-between py-1 border-b border-gray-800">
                        <span class="text-xs text-gray-500">${item.indicator}</span>
                        <span class="text-xs ${valColor} font-bold">${item.latestValue}</span>
                        <span class="text-xs ${valColor}">${item.conclusion}</span>
                    </div>
                `;
            }).join('');
            
            // 更新 Page 2 的引導文案
            const mainSignal = MOCK_DATA.indicators.find(i => i.signal === 'strong_buy' || i.signal === 'buy');
            if (mainSignal) {
                document.querySelector('#slide-1 header p').textContent = `AI 判讀背後的數據支撐：${mainSignal.indicator} ${mainSignal.conclusion}，信號強勁。`;
            }
            
            document.getElementById('app-screenshot').src = MOCK_DATA.appScreenshotUrl;

            // --- Page 3 Initialization ---
            document.querySelector('#slide-2 main p.text-xl').textContent = `$${MOCK_DATA.symbol} | 專屬 AI 策略`;
            document.querySelector('#slide-2 main div.bg-alert-orange p').textContent = `點擊主頁連結 [${MOCK_DATA.appLink}]`;
        }

        /**
         * 切換顯示的頁面
         * @param {number} index - 0, 1, or 2
         */
        function showSlide(index) {
            slides.forEach((slide, i) => {
                slide.classList.remove('active');
                if (i === index) {
                    slide.classList.add('active');
                }
            });
            
            document.querySelectorAll('#carousel-container button').forEach((btn, i) => {
                btn.classList.remove('bg-trend-blue', 'text-black', 'bg-gray-700');
                if (i === index) {
                    btn.classList.add('bg-trend-blue', 'text-black');
                } else {
                    btn.classList.add('bg-gray-700');
                }
            });
            currentSlide = index;
        }

        // 頁面載入時初始化內容並顯示第一頁
        window.onload = () => {
            initializeContent();
            showSlide(0);
        };
    </script>
</body>
</html>
