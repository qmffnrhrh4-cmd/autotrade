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
            const response = await fetch('/api/virtual-trading/strategies');
            const data = await response.json();

            if (data.success) {
                this.renderStrategies(data.strategies);

                // 첫 번째 전략 자동 선택
                if (!this.currentStrategy && data.strategies.length > 0) {
                    this.selectStrategy(data.strategies[0].id);
                }
            }
        } catch (error) {
            console.error('Failed to load strategies:', error);
        }
    }

    /**
     * 전략 목록 렌더링
     */
    renderStrategies(strategies) {
        const container = document.getElementById('virtual-strategies-list');
        if (!container) return;

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
                    <span class="badge ${strategy.return_rate >= 0 ? 'badge-success' : 'badge-danger'}">
                        ${strategy.return_rate >= 0 ? '+' : ''}${strategy.return_rate.toFixed(2)}%
                    </span>
                </div>
                <div class="strategy-stats">
                    <div class="stat-item">
                        <span class="stat-label">총 자산</span>
                        <span class="stat-value">${this.formatCurrency(strategy.total_assets)}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">수익</span>
                        <span class="stat-value ${strategy.total_profit >= 0 ? 'text-success' : 'text-danger'}">
                            ${strategy.total_profit >= 0 ? '+' : ''}${this.formatCurrency(strategy.total_profit)}
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
            const response = await fetch(`/api/virtual-trading/strategies/${strategyId}`);
            const data = await response.json();

            if (data.success) {
                this.renderStrategyDetail(data.strategy, data.metrics);
            }
        } catch (error) {
            console.error('Failed to load strategy detail:', error);
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
                <div class="metric-card ${metrics.total_profit >= 0 ? 'profit' : 'loss'}">
                    <div class="metric-label">실현 손익</div>
                    <div class="metric-value">
                        ${metrics.total_profit >= 0 ? '+' : ''}${this.formatCurrency(metrics.total_profit)}
                    </div>
                </div>
                <div class="metric-card ${metrics.unrealized_profit >= 0 ? 'profit' : 'loss'}">
                    <div class="metric-label">미실현 손익</div>
                    <div class="metric-value">
                        ${metrics.unrealized_profit >= 0 ? '+' : ''}${this.formatCurrency(metrics.unrealized_profit)}
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">수익률</div>
                    <div class="metric-value ${metrics.return_rate >= 0 ? 'text-success' : 'text-danger'}">
                        ${metrics.return_rate >= 0 ? '+' : ''}${metrics.return_rate.toFixed(2)}%
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
    showNotification(title, message, type = 'info') {
        // 기존 알림 시스템 사용 또는 커스텀 알림
        if (typeof showToast === 'function') {
            showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${title}: ${message}`);
        }
    }

    /**
     * 통화 포맷
     */
    formatCurrency(amount) {
        return amount.toLocaleString() + '원';
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
        // TODO: 매수 모달 구현
        alert('매수 기능은 곧 추가됩니다');
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
        // TODO: 전략 생성 모달 구현
        alert('전략 생성 기능은 곧 추가됩니다');
    }
}

// 전역 인스턴스 생성
let virtualTrading;

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    virtualTrading = new VirtualTradingManager();
});
