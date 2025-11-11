class RealtimeDataManager {
    constructor() {
        this.socket = null;
        this.subscribers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
        this.isConnected = false;
        this.connectionStatus = 'disconnected';

        this.init();
    }

    init() {
        if (typeof io === 'undefined') {
            console.warn('Socket.IO not loaded, realtime features disabled');
            return;
        }

        this.socket = io({
            reconnection: true,
            reconnectionAttempts: this.maxReconnectAttempts,
            reconnectionDelay: this.reconnectDelay
        });

        this.setupSocketHandlers();
    }

    setupSocketHandlers() {
        this.socket.on('connect', () => {
            console.log('✅ WebSocket connected');
            this.isConnected = true;
            this.connectionStatus = 'connected';
            this.reconnectAttempts = 0;
            this.resubscribeAll();
            this.notifyStatusChange('connected');
        });

        this.socket.on('disconnect', (reason) => {
            console.log('❌ WebSocket disconnected:', reason);
            this.isConnected = false;
            this.connectionStatus = 'disconnected';
            this.notifyStatusChange('disconnected');

            if (reason === 'io server disconnect') {
                this.socket.connect();
            }
        });

        this.socket.on('connect_error', (error) => {
            console.error('WebSocket connection error:', error);
            this.connectionStatus = 'error';
            this.notifyStatusChange('error');
        });

        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`🔄 WebSocket reconnected after ${attemptNumber} attempts`);
            this.isConnected = true;
            this.connectionStatus = 'connected';
            this.notifyStatusChange('reconnected');
        });

        this.socket.on('price_update', (data) => {
            this.notifySubscribers('price', data);
        });

        this.socket.on('market_status', (data) => {
            this.notifySubscribers('market_status', data);
        });

        this.socket.on('position_update', (data) => {
            this.notifySubscribers('position', data);
        });

        this.socket.on('order_update', (data) => {
            this.notifySubscribers('order', data);
        });

        this.socket.on('alert', (data) => {
            this.notifySubscribers('alert', data);
        });
    }

    subscribe(channel, callback) {
        if (!this.subscribers.has(channel)) {
            this.subscribers.set(channel, new Set());
        }

        this.subscribers.get(channel).add(callback);

        if (this.isConnected && this.socket) {
            this.socket.emit('subscribe', { channel });
        }

        console.log(`Subscribed to channel: ${channel}`);
    }

    unsubscribe(channel, callback) {
        if (!this.subscribers.has(channel)) return;

        this.subscribers.get(channel).delete(callback);

        if (this.subscribers.get(channel).size === 0) {
            this.subscribers.delete(channel);

            if (this.isConnected && this.socket) {
                this.socket.emit('unsubscribe', { channel });
            }
        }

        console.log(`Unsubscribed from channel: ${channel}`);
    }

    notifySubscribers(channel, data) {
        if (!this.subscribers.has(channel)) return;

        for (const callback of this.subscribers.get(channel)) {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in subscriber callback for ${channel}:`, error);
            }
        }
    }

    notifyStatusChange(status) {
        this.notifySubscribers('connection_status', { status });
    }

    resubscribeAll() {
        if (!this.isConnected || !this.socket) return;

        for (const channel of this.subscribers.keys()) {
            this.socket.emit('subscribe', { channel });
        }

        console.log(`Resubscribed to ${this.subscribers.size} channels`);
    }

    emit(event, data) {
        if (this.isConnected && this.socket) {
            this.socket.emit(event, data);
        } else {
            console.warn(`Cannot emit ${event}, socket not connected`);
        }
    }

    getConnectionStatus() {
        return {
            isConnected: this.isConnected,
            status: this.connectionStatus,
            reconnectAttempts: this.reconnectAttempts
        };
    }
}

const realtimeManager = new RealtimeDataManager();
window.realtimeManager = realtimeManager;
