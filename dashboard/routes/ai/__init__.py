from flask import Blueprint

from .ai_mode import ai_mode_bp
from .auto_analysis import auto_analysis_bp
from .common import set_bot_instance, get_bot_instance

ai_bp = Blueprint('ai', __name__)


def register_ai_routes(app):
    app.register_blueprint(ai_mode_bp)
    app.register_blueprint(auto_analysis_bp)


__all__ = [
    'ai_bp',
    'register_ai_routes',
    'set_bot_instance',
    'get_bot_instance',
    'ai_mode_bp',
    'auto_analysis_bp',
]
