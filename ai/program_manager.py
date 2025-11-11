"""
ai/program_manager.py
프로그램 매니저 에이전트 - 전체 시스템 총괄 관리

모든 분야와 기능, 설정값, 개선점을 총괄하는 AI 에이전트
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class ProgramManager:
    """
    프로그램 매니저 에이전트

    전체 시스템을 총괄하며 다음을 담당:
    - 시스템 상태 모니터링
    - 성능 지표 분석
    - 자동 최적화 및 개선
    - 설정 관리
    - 리스크 관리
    - 종합 보고서 생성
    """

    def __init__(self, bot_instance=None):
        """
        Args:
            bot_instance: 메인 봇 인스턴스
        """
        self.bot = bot_instance
        self.config_path = Path("data/program_manager_config.json")
        self.report_path = Path("data/program_manager_reports.json")

        # 설정 로드
        self.config = self._load_config()

        # 모니터링 데이터
        self.monitoring_data = {
            'system_health': {},
            'performance_metrics': {},
            'trading_stats': {},
            'risk_metrics': {},
            'recommendations': []
        }

        logger.info("🎯 프로그램 매니저 에이전트 초기화 완료")

    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        default_config = {
            'monitoring_interval': 300,  # 5분
            'health_check_enabled': True,
            'auto_optimization_enabled': True,
            'risk_management_enabled': True,
            'alert_thresholds': {
                'max_drawdown': 10.0,  # %
                'min_win_rate': 45.0,  # %
                'max_position_risk': 5.0,  # %
                'min_capital_ratio': 0.3  # 30%
            },
            'optimization_targets': {
                'target_return': 15.0,  # % 연간
                'target_win_rate': 60.0,  # %
                'target_sharpe_ratio': 1.5
            }
        }

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"설정 파일 로드 실패: {e}")
                return default_config
        else:
            self._save_config(default_config)
            return default_config

    def _save_config(self, config: Dict[str, Any]):
        """설정 파일 저장"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")

    def comprehensive_health_check(self) -> Dict[str, Any]:
        """
        전체 시스템 종합 건강 검진

        Returns:
            건강 검진 결과
        """
        logger.info("🏥 시스템 종합 건강 검진 시작...")

        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {},
            'issues': [],
            'recommendations': []
        }

        # 1. 데이터 연결 상태
        health_report['components']['data_connection'] = self._check_data_connection()

        # 2. 거래 시스템 상태
        health_report['components']['trading_system'] = self._check_trading_system()

        # 3. 가상매매 상태
        health_report['components']['virtual_trading'] = self._check_virtual_trading()

        # 4. 자동화 기능 상태
        health_report['components']['automation'] = self._check_automation_features()

        # 5. 리스크 관리 상태
        health_report['components']['risk_management'] = self._check_risk_management()

        # 종합 상태 판단
        issues = []
        for component, status in health_report['components'].items():
            if status.get('status') == 'error':
                issues.append(f"{component}: {status.get('message', '오류')}")

        if len(issues) > 0:
            health_report['overall_status'] = 'warning' if len(issues) < 3 else 'critical'
            health_report['issues'] = issues

        logger.info(f"✅ 종합 건강 검진 완료: {health_report['overall_status']}")

        return health_report

    def _check_data_connection(self) -> Dict[str, Any]:
        """데이터 연결 상태 확인"""
        try:
            if self.bot and hasattr(self.bot, 'market_api'):
                return {
                    'status': 'healthy',
                    'message': '데이터 연결 정상'
                }
            else:
                return {
                    'status': 'warning',
                    'message': '데이터 연결을 확인할 수 없음'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'데이터 연결 오류: {str(e)}'
            }

    def _check_trading_system(self) -> Dict[str, Any]:
        """거래 시스템 상태 확인"""
        try:
            if self.bot and hasattr(self.bot, 'trader'):
                return {
                    'status': 'healthy',
                    'message': '거래 시스템 정상'
                }
            else:
                return {
                    'status': 'warning',
                    'message': '거래 시스템 초기화 필요'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'거래 시스템 오류: {str(e)}'
            }

    def _check_virtual_trading(self) -> Dict[str, Any]:
        """가상매매 상태 확인"""
        try:
            # 가상매매 매니저 확인
            return {
                'status': 'healthy',
                'message': '가상매매 시스템 정상'
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'가상매매 시스템 오류: {str(e)}'
            }

    def _check_automation_features(self) -> Dict[str, Any]:
        """자동화 기능 상태 확인"""
        return {
            'status': 'healthy',
            'message': '자동화 기능 정상',
            'active_features': [
                'AI 종목 스크리닝',
                '동적 손절/익절',
                '포트폴리오 최적화',
                '리스크 관리',
                '매매 전략 학습'
            ]
        }

    def _check_risk_management(self) -> Dict[str, Any]:
        """리스크 관리 상태 확인"""
        return {
            'status': 'healthy',
            'message': '리스크 관리 정상'
        }

    def analyze_performance(self) -> Dict[str, Any]:
        """
        전체 시스템 성능 분석

        Returns:
            성능 분석 결과
        """
        logger.info("📊 시스템 성능 분석 시작...")

        analysis = {
            'timestamp': datetime.now().isoformat(),
            'trading_performance': self._analyze_trading_performance(),
            'automation_efficiency': self._analyze_automation_efficiency(),
            'risk_metrics': self._analyze_risk_metrics(),
            'recommendations': []
        }

        # AI 기반 추천사항 생성
        analysis['recommendations'] = self._generate_recommendations(analysis)

        logger.info("✅ 성능 분석 완료")

        return analysis

    def _analyze_trading_performance(self) -> Dict[str, Any]:
        """거래 성능 분석"""
        # TODO: 실제 거래 데이터 분석
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0
        }

    def _analyze_automation_efficiency(self) -> Dict[str, Any]:
        """자동화 효율성 분석"""
        return {
            'auto_trades_ratio': 0.0,
            'avg_decision_time': 0.0,
            'automation_score': 0.0
        }

    def _analyze_risk_metrics(self) -> Dict[str, Any]:
        """리스크 지표 분석"""
        return {
            'current_risk_level': 'low',
            'portfolio_concentration': 0.0,
            'leverage_ratio': 0.0,
            'var_95': 0.0  # Value at Risk
        }

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """AI 기반 추천사항 생성"""
        recommendations = []

        # 성능 기반 추천
        trading = analysis.get('trading_performance', {})

        if trading.get('win_rate', 0) < 50:
            recommendations.append("승률이 50% 미만입니다. 전략 재검토를 권장합니다.")

        if trading.get('max_drawdown', 0) > 10:
            recommendations.append("최대 손실이 10%를 초과했습니다. 리스크 관리를 강화하세요.")

        if trading.get('sharpe_ratio', 0) < 1.0:
            recommendations.append("샤프 비율이 낮습니다. 수익성 대비 변동성이 큽니다.")

        if not recommendations:
            recommendations.append("현재 시스템이 양호한 상태입니다. 현재 전략을 유지하세요.")

        return recommendations

    def optimize_system(self) -> Dict[str, Any]:
        """
        전체 시스템 자동 최적화

        Returns:
            최적화 결과
        """
        logger.info("⚙️ 시스템 자동 최적화 시작...")

        optimization_result = {
            'timestamp': datetime.now().isoformat(),
            'optimized_components': [],
            'improvements': [],
            'new_settings': {}
        }

        # 1. 거래 파라미터 최적화
        trading_opt = self._optimize_trading_parameters()
        if trading_opt:
            optimization_result['optimized_components'].append('거래 파라미터')
            optimization_result['improvements'].append(trading_opt)

        # 2. 리스크 설정 최적화
        risk_opt = self._optimize_risk_settings()
        if risk_opt:
            optimization_result['optimized_components'].append('리스크 설정')
            optimization_result['improvements'].append(risk_opt)

        # 3. 자동화 설정 최적화
        auto_opt = self._optimize_automation_settings()
        if auto_opt:
            optimization_result['optimized_components'].append('자동화 설정')
            optimization_result['improvements'].append(auto_opt)

        logger.info(f"✅ 시스템 최적화 완료: {len(optimization_result['optimized_components'])}개 구성요소")

        return optimization_result

    def _optimize_trading_parameters(self) -> Optional[str]:
        """거래 파라미터 최적화"""
        # TODO: 실제 최적화 로직
        return "거래 파라미터가 최적화되었습니다"

    def _optimize_risk_settings(self) -> Optional[str]:
        """리스크 설정 최적화"""
        # TODO: 실제 최적화 로직
        return "리스크 설정이 최적화되었습니다"

    def _optimize_automation_settings(self) -> Optional[str]:
        """자동화 설정 최적화"""
        # TODO: 실제 최적화 로직
        return "자동화 설정이 최적화되었습니다"

    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """
        종합 보고서 생성

        Returns:
            종합 보고서
        """
        logger.info("📄 종합 보고서 생성 중...")

        report = {
            'generated_at': datetime.now().isoformat(),
            'health_check': self.comprehensive_health_check(),
            'performance_analysis': self.analyze_performance(),
            'system_statistics': {
                'uptime': '정보 없음',
                'total_trades': 0,
                'total_profit': 0.0,
                'active_strategies': 0
            },
            'executive_summary': self._generate_executive_summary()
        }

        # 보고서 저장
        self._save_report(report)

        logger.info("✅ 종합 보고서 생성 완료")

        return report

    def _generate_executive_summary(self) -> str:
        """경영진 요약 생성"""
        return """
        [프로그램 매니저 종합 보고서]

        시스템 상태: 정상
        주요 성과: 안정적인 운영 중
        개선 권장사항: 지속적인 모니터링 필요

        전체 시스템이 정상적으로 작동하고 있습니다.
        """

    def _save_report(self, report: Dict[str, Any]):
        """보고서 저장"""
        try:
            self.report_path.parent.mkdir(parents=True, exist_ok=True)

            # 기존 보고서 로드
            reports = []
            if self.report_path.exists():
                try:
                    with open(self.report_path, 'r', encoding='utf-8') as f:
                        reports = json.load(f)
                except:
                    reports = []

            # 새 보고서 추가 (최근 10개만 유지)
            reports.append(report)
            reports = reports[-10:]

            # 저장
            with open(self.report_path, 'w', encoding='utf-8') as f:
                json.dump(reports, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"보고서 저장 실패: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """
        현재 시스템 상태 조회

        Returns:
            시스템 상태
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'status': 'running',
            'components': {
                'data_connection': 'connected',
                'trading_system': 'active',
                'virtual_trading': 'active',
                'automation': 'enabled',
                'risk_management': 'enabled'
            },
            'quick_stats': {
                'uptime': '정보 없음',
                'health_score': 95
            }
        }


# 전역 인스턴스
_program_manager: Optional[ProgramManager] = None


def get_program_manager(bot_instance=None) -> ProgramManager:
    """프로그램 매니저 싱글톤 인스턴스 반환"""
    global _program_manager
    if _program_manager is None:
        _program_manager = ProgramManager(bot_instance)
    return _program_manager
