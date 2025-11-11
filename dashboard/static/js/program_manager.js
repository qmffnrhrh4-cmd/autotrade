/**
 * Program Manager UI
 * 프로그램 매니저 대시보드 통합
 */

class ProgramManagerUI {
    constructor() {
        this.refreshInterval = null;
        this.init();
    }

    init() {
        console.log('[ProgramManager] Initializing...');
        this.setupEventListeners();
        this.loadStatus();
    }

    setupEventListeners() {
        // 건강 검진 버튼
        const healthCheckBtn = document.getElementById('pm-health-check-btn');
        if (healthCheckBtn) {
            healthCheckBtn.addEventListener('click', () => this.runHealthCheck());
        }

        // 성능 분석 버튼
        const analyzeBtn = document.getElementById('pm-analyze-btn');
        if (analyzeBtn) {
            analyzeBtn.addEventListener('click', () => this.analyzePerformance());
        }

        // 시스템 최적화 버튼
        const optimizeBtn = document.getElementById('pm-optimize-btn');
        if (optimizeBtn) {
            optimizeBtn.addEventListener('click', () => this.optimizeSystem());
        }

        // 보고서 생성 버튼
        const reportBtn = document.getElementById('pm-report-btn');
        if (reportBtn) {
            reportBtn.addEventListener('click', () => this.generateReport());
        }

        // 자동 새로고침 토글
        const autoRefreshToggle = document.getElementById('pm-auto-refresh');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }
    }

    async loadStatus() {
        try {
            const response = await fetch('/api/program-manager/status');
            const data = await response.json();

            if (data.success) {
                this.updateStatusDisplay(data.status);
            } else {
                this.showError('시스템 상태 조회 실패: ' + data.error);
            }
        } catch (error) {
            console.error('[ProgramManager] Status load error:', error);
            this.showError('시스템 상태 조회 중 오류 발생');
        }
    }

    updateStatusDisplay(status) {
        // 시스템 상태 표시
        const statusContainer = document.getElementById('pm-status-container');
        if (!statusContainer) return;

        statusContainer.innerHTML = `
            <div class="grid grid-3 mb-3">
                <div class="stats-card">
                    <div class="stats-label">CPU 사용률</div>
                    <div class="stats-value">${status.cpu_usage || 0}%</div>
                </div>
                <div class="stats-card">
                    <div class="stats-label">메모리 사용률</div>
                    <div class="stats-value">${status.memory_usage || 0}%</div>
                </div>
                <div class="stats-card">
                    <div class="stats-label">가동 시간</div>
                    <div class="stats-value">${status.uptime || 'N/A'}</div>
                </div>
            </div>
            <div class="modern-card">
                <h3>시스템 건강 상태</h3>
                <div class="progress-bar mt-2">
                    <div class="progress-fill" style="width: ${status.health_score || 0}%"></div>
                </div>
                <p class="text-secondary mt-1">건강 점수: ${status.health_score || 0}/100</p>
            </div>
        `;
    }

    async runHealthCheck() {
        const btn = document.getElementById('pm-health-check-btn');
        if (btn) btn.disabled = true;

        try {
            this.showLoading('종합 건강 검진 실행 중...');

            const response = await fetch('/api/program-manager/health-check', {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                this.displayHealthReport(data.report);
                this.showSuccess('건강 검진 완료');
            } else {
                this.showError('건강 검진 실패: ' + data.error);
            }
        } catch (error) {
            console.error('[ProgramManager] Health check error:', error);
            this.showError('건강 검진 중 오류 발생');
        } finally {
            if (btn) btn.disabled = false;
            this.hideLoading();
        }
    }

    displayHealthReport(report) {
        const container = document.getElementById('pm-health-report');
        if (!container) return;

        container.innerHTML = `
            <div class="modern-card">
                <h3>건강 검진 결과</h3>
                <div class="mt-2">
                    <p><strong>전체 점수:</strong> ${report.overall_score || 0}/100</p>
                    <p><strong>상태:</strong> <span class="${report.status === 'healthy' ? 'price-up' : 'price-down'}">${report.status || 'unknown'}</span></p>
                    <h4 class="mt-3">세부 항목</h4>
                    <ul>
                        ${Object.entries(report.checks || {}).map(([key, value]) => `
                            <li>${key}: <span class="${value.passed ? 'price-up' : 'price-down'}">${value.passed ? '✓' : '✗'}</span> ${value.message || ''}</li>
                        `).join('')}
                    </ul>
                    ${report.recommendations && report.recommendations.length > 0 ? `
                        <h4 class="mt-3">권장 사항</h4>
                        <ul>
                            ${report.recommendations.map(r => `<li>${r}</li>`).join('')}
                        </ul>
                    ` : ''}
                </div>
            </div>
        `;
    }

    async analyzePerformance() {
        const btn = document.getElementById('pm-analyze-btn');
        if (btn) btn.disabled = true;

        try {
            this.showLoading('성능 분석 실행 중...');

            const response = await fetch('/api/program-manager/analyze', {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                this.displayPerformanceAnalysis(data.analysis);
                this.showSuccess('성능 분석 완료');
            } else {
                this.showError('성능 분석 실패: ' + data.error);
            }
        } catch (error) {
            console.error('[ProgramManager] Analysis error:', error);
            this.showError('성능 분석 중 오류 발생');
        } finally {
            if (btn) btn.disabled = false;
            this.hideLoading();
        }
    }

    displayPerformanceAnalysis(analysis) {
        const container = document.getElementById('pm-analysis-result');
        if (!container) return;

        container.innerHTML = `
            <div class="modern-card">
                <h3>성능 분석 결과</h3>
                <div class="grid grid-2 mt-2">
                    ${Object.entries(analysis.metrics || {}).map(([key, value]) => `
                        <div class="stats-card">
                            <div class="stats-label">${key}</div>
                            <div class="stats-value">${value}</div>
                        </div>
                    `).join('')}
                </div>
                ${analysis.bottlenecks && analysis.bottlenecks.length > 0 ? `
                    <h4 class="mt-3">병목 지점</h4>
                    <ul>
                        ${analysis.bottlenecks.map(b => `<li class="price-down">${b}</li>`).join('')}
                    </ul>
                ` : ''}
            </div>
        `;
    }

    async optimizeSystem() {
        const btn = document.getElementById('pm-optimize-btn');
        if (btn) btn.disabled = true;

        if (!confirm('시스템 최적화를 실행하시겠습니까? 일부 기능이 일시적으로 중단될 수 있습니다.')) {
            if (btn) btn.disabled = false;
            return;
        }

        try {
            this.showLoading('시스템 최적화 실행 중...');

            const response = await fetch('/api/program-manager/optimize', {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                this.displayOptimizationResult(data.result);
                this.showSuccess('시스템 최적화 완료');
                // 상태 새로고침
                setTimeout(() => this.loadStatus(), 2000);
            } else {
                this.showError('시스템 최적화 실패: ' + data.error);
            }
        } catch (error) {
            console.error('[ProgramManager] Optimization error:', error);
            this.showError('시스템 최적화 중 오류 발생');
        } finally {
            if (btn) btn.disabled = false;
            this.hideLoading();
        }
    }

    displayOptimizationResult(result) {
        const container = document.getElementById('pm-optimization-result');
        if (!container) return;

        container.innerHTML = `
            <div class="modern-card">
                <h3>최적화 결과</h3>
                <div class="mt-2">
                    <p><strong>최적화 항목:</strong> ${result.optimized_items || 0}개</p>
                    <p><strong>성능 개선:</strong> <span class="price-up">+${result.performance_improvement || 0}%</span></p>
                    ${result.actions && result.actions.length > 0 ? `
                        <h4 class="mt-3">실행된 작업</h4>
                        <ul>
                            ${result.actions.map(a => `<li>${a}</li>`).join('')}
                        </ul>
                    ` : ''}
                </div>
            </div>
        `;
    }

    async generateReport() {
        const btn = document.getElementById('pm-report-btn');
        if (btn) btn.disabled = true;

        try {
            this.showLoading('종합 보고서 생성 중...');

            const response = await fetch('/api/program-manager/report');
            const data = await response.json();

            if (data.success) {
                this.displayReport(data.report);
                this.showSuccess('보고서 생성 완료');
            } else {
                this.showError('보고서 생성 실패: ' + data.error);
            }
        } catch (error) {
            console.error('[ProgramManager] Report generation error:', error);
            this.showError('보고서 생성 중 오류 발생');
        } finally {
            if (btn) btn.disabled = false;
            this.hideLoading();
        }
    }

    displayReport(report) {
        const container = document.getElementById('pm-report-container');
        if (!container) return;

        container.innerHTML = `
            <div class="modern-card">
                <h3>종합 보고서</h3>
                <div class="mt-2">
                    <h4>시스템 상태</h4>
                    <p>${report.system_status || 'N/A'}</p>

                    <h4 class="mt-3">성능 지표</h4>
                    <div class="grid grid-3 mt-2">
                        ${Object.entries(report.performance_metrics || {}).map(([key, value]) => `
                            <div class="stats-card">
                                <div class="stats-label">${key}</div>
                                <div class="stats-value">${value}</div>
                            </div>
                        `).join('')}
                    </div>

                    ${report.summary ? `
                        <h4 class="mt-3">요약</h4>
                        <p>${report.summary}</p>
                    ` : ''}
                </div>
            </div>
        `;
    }

    startAutoRefresh() {
        if (this.refreshInterval) return;

        this.refreshInterval = setInterval(() => {
            this.loadStatus();
        }, 30000); // 30초마다 새로고침

        console.log('[ProgramManager] Auto-refresh started');
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
            console.log('[ProgramManager] Auto-refresh stopped');
        }
    }

    showLoading(message) {
        // 로딩 표시 (실제 구현 필요)
        console.log('[ProgramManager] Loading:', message);
    }

    hideLoading() {
        // 로딩 숨기기 (실제 구현 필요)
        console.log('[ProgramManager] Loading hidden');
    }

    showSuccess(message) {
        // 성공 메시지 표시 (실제 구현 필요)
        console.log('[ProgramManager] Success:', message);
        alert(message);
    }

    showError(message) {
        // 오류 메시지 표시 (실제 구현 필요)
        console.error('[ProgramManager] Error:', message);
        alert('오류: ' + message);
    }
}

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', () => {
    // ID는 'program-manager' (tab-content)
    if (document.getElementById('program-manager')) {
        window.programManagerUI = new ProgramManagerUI();
    }
});
