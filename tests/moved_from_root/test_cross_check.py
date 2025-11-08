"""
크로스 체크 기능 테스트 스크립트
gemini-2.0-flash-exp vs gemini-2.5-flash 비교
"""
import os
import sys
import json
from typing import Dict, Any

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai.gemini_analyzer import GeminiAnalyzer

def print_separator():
    print("\n" + "="*80 + "\n")

def test_cross_check():
    """크로스 체크 테스트"""

    print_separator()
    print("🧪 Gemini AI 크로스 체크 테스트")
    print("gemini-2.0-flash-exp vs gemini-2.5-flash")
    print_separator()

    # API 키 확인
    try:
        from config import GEMINI_API_KEY
        api_key = GEMINI_API_KEY
    except Exception as e:
        print(f"❌ API 키 로드 실패: {e}")
        return

    if not api_key:
        print("❌ GEMINI_API_KEY가 설정되지 않았습니다")
        return

    # 테스트 데이터
    test_stock = {
        'stock_name': '삼성전자',
        'stock_code': '005930',
        'current_price': 70000,
        'change_rate': 2.5,
        'volume': 10000000,
        'institutional_net_buy': 5000000000,
        'foreign_net_buy': 3000000000,
        'bid_ask_ratio': 1.3,
    }

    score_info = {
        'score': 350,
        'percentage': 79.5,
        'breakdown': {
            '기술적분석': 35.0,
            '거래량': 32.0,
            '투자자동향': 38.0,
            '모멘텀': 40.0,
            '변동성': 35.0,
            '상대강도': 38.0,
            '가격위치': 36.0,
            '지지저항': 34.0,
            '추세': 38.0,
            '매물대': 34.0,
        }
    }

    portfolio_info = "삼성전자 100주 보유 중 (+5.2%)"

    print(f"📊 테스트 종목: {test_stock['stock_name']} ({test_stock['stock_code']})")
    print(f"현재가: {test_stock['current_price']:,}원")
    print(f"등락률: {test_stock['change_rate']:+.2f}%")
    print(f"종합 점수: {score_info['score']}/440점 ({score_info['percentage']:.1f}%)")

    # 테스트 1: 크로스 체크 비활성화
    print_separator()
    print("🔹 테스트 1: 일반 모드 (단일 모델)")
    print_separator()

    analyzer_normal = GeminiAnalyzer(api_key=api_key, enable_cross_check=False)

    if not analyzer_normal.initialize():
        print("❌ 분석기 초기화 실패")
        return

    print("분석 시작...")
    result_normal = analyzer_normal.analyze_stock(
        stock_data=test_stock,
        score_info=score_info,
        portfolio_info=portfolio_info
    )

    print(f"\n📋 일반 모드 결과:")
    print(f"  신호: {result_normal.get('signal', 'N/A')}")
    print(f"  신뢰도: {result_normal.get('confidence', 'N/A')}")
    print(f"  이유: {result_normal.get('reasons', ['N/A'])[0][:100]}...")

    # 테스트 2: 크로스 체크 활성화
    print_separator()
    print("🔹 테스트 2: 크로스 체크 모드 (2.0 vs 2.5)")
    print_separator()

    analyzer_cross = GeminiAnalyzer(api_key=api_key, enable_cross_check=True)

    if not analyzer_cross.initialize():
        print("❌ 분석기 초기화 실패")
        return

    print("분석 시작...")
    result_cross = analyzer_cross.analyze_stock(
        stock_data=test_stock,
        score_info=score_info,
        portfolio_info=portfolio_info
    )

    print(f"\n📋 크로스 체크 모드 결과:")
    print(f"  최종 신호: {result_cross.get('signal', 'N/A')}")
    print(f"  최종 신뢰도: {result_cross.get('confidence', 'N/A')}")

    if 'cross_check' in result_cross:
        cc = result_cross['cross_check']
        print(f"\n🔍 크로스 체크 상세:")
        print(f"  - 2.0 모델 신호: {cc.get('model_2_0_signal', 'N/A')}")
        print(f"  - 2.5 모델 신호: {cc.get('model_2_5_signal', 'N/A')}")
        print(f"  - 신호 일치: {'✅ 예' if cc.get('agreement') else '⚠️ 아니오'}")

        if cc.get('agreement'):
            print(f"  - 원래 신뢰도: {cc.get('original_confidence', 'N/A')}")
            print(f"  - 상향 신뢰도: {cc.get('boosted_confidence', 'N/A')}")
        else:
            print(f"  - 선택 이유: {cc.get('reason', 'N/A')}")

    print(f"\n  이유:")
    for i, reason in enumerate(result_cross.get('reasons', [])[:3], 1):
        print(f"    {i}. {reason[:150]}...")

    # 결과 비교
    print_separator()
    print("📊 결과 비교")
    print_separator()

    print(f"일반 모드:       신호={result_normal.get('signal')}, 신뢰도={result_normal.get('confidence')}")
    print(f"크로스 체크 모드: 신호={result_cross.get('signal')}, 신뢰도={result_cross.get('confidence')}")

    if 'cross_check' in result_cross and result_cross['cross_check'].get('agreement'):
        print(f"\n✅ 두 모델이 일치하여 신뢰도가 상향되었습니다!")
    elif 'cross_check' in result_cross:
        print(f"\n⚠️ 두 모델이 불일치하여 보수적으로 선택되었습니다.")

    # 결과를 JSON 파일로 저장
    results = {
        'normal_mode': result_normal,
        'cross_check_mode': result_cross,
        'test_stock': test_stock,
        'score_info': score_info,
    }

    with open('cross_check_test_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print_separator()
    print("💾 테스트 결과가 cross_check_test_results.json에 저장되었습니다")
    print_separator()


if __name__ == '__main__':
    try:
        test_cross_check()
    except KeyboardInterrupt:
        print("\n\n⚠️ 테스트 중단됨")
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
