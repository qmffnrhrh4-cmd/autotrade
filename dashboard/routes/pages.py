from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    return render_template('dashboard_main.html')


@pages_bp.route('/settings')
def settings_page():
    return render_template('settings_unified.html')


@pages_bp.route('/backtest')
def backtest_page():
    return render_template('backtest.html')
