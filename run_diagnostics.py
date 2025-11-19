#!/usr/bin/env python3
"""
시스템 진단 독립 실행 스크립트
언제든지 실행하여 시스템 상태를 체크할 수 있습니다.

사용법:
    python run_diagnostics.py

리포트:
    - logs/diagnostics_report.json (JSON 형식)
    - logs/diagnostics_report.txt (텍스트 형식)
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.system_diagnostics import run_diagnostics
from utils.logger_new import get_logger

logger = get_logger()


def main():
    """메인 함수"""
    logger.info("")
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "AutoTrade Pro - 시스템 진단 도구".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "═" * 78 + "╝")
    logger.info("")

    try:
        # 진단 실행
        summary = run_diagnostics(save_to_file=True)

        # 결과 출력
        logger.info("")
        if summary['overall_status'] == 'healthy':
            logger.info("🎉 모든 시스템이 정상입니다!")
        elif summary['overall_status'] == 'degraded':
            logger.warning("⚠️  일부 경고가 있지만 시스템은 작동 가능합니다.")
        else:
            logger.error("❌ 심각한 문제가 발견되었습니다. 수정이 필요합니다.")

        logger.info("")
        logger.info(f"📝 상세 리포트:")
        logger.info(f"   - logs/diagnostics_report.json")
        logger.info(f"   - logs/diagnostics_report.txt")
        logger.info("")

        # 종료 코드 설정
        if summary['failed'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        logger.error(f"진단 실행 중 오류 발생: {e}", exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
