class APIClient {
    constructor() {
        this.cache = new Map();
        this.pendingRequests = new Map();
        this.defaultTimeout = 10000;
    }

    async fetch(url, options = {}, cacheTime = 0) {
        const cacheKey = url + JSON.stringify(options);

        if (this.pendingRequests.has(cacheKey)) {
            return this.pendingRequests.get(cacheKey);
        }

        if (cacheTime > 0 && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (Date.now() - cached.timestamp < cacheTime) {
                return cached.data;
            }
        }

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.defaultTimeout);

        const promise = fetch(url, {
            ...options,
            signal: controller.signal
        })
        .then(res => {
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            }
            return res.json();
        })
        .then(data => {
            if (cacheTime > 0) {
                this.cache.set(cacheKey, {
                    data: data,
                    timestamp: Date.now()
                });
            }
            return data;
        })
        .catch(error => {
            if (error.name === 'AbortError') {
                throw new Error('요청 시간이 초과되었습니다.');
            }
            throw error;
        })
        .finally(() => {
            clearTimeout(timeoutId);
            this.pendingRequests.delete(cacheKey);
        });

        this.pendingRequests.set(cacheKey, promise);
        return promise;
    }

    clearCache() {
        this.cache.clear();
    }

    clearCacheByPrefix(prefix) {
        for (const key of this.cache.keys()) {
            if (key.startsWith(prefix)) {
                this.cache.delete(key);
            }
        }
    }
}

const apiClient = new APIClient();
window.apiClient = apiClient;
