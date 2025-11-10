/**
 * Modern UI Utilities v6.1
 * 부드러운 애니메이션, 인터랙티브 요소, 성능 최적화
 */

class ModernUI {
    constructor() {
        this.init();
    }

    init() {
        this.initScrollAnimations();
        this.initCardAnimations();
        this.initCounters();
        this.initLazyLoading();
        this.initSmoothScroll();
        console.log('✨ Modern UI initialized');
    }

    /**
     * 스크롤 기반 애니메이션 (AOS 스타일)
     */
    initScrollAnimations() {
        const observerOptions = {
            root: null,
            rootMargin: '0px',
            threshold: 0.1
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    // 한번만 애니메이션 실행
                    if (entry.target.dataset.once !== 'false') {
                        observer.unobserve(entry.target);
                    }
                }
            });
        }, observerOptions);

        // data-animate 속성을 가진 모든 요소 관찰
        document.querySelectorAll('[data-animate]').forEach(el => {
            el.style.opacity = '0';
            el.style.transform = this.getAnimationTransform(el.dataset.animate);
            el.style.transition = 'opacity 0.6s ease, transform 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
            observer.observe(el);
        });

        // 스타일 추가
        const style = document.createElement('style');
        style.textContent = `
            [data-animate].is-visible {
                opacity: 1 !important;
                transform: translate(0, 0) !important;
            }
        `;
        document.head.appendChild(style);
    }

    getAnimationTransform(type) {
        const transforms = {
            'fade-up': 'translateY(30px)',
            'fade-down': 'translateY(-30px)',
            'fade-left': 'translateX(30px)',
            'fade-right': 'translateX(-30px)',
            'zoom-in': 'scale(0.9)',
            'zoom-out': 'scale(1.1)'
        };
        return transforms[type] || 'translateY(30px)';
    }

    /**
     * 카드 호버 3D 효과
     */
    initCardAnimations() {
        document.querySelectorAll('.modern-card, .glass-card').forEach(card => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                const centerX = rect.width / 2;
                const centerY = rect.height / 2;

                const rotateX = (y - centerY) / 10;
                const rotateY = (centerX - x) / 10;

                card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = '';
            });
        });
    }

    /**
     * 애니메이션 카운터 (숫자 증가 효과)
     */
    initCounters() {
        const counters = document.querySelectorAll('[data-counter]');

        const animateCounter = (element) => {
            const target = parseFloat(element.dataset.counter);
            const duration = parseInt(element.dataset.duration || 2000);
            const start = 0;
            const startTime = performance.now();

            const updateCounter = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // Easing function (easeOutExpo)
                const easeProgress = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);

                const current = start + (target - start) * easeProgress;

                // 소수점 처리
                const decimals = element.dataset.decimals || 0;
                element.textContent = current.toFixed(decimals);

                // 천단위 콤마 추가
                if (element.dataset.comma !== 'false') {
                    element.textContent = parseFloat(element.textContent).toLocaleString('ko-KR', {
                        minimumFractionDigits: decimals,
                        maximumFractionDigits: decimals
                    });
                }

                // 단위 추가
                if (element.dataset.suffix) {
                    element.textContent += element.dataset.suffix;
                }

                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                }
            };

            requestAnimationFrame(updateCounter);
        };

        // Intersection Observer로 화면에 보일 때만 애니메이션
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        });

        counters.forEach(counter => observer.observe(counter));
    }

    /**
     * 이미지 레이지 로딩
     */
    initLazyLoading() {
        const images = document.querySelectorAll('img[data-src]');

        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.add('loaded');
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    }

    /**
     * 부드러운 스크롤
     */
    initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const target = document.querySelector(anchor.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    /**
     * 토스트 알림
     */
    static showToast(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;

        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };

        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 16px 24px;
            background: ${colors[type] || colors.info};
            color: white;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            font-size: 14px;
            font-weight: 500;
            z-index: 10000;
            animation: slideInRight 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }

    /**
     * 모달 관리
     */
    static openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('active'), 10);
        document.body.style.overflow = 'hidden';
    }

    static closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        modal.classList.remove('active');
        setTimeout(() => {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }, 300);
    }

    /**
     * 진행 바 애니메이션
     */
    static animateProgress(element, targetPercent, duration = 1000) {
        const startTime = performance.now();
        const startPercent = 0;

        const updateProgress = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            const easeProgress = 1 - Math.pow(1 - progress, 3); // easeOutCubic
            const currentPercent = startPercent + (targetPercent - startPercent) * easeProgress;

            element.style.width = `${currentPercent}%`;

            if (progress < 1) {
                requestAnimationFrame(updateProgress);
            }
        };

        requestAnimationFrame(updateProgress);
    }

    /**
     * 스크롤 진행률 표시
     */
    static initScrollProgress() {
        const progressBar = document.createElement('div');
        progressBar.className = 'scroll-progress';
        progressBar.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            height: 3px;
            background: linear-gradient(90deg, #6366f1, #8b5cf6);
            z-index: 9999;
            transition: width 0.1s ease;
        `;
        document.body.appendChild(progressBar);

        window.addEventListener('scroll', () => {
            const winScroll = document.documentElement.scrollTop;
            const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
            const scrolled = (winScroll / height) * 100;
            progressBar.style.width = `${scrolled}%`;
        });
    }

    /**
     * Debounce 유틸리티
     */
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Throttle 유틸리티
     */
    static throttle(func, limit) {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }

    /**
     * 실시간 데이터 업데이트 애니메이션
     */
    static animateValue(element, start, end, duration = 1000, formatter = null) {
        const startTime = performance.now();

        const updateValue = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            const easeProgress = 1 - Math.pow(1 - progress, 3);
            const currentValue = start + (end - start) * easeProgress;

            element.textContent = formatter ? formatter(currentValue) : Math.round(currentValue);
            element.classList.add('pulse');

            if (progress < 1) {
                requestAnimationFrame(updateValue);
            } else {
                setTimeout(() => element.classList.remove('pulse'), 500);
            }
        };

        requestAnimationFrame(updateValue);
    }

    /**
     * 파티클 효과
     */
    static createParticles(element, count = 20) {
        const rect = element.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        for (let i = 0; i < count; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.cssText = `
                position: fixed;
                width: 8px;
                height: 8px;
                background: #3b82f6;
                border-radius: 50%;
                pointer-events: none;
                z-index: 9999;
                left: ${centerX}px;
                top: ${centerY}px;
            `;

            document.body.appendChild(particle);

            const angle = (Math.PI * 2 * i) / count;
            const velocity = 2 + Math.random() * 2;
            const tx = Math.cos(angle) * velocity * 50;
            const ty = Math.sin(angle) * velocity * 50;

            particle.animate([
                { transform: 'translate(0, 0) scale(1)', opacity: 1 },
                { transform: `translate(${tx}px, ${ty}px) scale(0)`, opacity: 0 }
            ], {
                duration: 800,
                easing: 'cubic-bezier(0, .9, .57, 1)'
            }).onfinish = () => particle.remove();
        }
    }

    /**
     * 로딩 오버레이
     */
    static showLoadingOverlay(message = '로딩 중...') {
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            backdrop-filter: blur(4px);
        `;

        overlay.innerHTML = `
            <div style="text-align: center; color: white;">
                <div class="loading-spinner loading-spinner-lg"></div>
                <p style="margin-top: 20px; font-size: 16px;">${message}</p>
            </div>
        `;

        document.body.appendChild(overlay);
        return overlay;
    }

    static hideLoadingOverlay() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => overlay.remove(), 300);
        }
    }

    /**
     * 확인 다이얼로그
     */
    static async confirm(message, title = '확인') {
        return new Promise((resolve) => {
            const dialog = document.createElement('div');
            dialog.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10001;
                animation: fadeIn 0.2s;
            `;

            dialog.innerHTML = `
                <div style="background: white; padding: 30px; border-radius: 12px; max-width: 400px; box-shadow: 0 10px 40px rgba(0,0,0,0.3); animation: scaleIn 0.3s;">
                    <h3 style="margin: 0 0 15px 0; font-size: 20px;">${title}</h3>
                    <p style="margin: 0 0 25px 0; color: #666;">${message}</p>
                    <div style="display: flex; gap: 10px; justify-content: flex-end;">
                        <button id="dialog-cancel" style="padding: 10px 20px; border: 1px solid #ddd; background: white; border-radius: 6px; cursor: pointer;">취소</button>
                        <button id="dialog-confirm" style="padding: 10px 20px; border: none; background: #3b82f6; color: white; border-radius: 6px; cursor: pointer;">확인</button>
                    </div>
                </div>
            `;

            document.body.appendChild(dialog);

            dialog.querySelector('#dialog-confirm').onclick = () => {
                dialog.remove();
                resolve(true);
            };

            dialog.querySelector('#dialog-cancel').onclick = () => {
                dialog.remove();
                resolve(false);
            };

            dialog.onclick = (e) => {
                if (e.target === dialog) {
                    dialog.remove();
                    resolve(false);
                }
            };
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => new ModernUI());
} else {
    new ModernUI();
}

const globalStyles = document.createElement('style');
globalStyles.textContent = `
    @keyframes slideInRight {
        from { opacity: 0; transform: translateX(100px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes slideOutRight {
        from { opacity: 1; transform: translateX(0); }
        to { opacity: 0; transform: translateX(100px); }
    }
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
`;
document.head.appendChild(globalStyles);

window.ModernUI = ModernUI;
