"""
HTML page routes for dashboard UI
Serves different dashboard variations and configuration pages
"""
from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    """Serve main dashboard with tabs (v6.1 Enhanced UI)"""
    return render_template('dashboard_main.html')


@pages_bp.route('/modern')
def modern_dashboard():
    """Serve v6.1 Modern Dashboard with GSAP (Coming Soon)"""
    return render_template('dashboard_v6_modern.html')


@pages_bp.route('/old')
def old_dashboard():
    """Serve old V3.0 Korean dashboard"""
    return render_template('dashboard_pro_korean.html')


@pages_bp.route('/new')
def new_dashboard():
    """Serve experimental v4.2 dashboard"""
    return render_template('dashboard_v42_korean.html')


@pages_bp.route('/classic')
def classic():
    """Serve classic Apple-style dashboard"""
    return render_template('dashboard_apple.html')


@pages_bp.route('/v42')
def v42_features():
    """Serve v4.2 AI Features dashboard (English)"""
    return render_template('dashboard_v42.html')


@pages_bp.route('/ai-dashboard')
def ai_dashboard():
    """Serve AI Dashboard UI"""
    return render_template('ai_dashboard.html')


@pages_bp.route('/settings')
def settings_page():
    """통합 설정 페이지"""
    return render_template('settings_unified.html')


@pages_bp.route('/backtest')
def backtest_page():
    """백테스팅 페이지"""
    return render_template('backtest.html')
