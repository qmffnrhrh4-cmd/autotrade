from flask import Blueprint, render_template, redirect, url_for

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    """메인 페이지 - 자율 진화 모니터로 리다이렉트"""
    return redirect('/autonomous')


@pages_bp.route('/legacy')
def legacy_dashboard():
    """레거시 대시보드 (이전 버전 호환용)"""
    return render_template('dashboard_main.html')


@pages_bp.route('/settings')
def settings_page():
    return render_template('settings_unified.html')


@pages_bp.route('/backtest')
def backtest_page():
    return render_template('backtest.html')


@pages_bp.route('/chart')
def chart_page():
    return render_template('chart_analysis.html')


@pages_bp.route('/evolution')
def evolution_dashboard():
    """진화 알고리즘 실시간 대시보드"""
    return render_template('evolution_dashboard.html')


@pages_bp.route('/live-monitor')
def live_monitor():
    """실시간 활동 모니터"""
    return render_template('live_monitor.html')


@pages_bp.route('/split-orders')
def split_orders():
    """분할 주문 관리"""
    return render_template('split_orders.html')
