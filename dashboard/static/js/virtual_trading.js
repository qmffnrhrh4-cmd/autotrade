/**
 * Virtual Trading - Real-time Updates
 * 가상매매 실시간 비동기 업데이트
 */

class VirtualTradingManager {
    constructor() {
        this.updateInterval = 3000; // 3초마다 업데이트
        this.currentStrategy = null;
        this.isUpdating = false;
        this.socket = null;

        this.init();
    }

    init() {
        console.log('🎮 Virtual Trading Manager initialized');

        // 초기 데이터 로드
        this.loadStrategies();

        // 자동 업데이트 시작
        this.startAutoUpdate();

        // WebSocket 연결
        this.connectWebSocket();

        // 이벤트 리스너 등록
        this.setupEventListeners();
    }

    /**
     * Fetch with timeout (타임아웃 기능이 있는 fetch)
     * @param {string} url - 요청 URL
     * @param {object} options - fetch 옵션
     * @param {number} timeout - 타임아웃 시간 (ms, 기본값: 30000ms)
     */
    async fetchWithTimeout(url, options = {}, timeout = 30000) {
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

    /**
     * WebSocket 연결 (실시간 가격 업데이트)
     */
    connectWebSocket() {
        if (typeof io === 'undefined') {
            console.warn('⚠️ Socket.IO not loaded, using polling only');
            return;
        }

        try {
            this.socket = io();

            this.socket.on('connect', () => {
                console.log('✅ WebSocket connected for virtual trading');
            });

            // 실시간 가격 업데이트
            this.socket.on('price_update', (data) => {
                this.handlePriceUpdate(data);
            });

            // 실시간 거래 알림
            this.socket.on('virtual_trade_executed', (data) => {
                this.showTradeNotification(data);
                this.loadPositions();
                this.loadTradeHistory();
            });

        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
        }
    }

    /**
     * 자동 업데이트 시작
     */
    startAutoUpdate() {
        // 전략 목록 자동 업데이트
        setInterval(() => {
            if (!this.isUpdating) {
                this.loadStrategies();
            }
        }, this.updateInterval);

        // 포지션 자동 업데이트
        setInterval(() => {
            if (!this.isUpdating && this.currentStrategy) {
                this.loadPositions();
            }
        }, this.updateInterval);

        // 거래 내역 자동 업데이트
        setInterval(() => {
            if (!this.isUpdating && this.currentStrategy) {
                this.loadTradeHistory();
            }
        }, this.updateInterval * 2); // 6초마다

        // 자동 손절/익절 체크 (백그라운드)
        setInterval(() => {
            this.checkStopLossTakeProfit();
        }, 5000); // 5초마다
    }

    /**
     * 전략 목록 로드
     */
    async loadStrategies() {
        try {
            const response = await this.fetchWithTimeout('/api/virtual-trading/strategies');
            const data = await response.json();

            if (data.success) {
                // Fix: strategies가 배열인지 확인
                let strategies = data.strategies;

                // strategies가 배열이 아니면 빈 배열로 설정
                if (!Array.isArray(strategies)) {
                    console.warn('⚠️ strategies is not an array:', strategies);
                    strategies = [];
                }

                this.renderStrategies(strategies);

                // 첫 번째 전략 자동 선택
                if (!this.currentStrategy && strategies.length > 0) {
                    this.selectStrategy(strategies[0].id);
                }
            }
        } catch (error) {
            console.error('전략 로드 실패:', error);
        }
    }

    /**
     * 전략 목록 렌더링
     */
    renderStrategies(strategies) {
        const container = document.getElementById('virtual-strategies-list');
        if (!container) return;

        // Fix: 스크롤 위치 저장
        const scrollTop = container.scrollTop;

        if (strategies.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-flask"></i>
                    <p>가상매매 전략이 없습니다</p>
                    <button class="btn-primary" onclick="virtualTrading.showCreateStrategyModal()">
                        전략 생성
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = strategies.map(strategy => `
            <div class="strategy-card ${this.currentStrategy === strategy.id ? 'active' : ''}"
                 onclick="virtualTrading.selectStrategy(${strategy.id})">
                <div class="strategy-header">
                    <h3>${strategy.name}</h3>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span class="badge ${strategy.return_rate >= 0 ? 'badge-success' : 'badge-danger'}">
                            ${strategy.return_rate >= 0 ? '+' : ''}${strategy.return_rate.toFixed(2)}%
                        </span>
                        <button
                            class="btn-small btn-danger"
                            onclick="event.stopPropagation(); virtualTrading.deleteStrategy(${strategy.id}, '${strategy.name}')"
                            title="전략 삭제"
                            style="padding: 4px 8px; font-size: 11px;">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="strategy-stats">
                    <div class="stat-item">
                        <span class="stat-label">총 자산</span>
                        <span class="stat-value">${this.formatCurrency(strategy.total_assets)}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">수익</span>
                        <span class="stat-value ${Number(strategy.total_profit) >= 0 ? 'text-success' : 'text-danger'}">
                            ${this.formatCurrencyWithSign(strategy.total_profit)}
                        </span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">승률</span>
                        <span class="stat-value">${strategy.win_rate.toFixed(1)}%</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">거래</span>
                        <span class="stat-value">${strategy.trade_count}회</span>
                    </div>
                </div>
                <div class="strategy-description">
                    ${strategy.description || '전략 설명 없음'}
                </div>
            </div>
        `).join('');

        // Fix: 스크롤 위치 복원 (다음 프레임에서 실행)
        requestAnimationFrame(() => {
            container.scrollTop = scrollTop;
        });
    }

    /**
     * 전략 선택
     */
    async selectStrategy(strategyId) {
        this.currentStrategy = strategyId;

        // 전략 상세 정보 로드
        await this.loadStrategyDetail(strategyId);

        // 포지션 및 거래 내역 로드
        this.loadPositions();
        this.loadTradeHistory();

        // UI 업데이트
        this.renderStrategies([]);
        this.loadStrategies();
    }

    /**
     * 전략 상세 정보 로드
     */
    async loadStrategyDetail(strategyId) {
        try {
            const response = await this.fetchWithTimeout(`/api/virtual-trading/strategies/${strategyId}`);
            const data = await response.json();

            if (data.success) {
                this.renderStrategyDetail(data.strategy, data.metrics);
            }
        } catch (error) {
            console.error('전략 상세 로드 실패:', error);
        }
    }

    /**
     * 전략 상세 정보 렌더링
     */
    renderStrategyDetail(strategy, metrics) {
        const container = document.getElementById('virtual-strategy-detail');
        if (!container) return;

        container.innerHTML = `
            <div class="strategy-detail-header">
                <h2>${strategy.name}</h2>
                <div class="strategy-actions">
                    <button class="btn-primary" onclick="virtualTrading.showBuyModal()">
                        <i class="fas fa-plus"></i> 매수
                    </button>
                </div>
            </div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">총 자산</div>
                    <div class="metric-value">${this.formatCurrency(metrics.total_assets)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">현금</div>
                    <div class="metric-value">${this.formatCurrency(metrics.current_capital)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">주식 평가액</div>
                    <div class="metric-value">${this.formatCurrency(metrics.position_value)}</div>
                </div>
                <div class="metric-card ${Number(metrics.total_profit) >= 0 ? 'profit' : 'loss'}">
                    <div class="metric-label">실현 손익</div>
                    <div class="metric-value">
                        ${this.formatCurrencyWithSign(metrics.total_profit)}
                    </div>
                </div>
                <div class="metric-card ${Number(metrics.unrealized_profit) >= 0 ? 'profit' : 'loss'}">
                    <div class="metric-label">미실현 손익</div>
                    <div class="metric-value">
                        ${this.formatCurrencyWithSign(metrics.unrealized_profit)}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">수익률</div>
                    <div class="metric-value ${Number(metrics.return_rate) >= 0 ? 'text-success' : 'text-danger'}">
                        ${Number(metrics.return_rate) >= 0 ? '+' : ''}${Number(metrics.return_rate || 0).toFixed(2)}%
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">승률</div>
                    <div class="metric-value">${metrics.win_rate.toFixed(1)}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">거래 횟수</div>
                    <div class="metric-value">${metrics.trade_count}회</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">승</div>
                    <div class="metric-value text-success">${metrics.win_count}회</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">패</div>
                    <div class="metric-value text-danger">${metrics.loss_count}회</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">보유 종목</div>
                    <div class="metric-value">${metrics.position_count}개</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">최대 손실 (MDD)</div>
                    <div class="metric-value text-danger">${metrics.max_drawdown.toFixed(2)}%</div>
                </div>
            </div>
        `;
    }

    /**
     * 포지션 목록 로드
     */
    async loadPositions() {
        if (!this.currentStrategy) return;

        try {
            const response = await fetch(`/api/virtual-trading/positions?strategy_id=${this.currentStrategy}`);
            const data = await response.json();

            if (data.success) {
                this.renderPositions(data.positions);
            }
        } catch (error) {
            console.error('Failed to load positions:', error);
        }
    }

    /**
     * 포지션 목록 렌더링
     */
    renderPositions(positions) {
        const tbody = document.querySelector('#virtual-positions-table tbody');
        if (!tbody) return;

        if (positions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center">보유 포지션이 없습니다</td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = positions.map(pos => {
            const profitClass = pos.profit >= 0 ? 'text-success' : 'text-danger';
            const profitSign = pos.profit >= 0 ? '+' : '';

            return `
                <tr class="position-row ${pos.profit >= 0 ? 'profit' : 'loss'}">
                    <td>${pos.stock_code}</td>
                    <td>${pos.stock_name}</td>
                    <td class="text-right">${pos.quantity.toLocaleString()}</td>
                    <td class="text-right">${pos.avg_price.toLocaleString()}</td>
                    <td class="text-right">${pos.current_price.toLocaleString()}</td>
                    <td class="text-right">${pos.value.toLocaleString()}</td>
                    <td class="text-right ${profitClass}">
                        ${profitSign}${pos.profit.toLocaleString()}
                    </td>
                    <td class="text-right ${profitClass}">
                        ${profitSign}${pos.profit_percent.toFixed(2)}%
                    </td>
                    <td class="text-right">
                        ${pos.stop_loss_price ? pos.stop_loss_price.toLocaleString() : '-'}
                    </td>
                    <td class="text-right">
                        ${pos.take_profit_price ? pos.take_profit_price.toLocaleString() : '-'}
                    </td>
                    <td>
                        <button class="btn-small btn-danger"
                                onclick="virtualTrading.sellPosition(${pos.id}, '${pos.stock_name}')">
                            매도
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    /**
     * 거래 내역 로드
     */
    async loadTradeHistory() {
        if (!this.currentStrategy) return;

        try {
            const response = await fetch(`/api/virtual-trading/trades?strategy_id=${this.currentStrategy}&limit=50`);
            const data = await response.json();

            if (data.success) {
                this.renderTradeHistory(data.trades);
            }
        } catch (error) {
            console.error('Failed to load trade history:', error);
        }
    }

    /**
     * 거래 내역 렌더링
     */
    renderTradeHistory(trades) {
        const tbody = document.querySelector('#virtual-trades-table tbody');
        if (!tbody) return;

        if (trades.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="text-center">거래 내역이 없습니다</td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = trades.map(trade => {
            const isBuy = trade.side === 'buy';
            const sideClass = isBuy ? 'buy' : 'sell';
            const sideText = isBuy ? '매수' : '매도';
            const profitClass = trade.profit >= 0 ? 'text-success' : 'text-danger';
            const profitSign = trade.profit >= 0 ? '+' : '';

            return `
                <tr>
                    <td>${trade.timestamp}</td>
                    <td><span class="badge badge-${sideClass}">${sideText}</span></td>
                    <td>${trade.stock_code}</td>
                    <td>${trade.stock_name}</td>
                    <td class="text-right">${trade.quantity.toLocaleString()}</td>
                    <td class="text-right">${trade.price.toLocaleString()}</td>
                    <td class="text-right">${trade.total_amount.toLocaleString()}</td>
                    <td class="text-right ${profitClass}">
                        ${isBuy ? '-' : `${profitSign}${trade.profit.toLocaleString()} (${profitSign}${trade.profit_percent.toFixed(2)}%)`}
                    </td>
                </tr>
            `;
        }).join('');
    }

    /**
     * 자동 손절/익절 체크
     */
    async checkStopLossTakeProfit() {
        try {
            const response = await fetch('/api/virtual-trading/check-conditions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success && data.executed_orders.length > 0) {
                console.log(`🎯 자동 매도 실행: ${data.executed_orders.length}건`);

                // 자동 매도된 종목 알림
                data.executed_orders.forEach(order => {
                    const type = order.type === 'stop_loss' ? '손절' : '익절';
                    this.showNotification(
                        `${type} 실행`,
                        `${order.stock_name}: ${this.formatCurrency(order.profit)}`,
                        order.profit >= 0 ? 'success' : 'danger'
                    );
                });

                // 포지션 및 거래 내역 새로고침
                this.loadPositions();
                this.loadTradeHistory();
                this.loadStrategyDetail(this.currentStrategy);
            }
        } catch (error) {
            console.error('Failed to check stop loss/take profit:', error);
        }
    }

    /**
     * 실시간 가격 업데이트 처리
     */
    handlePriceUpdate(data) {
        // 포지션 테이블의 현재가 업데이트
        const rows = document.querySelectorAll('.position-row');
        rows.forEach(row => {
            const code = row.querySelector('td:first-child').textContent;
            if (data[code]) {
                const currentPriceCell = row.querySelector('td:nth-child(5)');
                if (currentPriceCell) {
                    currentPriceCell.textContent = data[code].toLocaleString();
                    currentPriceCell.classList.add('price-update-flash');
                    setTimeout(() => {
                        currentPriceCell.classList.remove('price-update-flash');
                    }, 500);
                }
            }
        });
    }

    /**
     * 거래 알림 표시
     */
    showTradeNotification(trade) {
        const type = trade.side === 'buy' ? '매수' : '매도';
        const message = `${trade.stock_name} ${trade.quantity}주 ${type} @ ${trade.price.toLocaleString()}원`;
        this.showNotification(`가상매매 ${type}`, message, 'info');
    }

    /**
     * 알림 표시
     */
    showNotification(title, message, type = 'info', duration = 5000) {
        // 기존 알림 시스템 사용 또는 커스텀 알림
        if (typeof showToast === 'function') {
            showToast(message, type);
        } else if (typeof Toastify !== 'undefined') {
            Toastify({
                text: `${title}\n${message}`,
                duration: duration,
                gravity: "top",
                position: "right",
                backgroundColor: type === 'success' ? '#10b981' : type === 'danger' ? '#ef4444' : '#3b82f6',
                stopOnFocus: true
            }).showToast();
        } else {
            // Fallback to alert
            alert(`${title}\n\n${message}`);
        }
    }

    /**
     * 통화 포맷
     */
    formatCurrency(amount) {
        const num = Number(amount) || 0;
        return num.toLocaleString() + '원';
    }

    /**
     * 부호 포함 통화 포맷 (수익/손실 표시용)
     */
    formatCurrencyWithSign(amount) {
        const num = Number(amount) || 0;
        const sign = num >= 0 ? '+' : '';
        return sign + num.toLocaleString() + '원';
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        // Tab 활성화 시 데이터 새로고침
        const virtualTradingTab = document.querySelector('[data-tab="virtual-trading"]');
        if (virtualTradingTab) {
            virtualTradingTab.addEventListener('click', () => {
                this.loadStrategies();
                if (this.currentStrategy) {
                    this.loadStrategyDetail(this.currentStrategy);
                    this.loadPositions();
                    this.loadTradeHistory();
                }
            });
        }
    }

    /**
     * 매수 모달 표시
     */
    showBuyModal() {
        if (!this.currentStrategy) {
            alert('먼저 전략을 선택하세요');
            return;
        }

        const stockCode = prompt('종목코드를 입력하세요 (예: 005930):');
        if (!stockCode) return;

        const stockName = prompt('종목명을 입력하세요 (예: 삼성전자):');
        if (!stockName) return;

        const quantity = parseInt(prompt('매수 수량을 입력하세요:'));
        if (!quantity || quantity <= 0) {
            alert('유효한 수량을 입력하세요');
            return;
        }

        const price = parseInt(prompt('매수 가격을 입력하세요 (현재가):'));
        if (!price || price <= 0) {
            alert('유효한 가격을 입력하세요');
            return;
        }

        const stopLoss = parseFloat(prompt('손절 비율을 입력하세요 (예: 5 = -5%) [선택사항]:') || 0);
        const takeProfit = parseFloat(prompt('익절 비율을 입력하세요 (예: 10 = +10%) [선택사항]:') || 0);

        this.executeBuy(stockCode, stockName, quantity, price, stopLoss, takeProfit);
    }

    /**
     * 매수 주문 실행
     */
    async executeBuy(stockCode, stockName, quantity, price, stopLossPercent, takeProfitPercent) {
        try {
            const response = await fetch('/api/virtual-trading/buy', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    strategy_id: this.currentStrategy,
                    stock_code: stockCode,
                    stock_name: stockName,
                    quantity: quantity,
                    price: price,
                    stop_loss_percent: stopLossPercent || null,
                    take_profit_percent: takeProfitPercent || null
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('매수 완료', data.message, 'success');
                this.loadPositions();
                this.loadTradeHistory();
                this.loadStrategyDetail(this.currentStrategy);
            } else {
                this.showNotification('매수 실패', data.error, 'danger');
            }
        } catch (error) {
            console.error('Failed to execute buy:', error);
            this.showNotification('매수 실패', error.message, 'danger');
        }
    }

    /**
     * 포지션 매도
     */
    async sellPosition(positionId, stockName) {
        if (!confirm(`${stockName}을(를) 매도하시겠습니까?`)) {
            return;
        }

        try {
            // 현재가 가져오기 (간단히 현재 표시된 가격 사용)
            const row = event.target.closest('tr');
            const currentPrice = parseInt(row.querySelector('td:nth-child(5)').textContent.replace(/,/g, ''));

            const response = await fetch('/api/virtual-trading/sell', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    position_id: positionId,
                    sell_price: currentPrice,
                    reason: 'manual'
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('매도 완료', data.message, 'success');
                this.loadPositions();
                this.loadTradeHistory();
                this.loadStrategyDetail(this.currentStrategy);
            } else {
                this.showNotification('매도 실패', data.error, 'danger');
            }
        } catch (error) {
            console.error('Failed to sell position:', error);
            this.showNotification('매도 실패', error.message, 'danger');
        }
    }

    /**
     * 전략 생성 모달 표시
     */
    showCreateStrategyModal() {
        const name = prompt('전략 이름을 입력하세요:');
        if (!name) return;

        const description = prompt('전략 설명을 입력하세요 (선택사항):') || '';
        const initialCapital = parseInt(prompt('초기 자본금을 입력하세요 (기본: 10,000,000원):', '10000000'));

        if (!initialCapital || initialCapital <= 0) {
            alert('유효한 자본금을 입력하세요');
            return;
        }

        this.createStrategy(name, description, initialCapital);
    }

    /**
     * 전략 생성
     */
    async createStrategy(name, description, initialCapital) {
        try {
            const response = await fetch('/api/virtual-trading/strategies', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: name,
                    description: description,
                    initial_capital: initialCapital
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('전략 생성', data.message, 'success');
                this.loadStrategies();
            } else {
                this.showNotification('전략 생성 실패', data.error, 'danger');
            }
        } catch (error) {
            console.error('Failed to create strategy:', error);
            this.showNotification('전략 생성 실패', error.message, 'danger');
        }
    }

    /**
     * 전략 삭제
     */
    async deleteStrategy(strategyId, strategyName) {
        if (!confirm(`"${strategyName}" 전략을 삭제하시겠습니까?\n\n⚠️ 이 작업은 되돌릴 수 없습니다.\n(활성 포지션이 있는 경우 삭제할 수 없습니다)`)) {
            return;
        }

        try {
            const response = await this.fetchWithTimeout(`/api/virtual-trading/strategies/${strategyId}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('전략 삭제 완료', data.message, 'success');

                // 현재 선택된 전략이 삭제된 경우 초기화
                if (this.currentStrategy === strategyId) {
                    this.currentStrategy = null;
                }

                // 전략 목록 새로고침
                this.loadStrategies();
            } else {
                this.showNotification('전략 삭제 실패', data.error, 'danger');
            }
        } catch (error) {
            console.error('Failed to delete strategy:', error);
            this.showNotification('전략 삭제 실패', error.message, 'danger');
        }
    }

    /**
     * 백테스팅 실행
     */
    showBacktestModal() {
        if (!this.currentStrategy) {
            alert('먼저 전략을 선택하세요');
            return;
        }

        const stockCode = prompt('백테스팅 종목코드 (예: 005930):');
        if (!stockCode) return;

        const startDate = prompt('시작일 (예: 20240101):');
        if (!startDate) return;

        const endDate = prompt('종료일 (예: 20241101):');
        if (!endDate) return;

        this.runBacktest(stockCode, startDate, endDate);
    }

    /**
     * 백테스팅 실행
     */
    async runBacktest(stockCode, startDate, endDate) {
        try {
            this.showNotification('백테스팅 시작', '데이터 분석 중...', 'info');

            const response = await fetch('/api/virtual-trading/backtest', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    strategy_id: this.currentStrategy,
                    stock_code: stockCode,
                    start_date: startDate,
                    end_date: endDate,
                    stop_loss_percents: [3.0, 5.0, 7.0],
                    take_profit_percents: [5.0, 10.0, 15.0]
                })
            });

            const data = await response.json();

            if (data.success) {
                const result = data.result;
                const best = result.best_result;

                const message = `
최적 조건: 손절 ${best.stop_loss_percent}%, 익절 ${best.take_profit_percent}%
기대 수익률: ${best.return_rate.toFixed(2)}%
기대 승률: ${best.win_rate.toFixed(1)}%
거래 횟수: ${best.trade_count}회 (승: ${best.win_count}, 패: ${best.loss_count})

이 조건을 적용하시겠습니까?
                `;

                if (confirm(message)) {
                    this.applyBacktestResult(data.result);
                }
            } else {
                this.showNotification('백테스팅 실패', data.error, 'danger');
            }
        } catch (error) {
            console.error('Failed to run backtest:', error);
            this.showNotification('백테스팅 실패', error.message, 'danger');
        }
    }

    /**
     * 백테스팅 결과 적용
     */
    async applyBacktestResult(backtestResult) {
        try {
            const response = await fetch('/api/virtual-trading/backtest/apply', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    strategy_id: this.currentStrategy,
                    backtest_result: backtestResult
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('조건 적용 완료', data.message, 'success');
            } else {
                this.showNotification('조건 적용 실패', data.error, 'danger');
            }
        } catch (error) {
            console.error('Failed to apply backtest result:', error);
            this.showNotification('조건 적용 실패', error.message, 'danger');
        }
    }

    // ============================================================
    // AI 자동 전략 관리 기능
    // ============================================================

    /**
     * AI 5가지 전략 자동 생성
     */
    async aiInitializeStrategies() {
        if (!confirm('AI가 5가지 전략을 자동으로 생성합니다. 계속하시겠습니까?')) {
            return;
        }

        try {
            this.showNotification('AI 전략 생성', '5가지 AI 전략을 생성하는 중...', 'info');

            const response = await this.fetchWithTimeout('/api/virtual-trading/ai/initialize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    initial_capital: 10000000  // 1000만원
                })
            }, 30000); // 30초 타임아웃

            const data = await response.json();

            if (data.success) {
                // Fix: 성공 메시지를 먼저 표시
                this.showNotification(
                    '✅ AI 전략 생성 완료!',
                    `${data.strategy_ids ? data.strategy_ids.length : 5}가지 AI 전략이 생성되었습니다.\n\n아래 목록에서 확인하세요:\n- AI-보수형\n- AI-균형형\n- AI-공격형\n- AI-가치형\n- AI-혁신형`,
                    'success',
                    8000
                );

                // Fix: 데이터베이스 커밋을 위한 짧은 대기 후 여러 번 새로고침
                await new Promise(resolve => setTimeout(resolve, 500));
                await this.loadStrategies();

                // Fix: 추가 새로고침으로 확실하게 로드 (1초 후)
                setTimeout(async () => {
                    await this.loadStrategies();

                    // 전략 목록 섹션으로 스크롤
                    const strategyListContainer = document.getElementById('virtual-strategies-list');
                    if (strategyListContainer) {
                        strategyListContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                        // 하이라이트 효과
                        strategyListContainer.style.animation = 'highlight-pulse 2s ease-in-out';
                        setTimeout(() => {
                            strategyListContainer.style.animation = '';
                        }, 2000);
                    }
                }, 1000);

                // Fix: 최종 새로고침 (2초 후) - 확실하게!
                setTimeout(() => {
                    this.loadStrategies();
                    console.log('✅ AI 전략 최종 로드 완료');
                }, 2000);
            } else {
                this.showNotification('AI 전략 생성 실패', data.error || '알 수 없는 오류가 발생했습니다', 'danger');
                console.error('AI strategy creation failed:', data);
            }
        } catch (error) {
            console.error('Failed to initialize AI strategies:', error);
            this.showNotification('AI 전략 생성 실패', error.message, 'danger');
        }
    }

    /**
     * AI 전략 성과 자동 검토
     */
    async aiReviewStrategies() {
        try {
            this.showNotification('AI 검토 시작', '전략 성과를 분석하는 중...', 'info');

            const response = await this.fetchWithTimeout('/api/virtual-trading/ai/review', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.displayAIReviewResult(data.result);
                this.showNotification('AI 검토 완료', '전략 성과 분석이 완료되었습니다', 'success');
            } else {
                this.showNotification('AI 검토 실패', data.error, 'danger');
            }
        } catch (error) {
            console.error('Failed to review strategies:', error);
            this.showNotification('AI 검토 실패', error.message, 'danger');
        }
    }

    /**
     * AI 전략 자동 개선
     */
    async aiImproveStrategies() {
        if (!confirm('AI가 전략을 자동으로 개선합니다. 백테스팅이 실행되며 시간이 걸릴 수 있습니다.')) {
            return;
        }

        try {
            this.showNotification('AI 개선 시작', '전략을 개선하는 중...', 'info');

            const response = await this.fetchWithTimeout('/api/virtual-trading/ai/improve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    backtest_period_days: 90
                })
            });

            const data = await response.json();

            if (data.success) {
                this.displayAIImprovementResult(data.result);
                this.showNotification(
                    'AI 개선 완료',
                    `${data.result.improved_count}개 전략이 개선되었습니다`,
                    'success'
                );
            } else {
                this.showNotification('AI 개선 실패', data.error, 'danger');
            }
        } catch (error) {
            console.error('Failed to improve strategies:', error);
            this.showNotification('AI 개선 실패', error.message, 'danger');
        }
    }

    /**
     * AI 자동 관리 (검토 → 개선 → 추천)
     */
    async aiAutoManage() {
        if (!confirm('AI가 전략을 자동으로 관리합니다 (검토 → 개선 → 최고 전략 추천). 계속하시겠습니까?')) {
            return;
        }

        try {
            this.showNotification('AI 자동 관리', '전략을 분석하고 개선하는 중...', 'info');

            const response = await this.fetchWithTimeout('/api/virtual-trading/ai/auto-manage', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.displayAIManageResult(data.result);
                this.showNotification('AI 자동 관리 완료', '전략 관리가 완료되었습니다', 'success');
            } else {
                this.showNotification('AI 자동 관리 실패', data.error, 'danger');
            }
        } catch (error) {
            console.error('Failed to auto-manage:', error);
            this.showNotification('AI 자동 관리 실패', error.message, 'danger');
        }
    }

    /**
     * AI 검토 결과 표시
     */
    displayAIReviewResult(result) {
        const container = document.getElementById('ai-review-result');
        if (!container) {
            console.warn('AI review result container not found');
            return;
        }

        const reviews = result.reviews || [];
        const summary = result.summary || {};

        let html = `
            <div class="ai-result-panel">
                <h3><i class="fas fa-brain"></i> AI 전략 검토 결과</h3>
                <div class="ai-summary">
                    <div class="summary-item">
                        <span>평가 전략 수:</span>
                        <span>${summary.total_strategies || 0}개</span>
                    </div>
                    <div class="summary-item">
                        <span>평균 점수:</span>
                        <span>${(summary.average_score || 0).toFixed(1)}점</span>
                    </div>
                    <div class="summary-item">
                        <span>최고 전략:</span>
                        <span>${summary.best_strategy?.name || '-'} (${summary.best_strategy?.grade || '-'}등급)</span>
                    </div>
                </div>
                <div class="ai-reviews">
        `;

        reviews.forEach(review => {
            const eval_data = review.evaluation;
            const grade_class = eval_data.grade === 'S' ? 'grade-s' :
                              eval_data.grade === 'A' ? 'grade-a' :
                              eval_data.grade === 'B' ? 'grade-b' :
                              eval_data.grade === 'C' ? 'grade-c' : 'grade-d';

            html += `
                <div class="review-card ${grade_class}">
                    <div class="review-header">
                        <h4>${review.name}</h4>
                        <span class="grade-badge ${grade_class}">${eval_data.grade}등급</span>
                    </div>
                    <div class="review-score">점수: ${eval_data.score.toFixed(0)}점</div>
                    <div class="review-recommendation">${eval_data.recommendation}</div>
                    <div class="review-details">
                        <div><strong>강점:</strong> ${eval_data.strengths.join(', ')}</div>
                        <div><strong>약점:</strong> ${eval_data.weaknesses.join(', ')}</div>
                    </div>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;

        container.innerHTML = html;
        container.style.display = 'block';
    }

    /**
     * AI 개선 결과 표시
     */
    displayAIImprovementResult(result) {
        const container = document.getElementById('ai-improvement-result');
        if (!container) {
            console.warn('AI improvement result container not found');
            return;
        }

        const improvements = result.improvements || [];

        let html = `
            <div class="ai-result-panel">
                <h3><i class="fas fa-magic"></i> AI 전략 개선 결과</h3>
                <p>개선된 전략 수: ${result.improved_count}개</p>
        `;

        if (improvements.length > 0) {
            html += '<div class="improvements-list">';
            improvements.forEach(imp => {
                html += `
                    <div class="improvement-card">
                        <h4>${imp.name}</h4>
                        <div class="improvement-details">
                            <div>현재 수익률: ${imp.before_return.toFixed(2)}%</div>
                            <div>예상 개선: ${imp.expected_improvement.toFixed(2)}%</div>
                            <div>최적 조건: 손절 ${imp.optimal_conditions.stop_loss}%, 익절 ${imp.optimal_conditions.take_profit}%</div>
                            <div>테스트 종목: ${imp.tested_stock}</div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        } else {
            html += '<p>개선이 필요한 전략이 없습니다.</p>';
        }

        html += '</div>';

        container.innerHTML = html;
        container.style.display = 'block';
    }

    /**
     * AI 자동 관리 결과 표시
     */
    displayAIManageResult(result) {
        // 검토 결과 표시
        if (result.review) {
            this.displayAIReviewResult(result.review);
        }

        // 개선 결과 표시
        if (result.improvement) {
            this.displayAIImprovementResult(result.improvement);
        }

        // 추천 전략 표시
        const recommended = result.recommended_for_real_trading;
        if (recommended) {
            this.showNotification(
                '🏆 실제 매매 추천 전략',
                `${recommended.name} (${recommended.evaluation.grade}등급, ${recommended.evaluation.score.toFixed(0)}점)`,
                'success',
                8000
            );
        }
    }
}

// 전역 인스턴스 생성
let virtualTrading;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    virtualTrading = new VirtualTradingManager();
});
