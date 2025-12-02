"""
단일 대시보드 라우트
모든 기능을 하나의 화면에서 처리
"""
from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    """메인 대시보드 - 단일 화면"""
    return render_template('autonomous_monitor.html')
