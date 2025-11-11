class LoadingStateManager {
    constructor() {
        this.loadingStates = new Map();
        this.setupGlobalStyles();
    }

    setupGlobalStyles() {
        if (document.getElementById('loading-manager-styles')) return;

        const style = document.createElement('style');
        style.id = 'loading-manager-styles';
        style.textContent = `
            .loading-container {
                position: relative;
                min-height: 100px;
            }

            .loading-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.9);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                z-index: 1000;
                opacity: 0;
                transition: opacity 0.3s ease;
            }

            .loading-overlay.show {
                opacity: 1;
            }

            .loading-spinner {
                width: 40px;
                height: 40px;
                border: 4px solid #f3f3f3;
                border-top: 4px solid #4CAF50;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            .loading-message {
                margin-top: 16px;
                font-size: 14px;
                color: #666;
            }

            .progress-bar {
                width: 200px;
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
                overflow: hidden;
                margin-top: 16px;
            }

            .progress-fill {
                height: 100%;
                background: #4CAF50;
                transition: width 0.3s ease;
            }

            .skeleton {
                background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
                background-size: 200% 100%;
                animation: loading 1.5s ease-in-out infinite;
                border-radius: 4px;
            }

            @keyframes loading {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }

            .skeleton-title {
                height: 24px;
                margin-bottom: 16px;
            }

            .skeleton-text {
                height: 16px;
                margin-bottom: 8px;
            }

            .skeleton-chart {
                height: 300px;
                margin: 16px 0;
            }

            .checkmark-animation {
                width: 60px;
                height: 60px;
                border-radius: 50%;
                display: block;
                stroke-width: 2;
                stroke: #4CAF50;
                stroke-miterlimit: 10;
                box-shadow: inset 0px 0px 0px #4CAF50;
                animation: fill 0.4s ease-in-out 0.4s forwards, scale 0.3s ease-in-out 0.9s both;
            }

            @keyframes fill {
                100% { box-shadow: inset 0px 0px 0px 30px #4CAF50; }
            }

            @keyframes scale {
                0%, 100% { transform: none; }
                50% { transform: scale3d(1.1, 1.1, 1); }
            }
        `;
        document.head.appendChild(style);
    }

    startLoading(containerId, message = '로딩 중...') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Container ${containerId} not found`);
            return;
        }

        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner"></div>
            <div class="loading-message">${message}</div>
        `;

        container.style.position = 'relative';
        container.appendChild(overlay);

        setTimeout(() => overlay.classList.add('show'), 10);

        this.loadingStates.set(containerId, {
            overlay: overlay,
            startTime: Date.now(),
            message: message
        });
    }

    updateProgress(containerId, percent) {
        const state = this.loadingStates.get(containerId);
        if (!state) return;

        let progressBar = state.overlay.querySelector('.progress-bar');

        if (!progressBar) {
            progressBar = document.createElement('div');
            progressBar.className = 'progress-bar';
            progressBar.innerHTML = '<div class="progress-fill" style="width: 0%"></div>';
            state.overlay.appendChild(progressBar);
        }

        const fill = progressBar.querySelector('.progress-fill');
        fill.style.width = `${Math.min(Math.max(percent, 0), 100)}%`;
    }

    finishLoading(containerId, showSuccess = false) {
        const state = this.loadingStates.get(containerId);
        if (!state) return;

        if (showSuccess) {
            state.overlay.innerHTML = `
                <svg class="checkmark-animation" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                    <circle cx="26" cy="26" r="25" fill="none"/>
                    <path fill="none" stroke="#4CAF50" stroke-width="2" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
                </svg>
            `;

            setTimeout(() => {
                this._removeOverlay(containerId);
            }, 1200);
        } else {
            this._removeOverlay(containerId);
        }
    }

    _removeOverlay(containerId) {
        const state = this.loadingStates.get(containerId);
        if (!state) return;

        state.overlay.classList.remove('show');

        setTimeout(() => {
            state.overlay.remove();
            this.loadingStates.delete(containerId);
        }, 300);
    }

    showSkeleton(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = `
            <div class="skeleton skeleton-title" style="width: 40%"></div>
            <div class="skeleton skeleton-text" style="width: 80%"></div>
            <div class="skeleton skeleton-text" style="width: 60%"></div>
            <div class="skeleton skeleton-chart"></div>
            <div class="skeleton skeleton-text" style="width: 90%"></div>
            <div class="skeleton skeleton-text" style="width: 70%"></div>
        `;
    }

    isLoading(containerId) {
        return this.loadingStates.has(containerId);
    }
}

const loadingManager = new LoadingStateManager();
window.loadingManager = loadingManager;
