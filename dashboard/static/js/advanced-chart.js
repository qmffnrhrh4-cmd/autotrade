/**
 * Advanced Trading Chart - Enhanced UX Version
 * Features: Multiple Timeframes, Technical Indicators, Drawing Tools
 */

class AdvancedTradingChart {
    constructor(containerId) {
        this.containerId = containerId;
        this.mainChart = null;
        this.candlestickSeries = null;
        this.rsiChart = null;
        this.macdChart = null;
        this.volumeChart = null;
        this.canvas = null;
        this.ctx = null;

        // Current state
        this.currentStockCode = '005930';
        this.currentTimeframe = 'D'; // D=일봉, W=주봉, M=월봉, 숫자=분봉
        this.rawData = null; // Store raw data for timeframe conversion

        // Series for indicators
        this.series = {
            ma5: null,
            ma20: null,
            ma60: null,
            ema12: null,
            ema26: null,
            bb_upper: null,
            bb_middle: null,
            bb_lower: null,
            rsi: null,
            macd_line: null,
            macd_signal: null,
            macd_histogram: null,
            volume: null
        };

        // Drawing tools state
        this.drawingMode = null;
        this.drawings = [];
        this.currentDrawing = null;
        this.isDrawing = false;
        this.startPoint = null;

        // Indicator visibility
        this.indicatorsVisible = {
            ma5: true,
            ma20: true,
            ma60: false,
            ema12: false,
            ema26: false,
            bb: false,
            rsi: true,
            macd: true,
            volume: true
        };

        // Panel visibility
        this.panelsVisible = {
            rsi: true,
            macd: true,
            volume: true
        };

        // v6.1: Multi-chart comparison
        this.comparisonStocks = []; // [{code, name, series, color}]
        this.comparisonColors = ['#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#14b8a6'];
        this.nextColorIndex = 0;
    }

    /**
     * Fetch with timeout (타임아웃 기능이 있는 fetch)
     * @param {string} url - 요청 URL
     * @param {object} options - fetch 옵션
     * @param {number} timeout - 타임아웃 시간 (ms, 기본값: 10000ms)
     */
    async fetchWithTimeout(url, options = {}, timeout = 10000) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('요청 시간이 초과되었습니다');
            }
            throw error;
        }
    }

    initialize() {
        const container = document.getElementById(this.containerId);
        if (!container) {
            console.error('Chart container not found:', this.containerId);
            return;
        }

        // Create chart layout
        this.createChartLayout(container);

        // Initialize main chart
        this.initMainChart();

        // Initialize indicator charts
        if (this.panelsVisible.rsi) this.initRSIChart();
        if (this.panelsVisible.macd) this.initMACDChart();
        if (this.panelsVisible.volume) this.initVolumeChart();

        // Setup drawing tools
        this.setupDrawingTools();

        // Handle resize
        window.addEventListener('resize', () => this.handleResize());
    }

    createChartLayout(container) {
        container.innerHTML = `
            <!-- Enhanced Toolbar -->
            <div class="chart-toolbar-enhanced" id="chart-toolbar">
                <!-- Timeframe Group -->
                <div class="toolbar-section">
                    <div class="toolbar-section-title">
                        <i class="fas fa-clock"></i> 시간봉
                    </div>
                    <div class="toolbar-button-group">
                        <button class="tf-btn tf-minute" data-timeframe="1" onclick="advancedChart.changeTimeframe('1')" title="1분봉">1분</button>
                        <button class="tf-btn tf-minute" data-timeframe="3" onclick="advancedChart.changeTimeframe('3')" title="3분봉">3분</button>
                        <button class="tf-btn tf-minute" data-timeframe="5" onclick="advancedChart.changeTimeframe('5')" title="5분봉">5분</button>
                        <button class="tf-btn tf-minute" data-timeframe="10" onclick="advancedChart.changeTimeframe('10')" title="10분봉">10분</button>
                        <button class="tf-btn tf-minute" data-timeframe="30" onclick="advancedChart.changeTimeframe('30')" title="30분봉">30분</button>
                        <button class="tf-btn tf-minute" data-timeframe="60" onclick="advancedChart.changeTimeframe('60')" title="60분봉">60분</button>
                    </div>
                    <div class="toolbar-button-group">
                        <button class="tf-btn tf-major active" data-timeframe="D" onclick="advancedChart.changeTimeframe('D')" title="일봉">
                            <i class="fas fa-sun"></i> 일봉
                        </button>
                        <button class="tf-btn tf-major" data-timeframe="W" onclick="advancedChart.changeTimeframe('W')" title="주봉">
                            <i class="fas fa-calendar-week"></i> 주봉
                        </button>
                        <button class="tf-btn tf-major" data-timeframe="M" onclick="advancedChart.changeTimeframe('M')" title="월봉">
                            <i class="fas fa-calendar-alt"></i> 월봉
                        </button>
                    </div>
                </div>

                <!-- Indicators Group -->
                <div class="toolbar-section">
                    <div class="toolbar-section-title">
                        <i class="fas fa-chart-line"></i> 이동평균
                    </div>
                    <div class="toolbar-button-group">
                        <button class="ind-btn active" data-indicator="ma5" onclick="advancedChart.toggleIndicator('ma5')" title="5일 이동평균">
                            <span class="ind-color" style="background: #f59e0b;"></span> MA5
                        </button>
                        <button class="ind-btn active" data-indicator="ma20" onclick="advancedChart.toggleIndicator('ma20')" title="20일 이동평균">
                            <span class="ind-color" style="background: #3b82f6;"></span> MA20
                        </button>
                        <button class="ind-btn" data-indicator="ma60" onclick="advancedChart.toggleIndicator('ma60')" title="60일 이동평균">
                            <span class="ind-color" style="background: #8b5cf6;"></span> MA60
                        </button>
                        <button class="ind-btn" data-indicator="bb" onclick="advancedChart.toggleIndicator('bb')" title="볼린저 밴드">
                            <i class="fas fa-chart-area"></i> BB
                        </button>
                    </div>
                </div>

                <!-- Drawing Tools Group (v6.1: Enhanced) -->
                <div class="toolbar-section">
                    <div class="toolbar-section-title">
                        <i class="fas fa-pen"></i> 그리기
                    </div>
                    <div class="toolbar-button-group">
                        <button class="draw-btn" onclick="advancedChart.setDrawingMode('trendline')" title="추세선">
                            <i class="fas fa-slash"></i> 추세선
                        </button>
                        <button class="draw-btn" onclick="advancedChart.setDrawingMode('fibonacci')" title="피보나치 되돌림">
                            <i class="fas fa-layer-group"></i> 피보나치
                        </button>
                        <button class="draw-btn" onclick="advancedChart.setDrawingMode('horizontal')" title="수평선">
                            <i class="fas fa-minus"></i>
                        </button>
                        <button class="draw-btn" onclick="advancedChart.setDrawingMode('rectangle')" title="사각형">
                            <i class="far fa-square"></i>
                        </button>
                        <button class="draw-btn" onclick="advancedChart.clearDrawings()" title="모두 지우기">
                            <i class="fas fa-eraser"></i> 지우기
                        </button>
                    </div>
                </div>

                <!-- Multi-Chart Comparison (v6.1: NEW) -->
                <div class="toolbar-section">
                    <div class="toolbar-section-title">
                        <i class="fas fa-layer-group"></i> 차트 비교
                    </div>
                    <div class="toolbar-button-group">
                        <button class="ctrl-btn" onclick="advancedChart.toggleComparisonMode()" title="비교 모드">
                            <i class="fas fa-plus"></i> 종목 추가
                        </button>
                        <button class="ctrl-btn" onclick="advancedChart.clearComparison()" title="비교 종목 제거">
                            <i class="fas fa-times"></i> 초기화
                        </button>
                    </div>
                    <div id="comparison-stocks" style="display: flex; gap: 4px; flex-wrap: wrap; margin-top: 8px;">
                        <!-- 비교 종목 태그들이 여기에 표시됨 -->
                    </div>
                </div>

                <!-- Chart Controls -->
                <div class="toolbar-section">
                    <div class="toolbar-section-title">
                        <i class="fas fa-cog"></i> 설정
                    </div>
                    <div class="toolbar-button-group">
                        <button class="ctrl-btn" onclick="advancedChart.togglePanel('rsi')" title="RSI 패널">
                            <i class="fas fa-chart-line"></i> RSI
                        </button>
                        <button class="ctrl-btn" onclick="advancedChart.togglePanel('macd')" title="MACD 패널">
                            <i class="fas fa-signal"></i> MACD
                        </button>
                        <button class="ctrl-btn" onclick="advancedChart.togglePanel('volume')" title="거래량 패널">
                            <i class="fas fa-chart-bar"></i> 거래량
                        </button>
                    </div>
                </div>
            </div>

            <!-- Chart Panels (v6.1: Flexible Layout - Fixed Height) -->
            <div id="chart-panels-wrapper" style="display: flex; flex-direction: column; height: 700px; max-height: 700px; overflow: hidden;">
                <div style="position: relative; flex: 1 1 auto; min-height: 300px; overflow: hidden;">
                    <canvas id="drawing-canvas" style="position: absolute; top: 0; left: 0; z-index: 10; pointer-events: auto;"></canvas>
                    <div id="main-chart-container" class="chart-panel-enhanced" style="height: 100%; position: relative;"></div>
                </div>
                <div id="rsi-chart-container" class="chart-panel-enhanced indicator-panel" style="flex: 0 0 100px; margin-top: 5px; min-height: 80px; display: block;"></div>
                <div id="macd-chart-container" class="chart-panel-enhanced indicator-panel" style="flex: 0 0 120px; margin-top: 5px; min-height: 90px; display: block;"></div>
                <div id="volume-chart-container" class="chart-panel-enhanced indicator-panel" style="flex: 0 0 90px; margin-top: 5px; min-height: 70px; display: block;"></div>
            </div>
        `;
    }

    initMainChart() {
        const container = document.getElementById('main-chart-container');
        if (!container) {
            console.error('Main chart container not found');
            return;
        }

        this.mainChart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 380,
            layout: {
                background: { color: '#1a1d2e' },
                textColor: '#a5b1c2',
            },
            grid: {
                vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
                horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {
                    color: '#758ca3',
                    width: 1,
                    style: 1,
                    labelBackgroundColor: '#3b82f6',
                },
                horzLine: {
                    color: '#758ca3',
                    width: 1,
                    style: 1,
                    labelBackgroundColor: '#3b82f6',
                },
            },
            rightPriceScale: {
                borderColor: '#2a2e39',
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.2,
                },
            },
            timeScale: {
                borderColor: '#2a2e39',
                timeVisible: true,
                secondsVisible: false,
            },
        });

        // Add candlestick series with Korean market colors (상승=빨강, 하락=파랑)
        this.candlestickSeries = this.mainChart.addCandlestickSeries({
            upColor: '#ef4444',        // Red for up
            downColor: '#3b82f6',      // Blue for down
            borderVisible: false,
            wickUpColor: '#ef4444',    // Red wick for up
            wickDownColor: '#3b82f6',  // Blue wick for down
        });

        // Add MA series
        this.series.ma5 = this.mainChart.addLineSeries({
            color: '#f59e0b',
            lineWidth: 2,
            title: 'MA5',
            visible: this.indicatorsVisible.ma5,
            priceLineVisible: false,
        });

        this.series.ma20 = this.mainChart.addLineSeries({
            color: '#3b82f6',
            lineWidth: 2,
            title: 'MA20',
            visible: this.indicatorsVisible.ma20,
            priceLineVisible: false,
        });

        this.series.ma60 = this.mainChart.addLineSeries({
            color: '#8b5cf6',
            lineWidth: 2,
            title: 'MA60',
            visible: this.indicatorsVisible.ma60,
            priceLineVisible: false,
        });

        // Bollinger Bands
        this.series.bb_upper = this.mainChart.addLineSeries({
            color: '#6366f1',
            lineWidth: 1,
            lineStyle: 2,
            visible: this.indicatorsVisible.bb,
            priceLineVisible: false,
        });

        this.series.bb_middle = this.mainChart.addLineSeries({
            color: '#94a3b8',
            lineWidth: 1,
            visible: this.indicatorsVisible.bb,
            priceLineVisible: false,
        });

        this.series.bb_lower = this.mainChart.addLineSeries({
            color: '#6366f1',
            lineWidth: 1,
            lineStyle: 2,
            visible: this.indicatorsVisible.bb,
            priceLineVisible: false,
        });
    }

    initRSIChart() {
        const container = document.getElementById('rsi-chart-container');
        if (!container) {
            console.log('RSI chart container not found');
            return;
        }
        if (!this.mainChart) {
            console.log('Main chart not initialized, skipping RSI chart sync');
            return;
        }

        this.rsiChart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 100,
            layout: {
                background: { color: '#1a1d2e' },
                textColor: '#a5b1c2',
            },
            grid: {
                vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
                horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
            },
            rightPriceScale: {
                borderColor: '#2a2e39',
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1,
                },
            },
            timeScale: {
                borderColor: '#2a2e39',
                visible: false,
            },
        });

        this.series.rsi = this.rsiChart.addLineSeries({
            color: '#a855f7',
            lineWidth: 2,
            title: 'RSI(14)',
        });

        // Add reference lines
        this.rsiChart.addLineSeries({
            color: 'rgba(239, 68, 68, 0.5)',
            lineWidth: 1,
            lineStyle: 2,
            priceLineVisible: false,
        }).setData([{time: '2020-01-01', value: 70}, {time: '2030-01-01', value: 70}]);

        this.rsiChart.addLineSeries({
            color: 'rgba(34, 197, 94, 0.5)',
            lineWidth: 1,
            lineStyle: 2,
            priceLineVisible: false,
        }).setData([{time: '2020-01-01', value: 30}, {time: '2030-01-01', value: 30}]);

        // Sync with main chart
        this.mainChart.timeScale().subscribeVisibleTimeRangeChange(() => {
            const range = this.mainChart.timeScale().getVisibleRange();
            if (range && this.rsiChart) {
                this.rsiChart.timeScale().setVisibleRange(range);
            }
        });
    }

    initMACDChart() {
        const container = document.getElementById('macd-chart-container');
        if (!container) {
            console.log('MACD chart container not found');
            return;
        }
        if (!this.mainChart) {
            console.log('Main chart not initialized, skipping MACD chart sync');
            return;
        }

        this.macdChart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 120,
            layout: {
                background: { color: '#1a1d2e' },
                textColor: '#a5b1c2',
            },
            grid: {
                vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
                horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
            },
            rightPriceScale: {
                borderColor: '#2a2e39',
            },
            timeScale: {
                borderColor: '#2a2e39',
                visible: false,
            },
        });

        // Histogram
        this.series.macd_histogram = this.macdChart.addHistogramSeries({
            priceFormat: {
                type: 'volume',
            },
        });

        // MACD Line
        this.series.macd_line = this.macdChart.addLineSeries({
            color: '#3b82f6',
            lineWidth: 2,
            title: 'MACD',
            priceLineVisible: false,
        });

        // Signal Line
        this.series.macd_signal = this.macdChart.addLineSeries({
            color: '#f59e0b',
            lineWidth: 2,
            title: 'Signal',
            priceLineVisible: false,
        });

        // Sync with main chart
        this.mainChart.timeScale().subscribeVisibleTimeRangeChange(() => {
            const range = this.mainChart.timeScale().getVisibleRange();
            if (range && this.macdChart) {
                this.macdChart.timeScale().setVisibleRange(range);
            }
        });
    }

    initVolumeChart() {
        const container = document.getElementById('volume-chart-container');
        if (!container) {
            console.log('Volume chart container not found');
            return;
        }
        if (!this.mainChart) {
            console.log('Main chart not initialized, skipping Volume chart sync');
            return;
        }

        this.volumeChart = LightweightCharts.createChart(container, {
            width: container.clientWidth,
            height: 90,
            layout: {
                background: { color: '#1a1d2e' },
                textColor: '#a5b1c2',
            },
            grid: {
                vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
                horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
            },
            rightPriceScale: {
                borderColor: '#2a2e39',
            },
            timeScale: {
                borderColor: '#2a2e39',
                visible: true,
                timeVisible: true,
            },
        });

        this.series.volume = this.volumeChart.addHistogramSeries({
            priceFormat: {
                type: 'volume',
            },
            priceScaleId: '',
        });

        // Sync with main chart
        this.mainChart.timeScale().subscribeVisibleTimeRangeChange(() => {
            const range = this.mainChart.timeScale().getVisibleRange();
            if (range && this.volumeChart) {
                this.volumeChart.timeScale().setVisibleRange(range);
            }
        });
    }

    async loadData(stockCode, timeframe = null) {
        try {
            this.currentStockCode = stockCode;
            if (timeframe) {
                this.currentTimeframe = timeframe;
            }

            // v6.0: Request correct timeframe from API (daily or minute)
            const url = `/api/chart/${stockCode}?timeframe=${this.currentTimeframe}`;
            console.log(`📡 Fetching chart data: ${url}`);
            const response = await this.fetchWithTimeout(url);
            const data = await response.json();

            if (!data.success || !data.data || data.data.length === 0) {
                console.error('No chart data available');
                this.showError('차트 데이터를 불러올 수 없습니다.');
                return;
            }

            // Store raw data for timeframe conversion (only for D/W/M aggregation)
            if (this.currentTimeframe === 'D') {
                this.rawData = data;
            }

            // Convert data based on timeframe (only for W/M aggregation)
            const processedData = this.convertTimeframe(data.data, this.currentTimeframe);

            // Update chart
            this.updateChartWithData(processedData, data);

            // AI 자동 분석 (차트 로드 완료 후)
            this.autoAnalyzeChart(stockCode, this.currentTimeframe);

        } catch (error) {
            console.error('Error loading chart data:', error);
            this.showError('차트 데이터 로드 실패');
        }
    }

    convertTimeframe(dailyData, timeframe) {
        if (timeframe === 'D' || timeframe.match(/^\d+$/)) {
            // For daily or minute data, return as is
            return dailyData;
        }

        if (timeframe === 'W') {
            // Convert to weekly
            return this.aggregateToWeekly(dailyData);
        }

        if (timeframe === 'M') {
            // Convert to monthly
            return this.aggregateToMonthly(dailyData);
        }

        return dailyData;
    }

    aggregateToWeekly(dailyData) {
        const weekly = [];
        let weekData = [];
        let lastDate = null;

        dailyData.forEach((day, index) => {
            const date = new Date(day.time);
            const weekNum = this.getWeekNumber(date);

            if (lastDate && weekNum !== this.getWeekNumber(lastDate)) {
                // New week, aggregate previous week
                if (weekData.length > 0) {
                    weekly.push(this.aggregateCandles(weekData));
                    weekData = [];
                }
            }

            weekData.push(day);
            lastDate = date;

            // Last item
            if (index === dailyData.length - 1 && weekData.length > 0) {
                weekly.push(this.aggregateCandles(weekData));
            }
        });

        return weekly;
    }

    aggregateToMonthly(dailyData) {
        const monthly = [];
        let monthData = [];
        let lastMonth = null;

        dailyData.forEach((day, index) => {
            const date = new Date(day.time);
            const month = date.getFullYear() * 12 + date.getMonth();

            if (lastMonth !== null && month !== lastMonth) {
                // New month, aggregate previous month
                if (monthData.length > 0) {
                    monthly.push(this.aggregateCandles(monthData));
                    monthData = [];
                }
            }

            monthData.push(day);
            lastMonth = month;

            // Last item
            if (index === dailyData.length - 1 && monthData.length > 0) {
                monthly.push(this.aggregateCandles(monthData));
            }
        });

        return monthly;
    }

    aggregateCandles(candles) {
        if (candles.length === 0) return null;

        const firstCandle = candles[0];
        const lastCandle = candles[candles.length - 1];

        // Sum up volume if it exists
        const totalVolume = candles.reduce((sum, c) => sum + (c.volume || 0), 0);

        return {
            time: lastCandle.time, // Use last candle's time
            open: firstCandle.open,
            high: Math.max(...candles.map(c => c.high)),
            low: Math.min(...candles.map(c => c.low)),
            close: lastCandle.close,
            volume: totalVolume
        };
    }

    getWeekNumber(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
        return Math.ceil((((d - yearStart) / 86400000) + 1)/7);
    }

    updateChartWithData(chartData, originalData) {
        console.log(`📊 Updating chart with ${chartData.length} candles, timeframe: ${this.currentTimeframe}`);

        // Update chart title and price
        const chartStockName = document.getElementById('chart-stock-name');
        const chartPrice = document.getElementById('chart-price');
        if (chartStockName) {
            chartStockName.textContent = originalData.name || this.currentStockCode;
        }
        if (chartPrice && originalData.current_price) {
            chartPrice.textContent = '₩' + this.formatNumber(originalData.current_price);
        }

        // Set candlestick data
        if (!this.candlestickSeries) {
            console.error('Candlestick series not initialized');
            return;
        }
        this.candlestickSeries.setData(chartData);

        // For weekly/monthly, create volume data from aggregated candles
        if (this.currentTimeframe === 'W' || this.currentTimeframe === 'M') {
            // Generate volume data from chartData (상승=빨강, 하락=파랑)
            const volumeData = chartData.map(candle => ({
                time: candle.time,
                value: candle.volume || 0,
                color: candle.close >= candle.open ? 'rgba(239, 68, 68, 0.5)' : 'rgba(59, 130, 246, 0.5)'  // Red for up, Blue for down
            }));

            if (this.series.volume) {
                this.series.volume.setData(volumeData);
            }

            // Clear indicators for weekly/monthly (they're based on daily data)
            if (this.series.ma5) this.series.ma5.setData([]);
            if (this.series.ma20) this.series.ma20.setData([]);
            if (this.series.ma60) this.series.ma60.setData([]);
            if (this.series.bb_upper) {
                this.series.bb_upper.setData([]);
                this.series.bb_middle.setData([]);
                this.series.bb_lower.setData([]);
            }
            if (this.series.rsi) this.series.rsi.setData([]);
            if (this.series.macd_line) {
                this.series.macd_line.setData([]);
                this.series.macd_signal.setData([]);
                this.series.macd_histogram.setData([]);
            }

            console.log('📊 Weekly/Monthly mode: Indicators hidden, volume aggregated');
            return;
        }

        // Set indicator data (only for daily and minute charts)
        const indicators = originalData.indicators || {};

        if (indicators.ma5 && this.series.ma5) {
            this.series.ma5.setData(indicators.ma5);
        }

        if (indicators.ma20 && this.series.ma20) {
            this.series.ma20.setData(indicators.ma20);
        }

        if (indicators.ma60 && this.series.ma60) {
            this.series.ma60.setData(indicators.ma60);
        }

        if (indicators.bb_upper && this.series.bb_upper) {
            this.series.bb_upper.setData(indicators.bb_upper);
            this.series.bb_middle.setData(indicators.bb_middle);
            this.series.bb_lower.setData(indicators.bb_lower);
        }

        if (indicators.rsi && this.series.rsi) {
            this.series.rsi.setData(indicators.rsi);
        }

        if (indicators.macd && this.series.macd_line) {
            const macdData = indicators.macd.map(item => ({
                time: item.time,
                value: item.macd
            }));

            const signalData = indicators.macd.map(item => ({
                time: item.time,
                value: item.signal
            }));

            const histogramData = indicators.macd.map(item => ({
                time: item.time,
                value: item.histogram,
                color: item.histogram >= 0 ? 'rgba(38, 166, 154, 0.8)' : 'rgba(239, 83, 80, 0.8)'
            }));

            this.series.macd_line.setData(macdData);
            this.series.macd_signal.setData(signalData);
            this.series.macd_histogram.setData(histogramData);
        }

        if (indicators.volume && this.series.volume) {
            this.series.volume.setData(indicators.volume);
        }

        console.log('✅ Chart updated successfully with indicators');
    }

    toggleIndicator(indicator) {
        this.indicatorsVisible[indicator] = !this.indicatorsVisible[indicator];

        const btn = event.target.closest('[data-indicator="' + indicator + '"]');
        if (btn) {
            btn.classList.toggle('active');
        }

        switch(indicator) {
            case 'ma5':
                this.series.ma5.applyOptions({ visible: this.indicatorsVisible.ma5 });
                break;
            case 'ma20':
                this.series.ma20.applyOptions({ visible: this.indicatorsVisible.ma20 });
                break;
            case 'ma60':
                this.series.ma60.applyOptions({ visible: this.indicatorsVisible.ma60 });
                break;
            case 'bb':
                const visible = this.indicatorsVisible.bb;
                this.series.bb_upper.applyOptions({ visible });
                this.series.bb_middle.applyOptions({ visible });
                this.series.bb_lower.applyOptions({ visible });
                break;
        }
    }

    togglePanel(panel) {
        this.panelsVisible[panel] = !this.panelsVisible[panel];

        const container = document.getElementById(`${panel}-chart-container`);
        if (container) {
            container.style.display = this.panelsVisible[panel] ? 'block' : 'none';
        }

        // Toggle button state
        const btn = event.target.closest('.ctrl-btn');
        if (btn) {
            btn.classList.toggle('active');
        }

        // Resize charts
        setTimeout(() => this.handleResize(), 100);
    }

    async changeTimeframe(timeframe) {
        try {
            console.log(`🔄 Changing timeframe to: ${timeframe}`);
            this.showLoading();

            // For D/W/M timeframes, ensure we have daily data first
            if (timeframe === 'D' || timeframe === 'W' || timeframe === 'M') {
                // If we don't have raw daily data, fetch it first
                if (!this.rawData) {
                    console.log('📡 Fetching daily data for conversion');
                    const url = `/api/chart/${this.currentStockCode}?timeframe=D`;
                    const response = await this.fetchWithTimeout(url);
                    const data = await response.json();

                    if (data.success && data.data && data.data.length > 0) {
                        this.rawData = data;
                        console.log(`✅ Loaded ${data.data.length} daily candles for conversion`);
                    } else {
                        console.error('❌ Failed to load daily data');
                        this.showError('일봉 데이터를 불러올 수 없습니다.');
                        return;
                    }
                }

                // Now convert to the desired timeframe
                console.log(`📈 Converting ${this.rawData.data.length} daily candles to ${timeframe}`);
                const processedData = this.convertTimeframe(this.rawData.data, timeframe);
                console.log(`✅ Converted to ${processedData.length} ${timeframe} candles`);

                // Update button states
                this.updateButtonStates(timeframe);
                this.currentTimeframe = timeframe;
                this.updateChartWithData(processedData, this.rawData);

            } else if (timeframe.match(/^\d+$/)) {
                // Minute data - fetch from server
                console.log(`📡 Fetching ${timeframe}-minute data from server`);
                const url = `/api/chart/${this.currentStockCode}?timeframe=${timeframe}`;
                const response = await this.fetchWithTimeout(url);
                const data = await response.json();

                if (data.success && data.data && data.data.length > 0) {
                    console.log(`📦 Received ${data.data.length} data points`);

                    // Check if fallback occurred (server returned different timeframe)
                    const actualTimeframe = data.timeframe || timeframe;
                    if (actualTimeframe !== timeframe) {
                        console.warn(`⚠️ Requested ${timeframe}min but got ${actualTimeframe}`);
                        this.showWarning(`${timeframe}분봉 데이터를 사용할 수 없어 일봉을 표시합니다.`);

                        // Update to the actual timeframe returned
                        this.updateButtonStates(actualTimeframe);
                        this.currentTimeframe = actualTimeframe;

                        // Store as rawData if it's daily data
                        if (actualTimeframe === 'D') {
                            this.rawData = data;
                        }
                    } else {
                        // Successfully got minute data
                        this.updateButtonStates(timeframe);
                        this.currentTimeframe = timeframe;
                    }

                    this.updateChartWithData(data.data, data);
                } else {
                    console.error('❌ No data received from server');
                    this.showError('차트 데이터를 불러올 수 없습니다.');
                }
            }

        } catch (error) {
            console.error('❌ Timeframe change error:', error);
            this.showError('시간봉 변경 실패');
        } finally {
            this.hideLoading();
        }
    }

    updateButtonStates(timeframe) {
        // Update button states
        document.querySelectorAll('[data-timeframe]').forEach(btn => {
            if (btn.getAttribute('data-timeframe') === timeframe) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    setDrawingMode(mode) {
        this.drawingMode = this.drawingMode === mode ? null : mode;

        // Update button states
        document.querySelectorAll('.draw-btn').forEach(btn => {
            const btnMode = btn.getAttribute('onclick')?.match(/setDrawingMode\('(.+?)'\)/)?.[1];
            if (btnMode && btnMode === mode) {
                if (this.drawingMode) {
                    btn.classList.add('active');
                } else {
                    btn.classList.remove('active');
                }
            }
        });

        if (this.drawingMode) {
            this.canvas.style.cursor = 'crosshair';
        } else {
            this.canvas.style.cursor = 'default';
        }
    }

    clearDrawings() {
        this.drawings = [];
        this.redrawCanvas();
    }

    setupDrawingTools() {
        this.canvas = document.getElementById('drawing-canvas');
        if (!this.canvas) return;

        const mainContainer = document.getElementById('main-chart-container');
        this.canvas.width = mainContainer.clientWidth;
        this.canvas.height = mainContainer.offsetHeight;
        this.ctx = this.canvas.getContext('2d');

        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('mouseleave', (e) => this.onMouseUp(e));
    }

    onMouseDown(e) {
        if (!this.drawingMode) return;

        const rect = this.canvas.getBoundingClientRect();
        this.isDrawing = true;
        this.startPoint = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    onMouseMove(e) {
        if (!this.isDrawing || !this.drawingMode) return;

        const rect = this.canvas.getBoundingClientRect();
        const currentPoint = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };

        this.redrawCanvas();

        this.ctx.strokeStyle = '#3b82f6';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([]);
        this.ctx.beginPath();

        if (this.drawingMode === 'trendline') {
            this.ctx.moveTo(this.startPoint.x, this.startPoint.y);
            this.ctx.lineTo(currentPoint.x, currentPoint.y);
        } else if (this.drawingMode === 'horizontal') {
            this.ctx.moveTo(0, this.startPoint.y);
            this.ctx.lineTo(this.canvas.width, this.startPoint.y);
        } else if (this.drawingMode === 'vertical') {
            this.ctx.moveTo(this.startPoint.x, 0);
            this.ctx.lineTo(this.startPoint.x, this.canvas.height);
        } else if (this.drawingMode === 'rectangle') {
            // v6.1: Rectangle drawing
            const width = currentPoint.x - this.startPoint.x;
            const height = currentPoint.y - this.startPoint.y;
            this.ctx.rect(this.startPoint.x, this.startPoint.y, width, height);
        } else if (this.drawingMode === 'fibonacci') {
            // v6.1: Fibonacci retracement preview
            this.drawFibonacci(this.startPoint, currentPoint, true);
            return; // Skip default stroke
        }

        this.ctx.stroke();
    }

    onMouseUp(e) {
        if (!this.isDrawing || !this.drawingMode) return;

        const rect = this.canvas.getBoundingClientRect();
        const endPoint = {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };

        this.drawings.push({
            type: this.drawingMode,
            start: this.startPoint,
            end: endPoint,
            color: '#3b82f6'
        });

        this.isDrawing = false;
        this.redrawCanvas();
    }

    redrawCanvas() {
        if (!this.ctx) return;

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        this.drawings.forEach(drawing => {
            this.ctx.strokeStyle = drawing.color;
            this.ctx.lineWidth = 2;
            this.ctx.setLineDash([]);
            this.ctx.beginPath();

            if (drawing.type === 'trendline') {
                this.ctx.moveTo(drawing.start.x, drawing.start.y);
                this.ctx.lineTo(drawing.end.x, drawing.end.y);
                this.ctx.stroke();
            } else if (drawing.type === 'horizontal') {
                this.ctx.moveTo(0, drawing.start.y);
                this.ctx.lineTo(this.canvas.width, drawing.start.y);
                this.ctx.stroke();
            } else if (drawing.type === 'vertical') {
                this.ctx.moveTo(drawing.start.x, 0);
                this.ctx.lineTo(drawing.start.x, this.canvas.height);
                this.ctx.stroke();
            } else if (drawing.type === 'rectangle') {
                // v6.1: Rectangle
                const width = drawing.end.x - drawing.start.x;
                const height = drawing.end.y - drawing.start.y;
                this.ctx.rect(drawing.start.x, drawing.start.y, width, height);
                this.ctx.stroke();
            } else if (drawing.type === 'fibonacci') {
                // v6.1: Fibonacci retracement
                this.drawFibonacci(drawing.start, drawing.end, false);
            }
        });
    }

    // v6.1: Draw Fibonacci retracement levels
    drawFibonacci(start, end, isPreview) {
        const levels = [
            { ratio: 0, label: '0.0%', color: '#ef4444' },
            { ratio: 0.236, label: '23.6%', color: '#f59e0b' },
            { ratio: 0.382, label: '38.2%', color: '#eab308' },
            { ratio: 0.5, label: '50.0%', color: '#84cc16' },
            { ratio: 0.618, label: '61.8%', color: '#10b981' },
            { ratio: 1.0, label: '100%', color: '#3b82f6' }
        ];

        const height = end.y - start.y;

        levels.forEach(level => {
            const y = start.y + (height * level.ratio);

            this.ctx.strokeStyle = level.color;
            this.ctx.lineWidth = isPreview ? 1 : 2;
            this.ctx.setLineDash(isPreview ? [5, 5] : []);
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width, y);
            this.ctx.stroke();

            // Draw label
            if (!isPreview) {
                this.ctx.fillStyle = level.color;
                this.ctx.font = '12px sans-serif';
                this.ctx.fillText(level.label, 10, y - 5);
            }
        });
    }

    handleResize() {
        const mainContainer = document.getElementById('main-chart-container');
        const rsiContainer = document.getElementById('rsi-chart-container');
        const macdContainer = document.getElementById('macd-chart-container');
        const volumeContainer = document.getElementById('volume-chart-container');

        // v6.1: Dynamic height support for flexible layout
        if (this.mainChart && mainContainer) {
            this.mainChart.applyOptions({
                width: mainContainer.clientWidth,
                height: mainContainer.clientHeight
            });
        }
        if (this.rsiChart && rsiContainer && this.panelsVisible.rsi) {
            this.rsiChart.applyOptions({
                width: rsiContainer.clientWidth,
                height: rsiContainer.clientHeight
            });
        }
        if (this.macdChart && macdContainer && this.panelsVisible.macd) {
            this.macdChart.applyOptions({
                width: macdContainer.clientWidth,
                height: macdContainer.clientHeight
            });
        }
        if (this.volumeChart && volumeContainer && this.panelsVisible.volume) {
            this.volumeChart.applyOptions({
                width: volumeContainer.clientWidth,
                height: volumeContainer.clientHeight
            });
        }

        if (this.canvas && mainContainer) {
            this.canvas.width = mainContainer.clientWidth;
            this.canvas.height = mainContainer.clientHeight;
            this.redrawCanvas();
        }
    }

    formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    }

    showLoading() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        let loader = container.querySelector('.chart-loader');
        if (!loader) {
            loader = document.createElement('div');
            loader.className = 'chart-loader';
            loader.innerHTML = `
                <div class="chart-loader-spinner"></div>
                <div class="chart-loader-text">차트 로딩 중...</div>
            `;
            container.appendChild(loader);
        }
        loader.style.display = 'flex';
    }

    hideLoading() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        const loader = container.querySelector('.chart-loader');
        if (loader) {
            loader.style.display = 'none';
        }
    }

    showError(message) {
        this.showToast(message, 'error');
    }

    showWarning(message) {
        this.showToast(message, 'warning');
    }

    showToast(message, type = 'info') {
        const existingToasts = document.querySelectorAll('.chart-toast');
        existingToasts.forEach(toast => toast.remove());

        const toast = document.createElement('div');
        toast.className = `chart-toast chart-toast-${type}`;
        toast.innerHTML = `
            <i class="fas ${type === 'error' ? 'fa-exclamation-circle' : type === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle'}"></i>
            <span>${message}</span>
        `;

        document.body.appendChild(toast);

        setTimeout(() => toast.classList.add('show'), 10);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    // ============================================================
    // v6.1: Multi-Chart Comparison Functions
    // ============================================================

    toggleComparisonMode() {
        const stockCode = prompt('비교할 종목 코드를 입력하세요 (예: 000660):', '');
        if (!stockCode) return;

        this.addComparisonStock(stockCode.trim());
    }

    async addComparisonStock(stockCode) {
        // Check if already added
        if (this.comparisonStocks.find(s => s.code === stockCode)) {
            this.showWarning('이미 추가된 종목입니다');
            return;
        }

        // Check limit (max 5 comparison stocks)
        if (this.comparisonStocks.length >= 5) {
            this.showWarning('최대 5개 종목까지 비교 가능합니다');
            return;
        }

        try {
            this.showLoading();

            // Fetch stock data
            const response = await this.fetchWithTimeout(`/api/chart/${stockCode}?timeframe=D`);
            const data = await response.json();

            if (!data.success || !data.data || data.data.length === 0) {
                this.showError('종목 데이터를 불러올 수 없습니다');
                this.hideLoading();
                return;
            }

            // Get next color
            const color = this.comparisonColors[this.nextColorIndex % this.comparisonColors.length];
            this.nextColorIndex++;

            // Create line series for comparison
            const lineSeries = this.mainChart.addLineSeries({
                color: color,
                lineWidth: 2,
                title: data.name || stockCode
            });

            // Convert data format
            const lineData = data.data.map(candle => ({
                time: candle.time,
                value: candle.close
            }));

            lineSeries.setData(lineData);

            // Store comparison stock
            this.comparisonStocks.push({
                code: stockCode,
                name: data.name || stockCode,
                series: lineSeries,
                color: color
            });

            // Update UI
            this.updateComparisonUI();
            this.hideLoading();
            this.showToast(`${data.name || stockCode} 종목이 추가되었습니다`, 'info');

        } catch (error) {
            console.error('Failed to add comparison stock:', error);
            this.showError('종목 추가 실패: ' + error.message);
            this.hideLoading();
        }
    }

    removeComparisonStock(stockCode) {
        const index = this.comparisonStocks.findIndex(s => s.code === stockCode);
        if (index === -1) return;

        const stock = this.comparisonStocks[index];

        // Remove series from chart
        this.mainChart.removeSeries(stock.series);

        // Remove from array
        this.comparisonStocks.splice(index, 1);

        // Update UI
        this.updateComparisonUI();
        this.showToast(`${stock.name} 종목이 제거되었습니다`, 'info');
    }

    clearComparison() {
        // Remove all comparison series
        this.comparisonStocks.forEach(stock => {
            this.mainChart.removeSeries(stock.series);
        });

        // Clear array
        this.comparisonStocks = [];
        this.nextColorIndex = 0;

        // Update UI
        this.updateComparisonUI();
        this.showToast('모든 비교 종목이 제거되었습니다', 'info');
    }

    updateComparisonUI() {
        const container = document.getElementById('comparison-stocks');
        if (!container) return;

        if (this.comparisonStocks.length === 0) {
            container.innerHTML = '<span style="font-size: 11px; color: var(--text-muted);">비교 종목이 없습니다</span>';
            return;
        }

        container.innerHTML = this.comparisonStocks.map(stock => `
            <div style="
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px 10px;
                background: ${stock.color}22;
                border: 1px solid ${stock.color};
                border-radius: 12px;
                font-size: 11px;
                font-weight: 500;
            ">
                <span style="color: ${stock.color};">⬤</span>
                <span>${stock.name}</span>
                <button
                    onclick="advancedChart.removeComparisonStock('${stock.code}')"
                    style="
                        background: none;
                        border: none;
                        color: ${stock.color};
                        cursor: pointer;
                        padding: 0;
                        margin-left: 4px;
                        font-size: 14px;
                        line-height: 1;
                    "
                    title="제거"
                >×</button>
            </div>
        `).join('');
    }

    // ============================================================
    // AI 자동 차트 분석
    // ============================================================

    /**
     * AI 자동 차트 분석
     */
    async autoAnalyzeChart(stockCode, timeframe) {
        try {
            console.log(`🤖 AI 차트 분석 시작: ${stockCode} (${timeframe})`);

            const url = `/api/chart/ai_analysis/${stockCode}?timeframe=${timeframe}`;
            const response = await this.fetchWithTimeout(url);
            const data = await response.json();

            if (data.success && data.analysis_points) {
                // AI 분석 결과를 차트에 마커로 표시
                this.displayAIAnalysis(data.analysis_points, data.summary);
                console.log(`✅ AI 분석 완료: ${data.analysis_points.length}개 포인트 발견`);
            }
        } catch (error) {
            console.warn('AI 차트 분석 실패:', error);
            // 분석 실패는 차트 표시를 막지 않음 (조용히 실패)
        }
    }

    /**
     * AI 분석 결과를 차트에 표시
     */
    displayAIAnalysis(analysisPoints, summary) {
        if (!this.candlestickSeries || !analysisPoints || analysisPoints.length === 0) {
            return;
        }

        // 분석 포인트를 마커로 변환
        const markers = analysisPoints.map(point => {
            // signal 타입에 따라 색상 및 위치 결정
            let color, position, shape, text;

            if (point.signal === 'bullish') {
                // 상승 시그널 - 빨강, 아래쪽, 위 화살표
                color = '#ef4444';
                position = 'belowBar';
                shape = 'arrowUp';
                text = '매수';
            } else if (point.signal === 'bearish') {
                // 하락 시그널 - 파랑, 위쪽, 아래 화살표
                color = '#3b82f6';
                position = 'aboveBar';
                shape = 'arrowDown';
                text = '매도';
            } else if (point.type === 'support') {
                // 지지선 - 초록, 아래쪽, 원
                color = '#10b981';
                position = 'belowBar';
                shape = 'circle';
                text = '지지';
            } else if (point.type === 'resistance') {
                // 저항선 - 주황, 위쪽, 원
                color = '#f59e0b';
                position = 'aboveBar';
                shape = 'circle';
                text = '저항';
            } else {
                // 기타 - 보라, 중간, 사각형
                color = '#8b5cf6';
                position = 'inBar';
                shape = 'square';
                text = point.type.toUpperCase();
            }

            return {
                time: point.date,
                position: position,
                color: color,
                shape: shape,
                text: text
            };
        });

        // 차트에 마커 추가
        this.candlestickSeries.setMarkers(markers);

        // AI 분석 요약 표시 (차트 상단에 오버레이)
        this.displayAISummary(summary);
    }

    /**
     * AI 분석 요약 표시
     */
    displayAISummary(summary) {
        if (!summary) return;

        // 기존 요약 제거
        const existingSummary = document.getElementById('ai-chart-summary');
        if (existingSummary) {
            existingSummary.remove();
        }

        // 추세 색상 결정
        let trendColor, trendIcon, trendText;
        if (summary.trend === 'bullish') {
            trendColor = '#ef4444';
            trendIcon = '📈';
            trendText = '상승 추세';
        } else if (summary.trend === 'bearish') {
            trendColor = '#3b82f6';
            trendIcon = '📉';
            trendText = '하락 추세';
        } else {
            trendColor = '#94a3b8';
            trendIcon = '➡️';
            trendText = '중립';
        }

        // 추천 행동
        let recommendText, recommendColor;
        if (summary.recommendation === 'buy') {
            recommendText = '매수 추천';
            recommendColor = '#ef4444';
        } else if (summary.recommendation === 'sell') {
            recommendText = '매도 추천';
            recommendColor = '#3b82f6';
        } else {
            recommendText = '관망';
            recommendColor = '#94a3b8';
        }

        // 요약 HTML 생성
        const summaryHTML = `
            <div id="ai-chart-summary" style="
                position: absolute;
                top: 60px;
                right: 10px;
                background: rgba(30, 33, 57, 0.95);
                border: 1px solid rgba(148, 163, 184, 0.2);
                border-radius: 12px;
                padding: 12px 16px;
                color: var(--text-primary);
                font-size: 13px;
                z-index: 100;
                backdrop-filter: blur(10px);
                min-width: 200px;
            ">
                <div style="font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                    <span style="font-size: 18px;">🤖</span>
                    <span>AI 차트 분석</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: var(--text-muted);">추세:</span>
                        <span style="color: ${trendColor}; font-weight: 600;">
                            ${trendIcon} ${trendText}
                        </span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: var(--text-muted);">강도:</span>
                        <span style="font-weight: 600;">${summary.strength || 'medium'}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: var(--text-muted);">추천:</span>
                        <span style="color: ${recommendColor}; font-weight: 600;">${recommendText}</span>
                    </div>
                    ${summary.key_levels ? `
                    <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(148, 163, 184, 0.1);">
                        <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">주요 가격대</div>
                        <div style="display: flex; justify-content: space-between; font-size: 11px;">
                            <span>지지: ${summary.key_levels.support?.toLocaleString() || '-'}원</span>
                            <span>저항: ${summary.key_levels.resistance?.toLocaleString() || '-'}원</span>
                        </div>
                    </div>
                    ` : ''}
                </div>
            </div>
        `;

        // 차트 컨테이너에 추가
        const chartContainer = document.querySelector(`#${this.containerId}`);
        if (chartContainer) {
            chartContainer.insertAdjacentHTML('beforeend', summaryHTML);
        }
    }
}

// Global instance
let advancedChart = null;

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    advancedChart = new AdvancedTradingChart('main-chart');
    advancedChart.initialize();
    advancedChart.loadData('005930');
});
