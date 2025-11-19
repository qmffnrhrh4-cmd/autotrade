"""
System Diagnostics - 시스템 자가 진단 및 헬스체크
시작 시 모든 기능, 연계, 설정을 자동으로 체크하고 리포트 생성
"""
import os
import sys
import json
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict

from utils.logger_new import get_logger

logger = get_logger()


@dataclass
class DiagnosticResult:
    """진단 결과"""
    category: str
    check_name: str
    status: str  # 'pass', 'warning', 'fail'
    message: str
    details: str = ""
    solution: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class SystemDiagnostics:
    """시스템 진단 클래스"""

    def __init__(self):
        self.results: List[DiagnosticResult] = []
        self.start_time = datetime.now()

    def add_result(self, result: DiagnosticResult):
        """진단 결과 추가"""
        self.results.append(result)

        # 실시간 로깅
        emoji = "✅" if result.status == "pass" else "⚠️" if result.status == "warning" else "❌"
        logger.info(f"{emoji} [{result.category}] {result.check_name}: {result.message}")

        if result.details:
            logger.debug(f"   상세: {result.details}")

        if result.solution and result.status != "pass":
            logger.warning(f"   💡 해결방법: {result.solution}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 1. 데이터베이스 체크
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def check_database(self) -> bool:
        """데이터베이스 연결 및 스키마 체크"""
        logger.info("📊 데이터베이스 진단 중...")

        # 1. 메인 DB 연결
        try:
            from database import get_db_session, Trade, Position
            from sqlalchemy import inspect

            session = get_db_session()
            if not session:
                raise Exception("Session is None")

            self.add_result(DiagnosticResult(
                category="Database",
                check_name="Main DB Connection",
                status="pass",
                message="메인 데이터베이스 연결 성공"
            ))

            # 2. 스키마 체크 - is_virtual 컬럼
            inspector = inspect(session.bind)
            columns = [col['name'] for col in inspector.get_columns('trades')]

            if 'is_virtual' in columns:
                self.add_result(DiagnosticResult(
                    category="Database",
                    check_name="Schema Check (is_virtual)",
                    status="pass",
                    message="is_virtual 컬럼이 존재합니다"
                ))
            else:
                self.add_result(DiagnosticResult(
                    category="Database",
                    check_name="Schema Check (is_virtual)",
                    status="warning",
                    message="is_virtual 컬럼이 없습니다 (자동 마이그레이션 예정)",
                    solution="시스템이 자동으로 컬럼을 추가합니다"
                ))

            # 3. 인덱스 체크
            indexes = inspector.get_indexes('trades')
            index_names = [idx['name'] for idx in indexes]

            expected_indexes = ['idx_stock_timestamp', 'idx_action_timestamp', 'idx_stock_action_timestamp']
            missing_indexes = [idx for idx in expected_indexes if idx not in index_names]

            if not missing_indexes:
                self.add_result(DiagnosticResult(
                    category="Database",
                    check_name="Index Check",
                    status="pass",
                    message=f"모든 인덱스가 존재합니다 ({len(index_names)}개)"
                ))
            else:
                self.add_result(DiagnosticResult(
                    category="Database",
                    check_name="Index Check",
                    status="warning",
                    message=f"일부 인덱스 누락: {missing_indexes}",
                    solution="시스템이 자동으로 인덱스를 생성합니다"
                ))

            # 4. 거래 기록 샘플 조회
            trade_count = session.query(Trade).count()
            self.add_result(DiagnosticResult(
                category="Database",
                check_name="Trade Records",
                status="pass",
                message=f"거래 기록 {trade_count}개 확인"
            ))

            session.close()
            return True

        except Exception as e:
            self.add_result(DiagnosticResult(
                category="Database",
                check_name="Main DB Connection",
                status="fail",
                message="데이터베이스 연결 실패",
                details=str(e),
                solution="data/ 디렉토리 권한 확인 및 SQLite 설치 확인"
            ))
            return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 2. 가상매매 DB 체크
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def check_virtual_trading_db(self) -> bool:
        """가상매매 데이터베이스 체크"""
        logger.info("🎮 가상매매 DB 진단 중...")

        try:
            from virtual_trading.models import VirtualTradingDB

            db = VirtualTradingDB()
            strategies = db.get_all_strategies()

            self.add_result(DiagnosticResult(
                category="Virtual Trading",
                check_name="Virtual Trading DB",
                status="pass",
                message=f"가상매매 DB 정상 ({len(strategies)}개 전략)",
                details=f"전략: {', '.join([s['name'] for s in strategies]) if strategies else '없음'}"
            ))

            db.close()
            return True

        except Exception as e:
            self.add_result(DiagnosticResult(
                category="Virtual Trading",
                check_name="Virtual Trading DB",
                status="fail",
                message="가상매매 DB 연결 실패",
                details=str(e),
                solution="virtual_trading/models.py 확인"
            ))
            return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 3. 모듈 Import 체크
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def check_module_imports(self) -> bool:
        """핵심 모듈 import 가능 여부 체크"""
        logger.info("📦 모듈 Import 진단 중...")

        modules_to_check = [
            ("database", "데이터베이스 모델"),
            ("api.openapi", "OpenAPI 클라이언트"),
            ("api.account", "계좌 API"),
            ("api.order", "주문 API"),
            ("api.data_fetcher", "시세 조회 API"),
            ("virtual_trading", "가상매매 시스템"),
            ("ai.strategy_loader", "전략 로더"),
            ("ai.program_manager", "프로그램 매니저"),
            ("strategy.emergency_manager", "긴급 관리자"),
            ("strategy.scoring_system", "스코어링 시스템"),
        ]

        all_passed = True

        for module_name, description in modules_to_check:
            try:
                __import__(module_name)
                self.add_result(DiagnosticResult(
                    category="Module Import",
                    check_name=module_name,
                    status="pass",
                    message=f"{description} import 성공"
                ))
            except Exception as e:
                all_passed = False
                self.add_result(DiagnosticResult(
                    category="Module Import",
                    check_name=module_name,
                    status="fail",
                    message=f"{description} import 실패",
                    details=str(e),
                    solution=f"pip install 또는 {module_name}.py 파일 확인"
                ))

        return all_passed

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 4. 설정 파일 체크
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def check_configuration(self) -> bool:
        """설정 파일 유효성 체크"""
        logger.info("⚙️  설정 파일 진단 중...")

        try:
            from config.manager import get_config

            config = get_config()

            # 필수 설정 확인
            required_configs = [
                ("database", "데이터베이스 설정"),
                ("trading", "거래 설정"),
                ("risk_management", "리스크 관리 설정"),
            ]

            for config_key, description in required_configs:
                if hasattr(config, config_key):
                    self.add_result(DiagnosticResult(
                        category="Configuration",
                        check_name=config_key,
                        status="pass",
                        message=f"{description} 로드 성공"
                    ))
                else:
                    self.add_result(DiagnosticResult(
                        category="Configuration",
                        check_name=config_key,
                        status="warning",
                        message=f"{description} 누락",
                        solution="config/config.yaml 확인"
                    ))

            return True

        except Exception as e:
            self.add_result(DiagnosticResult(
                category="Configuration",
                check_name="Config Load",
                status="fail",
                message="설정 파일 로드 실패",
                details=str(e),
                solution="config/config.yaml 파일 존재 여부 및 문법 확인"
            ))
            return False

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 5. 파일 시스템 체크
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def check_filesystem(self) -> bool:
        """필수 디렉토리 및 파일 존재 여부 체크"""
        logger.info("📁 파일 시스템 진단 중...")

        required_dirs = [
            "data",
            "logs",
            "config",
            "api",
            "ai",
            "strategy",
            "virtual_trading",
            "dashboard",
        ]

        all_passed = True

        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists() and dir_path.is_dir():
                self.add_result(DiagnosticResult(
                    category="Filesystem",
                    check_name=f"Directory: {dir_name}",
                    status="pass",
                    message=f"{dir_name}/ 디렉토리 존재"
                ))
            else:
                all_passed = False
                self.add_result(DiagnosticResult(
                    category="Filesystem",
                    check_name=f"Directory: {dir_name}",
                    status="fail",
                    message=f"{dir_name}/ 디렉토리 없음",
                    solution=f"mkdir {dir_name}"
                ))

        # 쓰기 권한 체크
        test_file = Path("data/.write_test")
        try:
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("test")
            test_file.unlink()

            self.add_result(DiagnosticResult(
                category="Filesystem",
                check_name="Write Permission",
                status="pass",
                message="data/ 디렉토리 쓰기 권한 확인"
            ))
        except Exception as e:
            self.add_result(DiagnosticResult(
                category="Filesystem",
                check_name="Write Permission",
                status="fail",
                message="data/ 디렉토리 쓰기 권한 없음",
                details=str(e),
                solution="chmod 755 data/ 또는 관리자 권한으로 실행"
            ))

        return all_passed

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 6. 통합 테스트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def check_integrations(self) -> bool:
        """모듈 간 통합 테스트"""
        logger.info("🔗 통합 테스트 진단 중...")

        # 1. 가상매매 → 메인 DB 연동 테스트
        try:
            from virtual_trading.manager import VirtualTradingManager
            from database import get_db_session, Trade

            manager = VirtualTradingManager()

            # _log_to_main_db 메서드 존재 확인
            if hasattr(manager, '_log_to_main_db'):
                self.add_result(DiagnosticResult(
                    category="Integration",
                    check_name="Virtual Trading → Main DB",
                    status="pass",
                    message="가상매매 메인 DB 연동 기능 확인",
                    details="_log_to_main_db() 메서드 존재"
                ))
            else:
                self.add_result(DiagnosticResult(
                    category="Integration",
                    check_name="Virtual Trading → Main DB",
                    status="warning",
                    message="가상매매 메인 DB 연동 기능 없음",
                    solution="virtual_trading/manager.py 업데이트 필요"
                ))

            manager.close()

        except Exception as e:
            self.add_result(DiagnosticResult(
                category="Integration",
                check_name="Virtual Trading → Main DB",
                status="fail",
                message="가상매매 통합 테스트 실패",
                details=str(e)
            ))

        # 2. 전략진화 → 실제 매매 연동 테스트
        try:
            from ai.strategy_loader import get_strategy_loader

            loader = get_strategy_loader()

            self.add_result(DiagnosticResult(
                category="Integration",
                check_name="Strategy Evolution → Trading",
                status="pass",
                message="전략 로더 초기화 성공",
                details="진화된 전략을 실제 매매에 적용 가능"
            ))

        except Exception as e:
            self.add_result(DiagnosticResult(
                category="Integration",
                check_name="Strategy Evolution → Trading",
                status="warning",
                message="전략 로더 초기화 실패 (선택적 기능)",
                details=str(e),
                solution="python run_strategy_optimizer.py 실행하여 전략 생성"
            ))

        return True

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 전체 진단 실행
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def run_full_diagnostics(self) -> Dict[str, Any]:
        """전체 시스템 진단 실행"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("🔍 AutoTrade Pro - 시스템 자가 진단 시작")
        logger.info("=" * 80)
        logger.info("")

        # 각 카테고리별 진단 실행
        self.check_database()
        self.check_virtual_trading_db()
        self.check_module_imports()
        self.check_configuration()
        self.check_filesystem()
        self.check_integrations()

        # 결과 집계
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "pass")
        warnings = sum(1 for r in self.results if r.status == "warning")
        failed = sum(1 for r in self.results if r.status == "fail")

        duration = (datetime.now() - self.start_time).total_seconds()

        summary = {
            "timestamp": self.start_time.isoformat(),
            "duration_seconds": duration,
            "total_checks": total,
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "success_rate": (passed / total * 100) if total > 0 else 0,
            "overall_status": "healthy" if failed == 0 else "degraded" if warnings > 0 else "critical",
            "results": [asdict(r) for r in self.results]
        }

        # 요약 출력
        logger.info("")
        logger.info("=" * 80)
        logger.info("📊 진단 결과 요약")
        logger.info("=" * 80)
        logger.info(f"✅ 성공: {passed}/{total} ({passed/total*100:.1f}%)")
        logger.info(f"⚠️  경고: {warnings}/{total}")
        logger.info(f"❌ 실패: {failed}/{total}")
        logger.info(f"⏱️  소요시간: {duration:.2f}초")
        logger.info(f"🎯 전체 상태: {summary['overall_status'].upper()}")
        logger.info("=" * 80)

        if failed > 0:
            logger.warning("")
            logger.warning("⚠️  일부 체크가 실패했습니다. 위의 해결방법을 참고하세요.")

        return summary

    def save_report(self, summary: Dict[str, Any], filepath: str = "logs/diagnostics_report.json"):
        """진단 리포트 파일로 저장"""
        try:
            report_path = Path(filepath)
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)

            logger.info(f"📝 진단 리포트 저장: {filepath}")

            # 텍스트 버전도 저장
            txt_path = report_path.with_suffix('.txt')
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"AutoTrade Pro - 시스템 진단 리포트\n")
                f.write(f"생성 시간: {summary['timestamp']}\n")
                f.write("=" * 80 + "\n\n")

                f.write(f"전체 상태: {summary['overall_status'].upper()}\n")
                f.write(f"성공: {summary['passed']}/{summary['total_checks']}\n")
                f.write(f"경고: {summary['warnings']}/{summary['total_checks']}\n")
                f.write(f"실패: {summary['failed']}/{summary['total_checks']}\n\n")

                for result in summary['results']:
                    emoji = "✅" if result['status'] == "pass" else "⚠️" if result['status'] == "warning" else "❌"
                    f.write(f"{emoji} [{result['category']}] {result['check_name']}\n")
                    f.write(f"   {result['message']}\n")
                    if result.get('details'):
                        f.write(f"   상세: {result['details']}\n")
                    if result.get('solution'):
                        f.write(f"   해결: {result['solution']}\n")
                    f.write("\n")

            logger.info(f"📝 텍스트 리포트 저장: {txt_path}")

        except Exception as e:
            logger.error(f"리포트 저장 실패: {e}")


def run_diagnostics(save_to_file: bool = True) -> Dict[str, Any]:
    """
    시스템 진단 실행 (외부에서 호출용)

    Args:
        save_to_file: 파일로 저장 여부

    Returns:
        진단 결과 요약
    """
    diagnostics = SystemDiagnostics()
    summary = diagnostics.run_full_diagnostics()

    if save_to_file:
        diagnostics.save_report(summary)

    return summary


if __name__ == "__main__":
    # 독립 실행
    run_diagnostics(save_to_file=True)
