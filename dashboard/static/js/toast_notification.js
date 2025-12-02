/**
 * Toast Notification System
 * 부드러운 애니메이션의 토스트 알림
 */

class ToastNotification {
    constructor() {
        this.container = null;
        this.toasts = [];
        this.maxToasts = 5;
        this.defaultDuration = 4000;
        this.init();
    }

    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 10px;
                pointer-events: none;
            `;
            document.body.appendChild(this.container);
        }
    }

    show(message, type = 'info', duration = this.defaultDuration, options = {}) {
        this.init();

        while (this.toasts.length >= this.maxToasts) {
            this.removeOldest();
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;

        const icons = {
            success: `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>`,
            error: `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>`,
            warning: `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>`,
            info: `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>`
        };

        const colors = {
            success: { bg: 'rgba(16, 185, 129, 0.95)', border: '#10b981' },
            error: { bg: 'rgba(239, 68, 68, 0.95)', border: '#ef4444' },
            warning: { bg: 'rgba(245, 158, 11, 0.95)', border: '#f59e0b' },
            info: { bg: 'rgba(59, 130, 246, 0.95)', border: '#3b82f6' }
        };

        const color = colors[type] || colors.info;

        toast.style.cssText = `
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 16px 20px;
            background: ${color.bg};
            border-left: 4px solid ${color.border};
            border-radius: 8px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            color: white;
            font-size: 14px;
            max-width: 380px;
            min-width: 280px;
            pointer-events: auto;
            transform: translateX(120%);
            opacity: 0;
            transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
            backdrop-filter: blur(10px);
        `;

        const iconHtml = icons[type] || icons.info;

        toast.innerHTML = `
            <div style="flex-shrink: 0; margin-top: 2px;">${iconHtml}</div>
            <div style="flex: 1;">
                ${options.title ? `<div style="font-weight: 600; margin-bottom: 4px;">${options.title}</div>` : ''}
                <div style="line-height: 1.5;">${message}</div>
                ${options.action ? `<button class="toast-action" style="
                    margin-top: 8px;
                    padding: 6px 12px;
                    background: rgba(255,255,255,0.2);
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-size: 12px;
                    cursor: pointer;
                    transition: background 0.2s;
                ">${options.action.text}</button>` : ''}
            </div>
            <button class="toast-close" style="
                background: none;
                border: none;
                color: white;
                opacity: 0.7;
                cursor: pointer;
                padding: 4px;
                margin: -4px;
                transition: opacity 0.2s;
            ">✕</button>
        `;

        const closeBtn = toast.querySelector('.toast-close');
        closeBtn.addEventListener('click', () => this.remove(toast));
        closeBtn.addEventListener('mouseenter', () => closeBtn.style.opacity = '1');
        closeBtn.addEventListener('mouseleave', () => closeBtn.style.opacity = '0.7');

        if (options.action) {
            const actionBtn = toast.querySelector('.toast-action');
            actionBtn.addEventListener('click', () => {
                options.action.callback();
                this.remove(toast);
            });
            actionBtn.addEventListener('mouseenter', () => actionBtn.style.background = 'rgba(255,255,255,0.3)');
            actionBtn.addEventListener('mouseleave', () => actionBtn.style.background = 'rgba(255,255,255,0.2)');
        }

        this.container.appendChild(toast);
        this.toasts.push(toast);

        requestAnimationFrame(() => {
            toast.style.transform = 'translateX(0)';
            toast.style.opacity = '1';
        });

        const progressBar = document.createElement('div');
        progressBar.style.cssText = `
            position: absolute;
            bottom: 0;
            left: 0;
            height: 3px;
            background: rgba(255, 255, 255, 0.5);
            width: 100%;
            transform-origin: left;
            animation: toast-progress ${duration}ms linear forwards;
        `;
        toast.style.position = 'relative';
        toast.style.overflow = 'hidden';
        toast.appendChild(progressBar);

        if (!document.querySelector('#toast-progress-style')) {
            const style = document.createElement('style');
            style.id = 'toast-progress-style';
            style.textContent = `
                @keyframes toast-progress {
                    from { transform: scaleX(1); }
                    to { transform: scaleX(0); }
                }
            `;
            document.head.appendChild(style);
        }

        if (duration > 0) {
            setTimeout(() => this.remove(toast), duration);
        }

        return toast;
    }

    remove(toast) {
        toast.style.transform = 'translateX(120%)';
        toast.style.opacity = '0';

        setTimeout(() => {
            if (toast.parentNode === this.container) {
                this.container.removeChild(toast);
            }
            this.toasts = this.toasts.filter(t => t !== toast);
        }, 400);
    }

    removeOldest() {
        if (this.toasts.length > 0) {
            this.remove(this.toasts[0]);
        }
    }

    success(message, options = {}) {
        return this.show(message, 'success', options.duration || this.defaultDuration, options);
    }

    error(message, options = {}) {
        return this.show(message, 'error', options.duration || 6000, options);
    }

    warning(message, options = {}) {
        return this.show(message, 'warning', options.duration || 5000, options);
    }

    info(message, options = {}) {
        return this.show(message, 'info', options.duration || this.defaultDuration, options);
    }

    buy(stockName, price) {
        return this.success(`${stockName} 매수 완료`, {
            title: '주문 체결',
            duration: 5000,
            action: {
                text: '상세 보기',
                callback: () => window.location.hash = '#orders'
            }
        });
    }

    sell(stockName, profit) {
        const profitText = profit >= 0 ? `+${profit.toFixed(2)}%` : `${profit.toFixed(2)}%`;
        const type = profit >= 0 ? 'success' : 'warning';
        return this.show(`${stockName} 매도 완료 (${profitText})`, type, 5000, {
            title: '주문 체결'
        });
    }

    aiAnalysis(signal, stockName) {
        const signalMap = {
            'buy': { type: 'success', text: '매수 추천' },
            'sell': { type: 'error', text: '매도 추천' },
            'hold': { type: 'info', text: '관망 추천' }
        };
        const config = signalMap[signal] || signalMap['hold'];
        return this.show(`${stockName}: ${config.text}`, config.type, 4000, {
            title: 'AI 분석 완료'
        });
    }

    clearAll() {
        this.toasts.forEach(toast => this.remove(toast));
    }
}

const toast = new ToastNotification();
window.toast = toast;
