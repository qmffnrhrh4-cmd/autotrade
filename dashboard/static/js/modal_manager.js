class ModalManager {
    constructor() {
        this.modals = new Map();
        this.setupGlobalStyles();
    }

    setupGlobalStyles() {
        if (document.getElementById('modal-manager-styles')) return;

        const style = document.createElement('style');
        style.id = 'modal-manager-styles';
        style.textContent = `
            .modal-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.3s ease;
            }

            .modal-overlay.show {
                opacity: 1;
            }

            .modal-container {
                background: white;
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                max-width: 600px;
                width: 90%;
                max-height: 80vh;
                overflow: hidden;
                transform: scale(0.9) translateY(20px);
                transition: transform 0.3s ease;
            }

            .modal-overlay.show .modal-container {
                transform: scale(1) translateY(0);
            }

            .modal-header {
                padding: 20px 24px;
                border-bottom: 1px solid #e0e0e0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .modal-header h3 {
                margin: 0;
                font-size: 20px;
                font-weight: 600;
                color: #333;
            }

            .modal-close {
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #666;
                padding: 0;
                width: 32px;
                height: 32px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: all 0.2s;
            }

            .modal-close:hover {
                background: #f0f0f0;
                color: #333;
            }

            .modal-body {
                padding: 24px;
                max-height: calc(80vh - 140px);
                overflow-y: auto;
            }

            .modal-footer {
                padding: 16px 24px;
                border-top: 1px solid #e0e0e0;
                display: flex;
                justify-content: flex-end;
                gap: 12px;
            }

            .form-group {
                margin-bottom: 20px;
            }

            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: 500;
                color: #555;
            }

            .form-input {
                width: 100%;
                padding: 10px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 14px;
                transition: border-color 0.2s;
            }

            .form-input:focus {
                outline: none;
                border-color: #4CAF50;
            }

            .btn {
                padding: 10px 20px;
                border: 1px solid #ddd;
                border-radius: 6px;
                background: white;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                transition: all 0.2s;
            }

            .btn:hover {
                background: #f5f5f5;
            }

            .btn-primary {
                background: #4CAF50;
                color: white;
                border-color: #4CAF50;
            }

            .btn-primary:hover {
                background: #45a049;
            }

            .btn-danger {
                background: #f44336;
                color: white;
                border-color: #f44336;
            }

            .btn-danger:hover {
                background: #da190b;
            }
        `;
        document.head.appendChild(style);
    }

    show(options) {
        const modalId = 'modal-' + Date.now();

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.id = modalId;

        overlay.innerHTML = `
            <div class="modal-container">
                <div class="modal-header">
                    <h3>${options.title || '확인'}</h3>
                    <button class="modal-close" data-action="close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    ${options.content || ''}
                </div>
                ${options.buttons ? `
                    <div class="modal-footer">
                        ${options.buttons.map(btn => `
                            <button class="btn ${btn.class || ''}" data-action="${btn.action || 'custom'}">
                                ${btn.text}
                            </button>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;

        document.body.appendChild(overlay);
        this.modals.set(modalId, overlay);

        setTimeout(() => overlay.classList.add('show'), 10);

        overlay.addEventListener('click', (e) => {
            if (e.target === overlay || e.target.closest('[data-action="close"]')) {
                this.hide(modalId);
            }

            const actionBtn = e.target.closest('[data-action]');
            if (actionBtn && actionBtn.dataset.action !== 'close') {
                const button = options.buttons?.find(b => b.action === actionBtn.dataset.action);
                if (button?.onclick) {
                    const result = button.onclick();
                    if (result !== false) {
                        this.hide(modalId);
                    }
                }
            }
        });

        return modalId;
    }

    hide(modalId) {
        const modal = this.modals.get(modalId);
        if (!modal) return;

        modal.classList.remove('show');
        setTimeout(() => {
            modal.remove();
            this.modals.delete(modalId);
        }, 300);
    }

    confirm(message, title = '확인') {
        return new Promise((resolve) => {
            this.show({
                title: title,
                content: `<p style="margin: 0; font-size: 16px; line-height: 1.6;">${message}</p>`,
                buttons: [
                    {
                        text: '취소',
                        class: 'btn',
                        action: 'cancel',
                        onclick: () => {
                            resolve(false);
                        }
                    },
                    {
                        text: '확인',
                        class: 'btn-primary',
                        action: 'confirm',
                        onclick: () => {
                            resolve(true);
                        }
                    }
                ]
            });
        });
    }

    alert(message, title = '알림') {
        return new Promise((resolve) => {
            this.show({
                title: title,
                content: `<p style="margin: 0; font-size: 16px; line-height: 1.6;">${message}</p>`,
                buttons: [
                    {
                        text: '확인',
                        class: 'btn-primary',
                        action: 'ok',
                        onclick: () => {
                            resolve(true);
                        }
                    }
                ]
            });
        });
    }

    showBuyModal(stockCode, stockName, currentPrice) {
        return new Promise((resolve) => {
            this.show({
                title: `${stockName} 매수`,
                content: `
                    <form id="buy-form">
                        <div class="form-group">
                            <label>현재가</label>
                            <input type="text" class="form-input" value="${currentPrice?.toLocaleString()}원" readonly>
                        </div>
                        <div class="form-group">
                            <label>수량 *</label>
                            <input type="number" name="quantity" class="form-input" min="1" required>
                        </div>
                        <div class="form-group">
                            <label>매수가격 *</label>
                            <input type="number" name="price" class="form-input" value="${currentPrice || ''}" min="0" required>
                        </div>
                        <div class="form-group">
                            <label>손절 비율 (%)</label>
                            <input type="number" name="stop_loss" class="form-input" min="0" max="100" step="0.1" value="5">
                        </div>
                        <div class="form-group">
                            <label>익절 비율 (%)</label>
                            <input type="number" name="take_profit" class="form-input" min="0" max="100" step="0.1" value="10">
                        </div>
                    </form>
                `,
                buttons: [
                    {
                        text: '취소',
                        class: 'btn',
                        action: 'cancel',
                        onclick: () => resolve(null)
                    },
                    {
                        text: '매수',
                        class: 'btn-primary',
                        action: 'buy',
                        onclick: () => {
                            const form = document.getElementById('buy-form');
                            if (!form.checkValidity()) {
                                form.reportValidity();
                                return false;
                            }

                            const formData = new FormData(form);
                            resolve({
                                stockCode,
                                stockName,
                                quantity: parseInt(formData.get('quantity')),
                                price: parseFloat(formData.get('price')),
                                stopLoss: parseFloat(formData.get('stop_loss')) || null,
                                takeProfit: parseFloat(formData.get('take_profit')) || null
                            });
                        }
                    }
                ]
            });
        });
    }
}

const modalManager = new ModalManager();
window.modalManager = modalManager;
