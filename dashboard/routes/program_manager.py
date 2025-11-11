"""
dashboard/routes/program_manager.py
프로그램 매니저 API 엔드포인트
"""
import logging
from flask import Blueprint, jsonify, request
from ai.program_manager import get_program_manager

logger = logging.getLogger(__name__)

# Blueprint 생성
program_manager_bp = Blueprint('program_manager', __name__)

# 봇 인스턴스 (전역)
_bot_instance = None


def set_bot_instance(bot):
    """봇 인스턴스 설정"""
    global _bot_instance
    _bot_instance = bot
    logger.info("프로그램 매니저에 봇 인스턴스 설정 완료")


@program_manager_bp.route('/api/program-manager/status', methods=['GET'])
def get_status():
    """시스템 상태 조회"""
    try:
        pm = get_program_manager(_bot_instance)
        status = pm.get_system_status()

        return jsonify({
            'success': True,
            'status': status
        })

    except Exception as e:
        logger.error(f"시스템 상태 조회 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@program_manager_bp.route('/api/program-manager/health-check', methods=['POST'])
def health_check():
    """종합 건강 검진 실행"""
    try:
        pm = get_program_manager(_bot_instance)
        health_report = pm.comprehensive_health_check()

        return jsonify({
            'success': True,
            'report': health_report
        })

    except Exception as e:
        logger.error(f"건강 검진 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@program_manager_bp.route('/api/program-manager/analyze', methods=['POST'])
def analyze_performance():
    """시스템 성능 분석"""
    try:
        pm = get_program_manager(_bot_instance)
        analysis = pm.analyze_performance()

        return jsonify({
            'success': True,
            'analysis': analysis
        })

    except Exception as e:
        logger.error(f"성능 분석 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@program_manager_bp.route('/api/program-manager/optimize', methods=['POST'])
def optimize_system():
    """시스템 자동 최적화"""
    try:
        pm = get_program_manager(_bot_instance)
        result = pm.optimize_system()

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        logger.error(f"시스템 최적화 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@program_manager_bp.route('/api/program-manager/report', methods=['GET'])
def generate_report():
    """종합 보고서 생성"""
    try:
        pm = get_program_manager(_bot_instance)
        report = pm.generate_comprehensive_report()

        return jsonify({
            'success': True,
            'report': report
        })

    except Exception as e:
        logger.error(f"보고서 생성 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@program_manager_bp.route('/api/program-manager/config', methods=['GET', 'POST'])
def manage_config():
    """설정 관리"""
    try:
        pm = get_program_manager(_bot_instance)

        if request.method == 'GET':
            # 설정 조회
            return jsonify({
                'success': True,
                'config': pm.config
            })

        elif request.method == 'POST':
            # 설정 업데이트
            data = request.json
            pm.config.update(data)
            pm._save_config(pm.config)

            return jsonify({
                'success': True,
                'message': '설정이 업데이트되었습니다',
                'config': pm.config
            })

    except Exception as e:
        logger.error(f"설정 관리 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@program_manager_bp.route('/api/program-manager/execute-recommendation', methods=['POST'])
def execute_recommendation():
    """권장사항 실행"""
    try:
        data = request.json
        recommendation = data.get('recommendation', '')

        pm = get_program_manager(_bot_instance)

        # 권장사항에 따라 실제 조치 수행
        if '초기화' in recommendation or 'reset' in recommendation.lower():
            # 시스템 초기화
            result = pm.reset_system_component(recommendation)
            message = f"시스템 컴포넌트가 초기화되었습니다: {result.get('component', 'unknown')}"
        elif '재시작' in recommendation or 'restart' in recommendation.lower():
            # 컴포넌트 재시작
            result = pm.restart_component(recommendation)
            message = f"컴포넌트가 재시작되었습니다: {result.get('component', 'unknown')}"
        elif '정리' in recommendation or 'clean' in recommendation.lower():
            # 데이터 정리
            result = pm.clean_data()
            message = f"데이터가 정리되었습니다: {result.get('cleaned_items', 0)}개 항목"
        else:
            # 기본 최적화
            result = pm.optimize_system()
            message = "시스템 최적화가 완료되었습니다"

        return jsonify({
            'success': True,
            'message': message,
            'result': result
        })

    except Exception as e:
        logger.error(f"권장사항 실행 실패: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


__all__ = ['program_manager_bp', 'set_bot_instance']
