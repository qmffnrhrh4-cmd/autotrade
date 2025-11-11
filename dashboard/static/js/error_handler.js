class ErrorHandler {
    constructor() {
        this.errorHistory = [];
        this.maxHistorySize = 50;
    }

    handle(error, context = '', showToUser = true) {
        console.error(`[${context}] Error:`, error);

        this.errorHistory.push({
            error: error,
            context: context,
            timestamp: new Date().toISOString()
        });

        if (this.errorHistory.length > this.maxHistorySize) {
            this.errorHistory.shift();
        }

        if (!showToUser) return;

        let userMessage = '';
        let actionButton = null;

        if (error.name === 'AbortError') {
            userMessage = '요청 시간이 초과되었습니다.';
            actionButton = {
                text: '다시 시도',
                action: () => window.location.reload()
            };
        } else if (error.message?.includes('Network') || error.message?.includes('Failed to fetch')) {
            userMessage = '네트워크 연결을 확인해주세요.';
            actionButton = {
                text: '재연결',
                action: () => this.reconnect()
            };
        } else if (error.status === 401) {
            userMessage = '로그인이 필요합니다.';
            actionButton = {
                text: '로그인',
                action: () => window.location.href = '/login'
            };
        } else if (error.status === 403) {
            userMessage = '접근 권한이 없습니다.';
        } else if (error.status === 404) {
            userMessage = '요청한 리소스를 찾을 수 없습니다.';
        } else if (error.status === 500) {
            userMessage = '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
        } else {
            userMessage = error.message || '오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
        }

        this.showErrorModal(userMessage, actionButton, context);
    }

    showErrorModal(message, actionButton, context) {
        if (typeof modalManager === 'undefined') {
            alert(message);
            return;
        }

        const buttons = [
            {
                text: '닫기',
                class: 'btn',
                action: 'close',
                onclick: () => true
            }
        ];

        if (actionButton) {
            buttons.unshift({
                text: actionButton.text,
                class: 'btn-primary',
                action: 'action',
                onclick: () => {
                    actionButton.action();
                    return true;
                }
            });
        }

        modalManager.show({
            title: '⚠️ 오류 발생',
            content: `
                <div style="margin-bottom: 16px;">
                    <p style="margin: 0; font-size: 16px; line-height: 1.6;">${message}</p>
                </div>
                ${context ? `
                    <div style="background: #f5f5f5; padding: 12px; border-radius: 6px; font-size: 12px; color: #666;">
                        <strong>상세 정보:</strong> ${context}
                    </div>
                ` : ''}
            `,
            buttons: buttons
        });
    }

    reconnect() {
        if (typeof realtimeManager !== 'undefined' && realtimeManager.socket) {
            realtimeManager.socket.connect();
        }

        apiClient.clearCache();

        modalManager.alert('재연결을 시도합니다...', '알림');
    }

    showNetworkError() {
        this.handle(
            new Error('Network connection failed'),
            'Network',
            true
        );
    }

    showTimeoutError() {
        this.handle(
            new Error('Request timeout'),
            'Timeout',
            true
        );
    }

    getErrorHistory() {
        return [...this.errorHistory];
    }

    clearErrorHistory() {
        this.errorHistory = [];
    }
}

const errorHandler = new ErrorHandler();
window.errorHandler = errorHandler;

window.addEventListener('error', (event) => {
    errorHandler.handle(event.error, 'Global Error', false);
});

window.addEventListener('unhandledrejection', (event) => {
    errorHandler.handle(event.reason, 'Unhandled Promise Rejection', false);
});
