#!/usr/bin/env python3
"""
통합 API 테스트 스크립트

기능:
1. 주요 ranking API 상세 테스트 (10개)
2. 전체 API 응답 키 자동 탐색 (선택사항, 133개)

사용법:
    python test_all_ranking_apis.py              # 주요 API만 빠르게 테스트
    python test_all_ranking_apis.py --full       # 전체 API 탐색 포함
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import argparse

sys.path.insert(0, str(Path(__file__).parent))

from core.rest_client import KiwoomRESTClient
from api.market import MarketAPI


class TeeOutput:
    """화면과 파일에 동시 출력하는 클래스"""
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, 'w', encoding='utf-8')

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)

    def flush(self):
        self.terminal.flush()
        self.log.flush()

    def close(self):
        self.log.close()
        sys.stdout = self.terminal


def print_header(title):
    """헤더 출력"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


class RankingAPITester:
    """Ranking API 테스터"""

    def __init__(self, market_api):
        self.market_api = market_api
        self.results = []

    def test_api(self, name, api_id, func, *args, **kwargs):
        """단일 API 테스트"""
        print_header(f"{name} ({api_id})")

        try:
            result = func(*args, **kwargs)

            if result and len(result) > 0:
                print(f"✅ 성공! {len(result)}개 조회")

                # 샘플 데이터 출력 (상위 3개)
                if len(result) > 0:
                    print("\n샘플 데이터 (상위 3개):")
                    for i, item in enumerate(result[:3], 1):
                        name_str = item.get('name', 'N/A')

                        # API별로 다른 정보 표시
                        if api_id == 'ka90009':
                            # 외국인기관매매: 순매수 금액
                            net_amt = item.get('net_amount', 0)
                            print(f"  {i}. {name_str} - 순매수금액: {net_amt:,}백만원")
                        elif api_id == 'ka10065':
                            # 장중투자자별매매: 순매수량
                            net_qty = item.get('net_buy_qty', 0)
                            print(f"  {i}. {name_str} - 순매수량: {net_qty:,}주")
                        else:
                            # 기본: 현재가
                            price = item.get('price', 0)
                            print(f"  {i}. {name_str} - 현재가: {price:,}원")

                self.results.append((name, True))
                return True
            else:
                print("❌ 실패: 데이터 없음")
                self.results.append((name, False))
                return False

        except Exception as e:
            print(f"❌ 에러 발생: {e}")
            import traceback
            print(traceback.format_exc())
            self.results.append((name, False))
            return False

    def run_all_tests(self):
        """모든 ranking API 테스트"""
        print_header("주요 Ranking API 테스트 (10개)")

        # 1. 전일거래량상위
        self.test_api(
            "전일거래량상위", "ka10031",
            self.market_api.get_volume_rank,
            market='KOSPI', limit=10
        )

        # 2. 전일대비등락률상위
        self.test_api(
            "전일대비등락률상위", "ka10027",
            self.market_api.get_price_change_rank,
            market='KOSDAQ', sort='rise', limit=10
        )

        # 3. 거래대금상위
        self.test_api(
            "거래대금상위", "ka10032",
            self.market_api.get_trading_value_rank,
            market='KOSPI', limit=10
        )

        # 4. 거래량급증
        self.test_api(
            "거래량급증", "ka10023",
            self.market_api.get_volume_surge_rank,
            market='ALL', limit=10, time_interval=5
        )

        # 5. 시가대비등락률
        self.test_api(
            "시가대비등락률", "ka10028",
            self.market_api.get_intraday_change_rank,
            market='KOSDAQ', sort='rise', limit=10
        )

        # 6. 외국인 기간별 매매
        self.test_api(
            "외국인5일순매수", "ka10034",
            self.market_api.get_foreign_period_trading_rank,
            market='KOSPI', period_days=5, limit=10
        )

        # 7. 외국인 연속 순매매
        self.test_api(
            "외국인연속순매매", "ka10035",
            self.market_api.get_foreign_continuous_trading_rank,
            market='KOSPI', trade_type='buy', limit=10
        )

        # 8. 외국인/기관 매매상위
        self.test_api(
            "외국인기관매매", "ka90009",
            self.market_api.get_foreign_institution_trading_rank,
            market='KOSPI', limit=10
        )

        # 9. 신용비율 상위
        self.test_api(
            "신용비율상위", "ka10033",
            self.market_api.get_credit_ratio_rank,
            market='KOSPI', limit=10
        )

        # 10. 장중 투자자별 매매
        self.test_api(
            "장중투자자별매매", "ka10065",
            self.market_api.get_investor_intraday_trading_rank,
            market='KOSPI', investor_type='foreign', limit=10
        )

    def print_summary(self):
        """결과 요약 출력"""
        print_header("테스트 결과 요약")

        success_count = sum(1 for _, success in self.results if success)
        total_count = len(self.results)

        for name, success in self.results:
            status = "✅ 성공" if success else "❌ 실패"
            print(f"{name:<20} {status}")

        print(f"\n전체: {success_count}/{total_count} 성공")

        if success_count == total_count:
            print("\n🎉 모든 API가 정상 작동합니다!")
        else:
            print(f"\n⚠️  {total_count - success_count}개 API 실패")

        return success_count == total_count


class APIResponseKeyDiscovery:
    """전체 API 응답 키 자동 탐색"""

    def __init__(self, client):
        self.client = client
        self.results = {}
        self.stats = {
            'total_apis': 0,
            'tested_apis': 0,
            'success_with_data': 0,
            'success_no_data': 0,
            'failed': 0,
        }

    def load_successful_apis(self) -> Dict[str, Any]:
        """successful_apis.json 로드"""
        print("전체 API 정의 로드 중...")

        api_specs_path = Path(__file__).parent / '_immutable' / 'api_specs' / 'successful_apis.json'

        try:
            with open(api_specs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                apis = data.get('apis', {})
                print(f"✅ {len(apis)}개 API 정의 로드 완료\n")
                return apis
        except Exception as e:
            print(f"❌ 로드 실패: {e}\n")
            return {}

    def discover_response_key(self, response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """응답에서 데이터가 있는 키 찾기"""
        if not response or response.get('return_code') != 0:
            return None

        metadata_keys = {'return_code', 'return_msg', 'api-id', 'cont-yn', 'next-key'}
        data_keys = [k for k in response.keys() if k not in metadata_keys]

        result = {'data_keys': [], 'total_items': 0, 'key_details': {}}

        for key in data_keys:
            value = response.get(key)

            if isinstance(value, list):
                if len(value) > 0:
                    result['data_keys'].append(key)
                    result['total_items'] += len(value)
                    result['key_details'][key] = {
                        'type': 'list',
                        'count': len(value),
                        'sample_keys': list(value[0].keys()) if value and isinstance(value[0], dict) else []
                    }
            elif isinstance(value, dict):
                if value:
                    result['data_keys'].append(key)
                    result['total_items'] += 1
                    result['key_details'][key] = {'type': 'dict', 'keys': list(value.keys())}
            elif value:
                result['data_keys'].append(key)
                result['total_items'] += 1
                result['key_details'][key] = {'type': type(value).__name__, 'value': str(value)[:100]}

        return result if result['data_keys'] else None

    def test_api(self, api_id: str, api_info: Dict[str, Any]) -> Dict[str, Any]:
        """단일 API 테스트"""
        result = {
            'api_id': api_id,
            'api_name': api_info.get('api_name', ''),
            'category': api_info.get('category', ''),
            'variants': []
        }

        calls = api_info.get('calls', [])

        for call in calls:
            # success, corrected, pending 상태 모두 테스트
            status = call.get('status')
            if status not in ['success', 'corrected', 'pending']:
                continue

            variant_result = {
                'variant_idx': call.get('variant_idx'),
                'path': call.get('path'),
                'body': call.get('body'),
                'call_status': status,  # 원래 상태 기록
                'success': False,
                'has_data': False,
                'response_keys': None
            }

            try:
                response = self.client.request(
                    api_id=api_id,
                    body=call.get('body', {}),
                    path=call.get('path', '')
                )

                if response and response.get('return_code') == 0:
                    variant_result['success'] = True

                    key_info = self.discover_response_key(response)
                    if key_info and key_info['total_items'] > 0:
                        variant_result['has_data'] = True
                        variant_result['response_keys'] = key_info
                        self.stats['success_with_data'] += 1
                    else:
                        self.stats['success_no_data'] += 1
                else:
                    self.stats['failed'] += 1

            except Exception as e:
                variant_result['error'] = str(e)
                self.stats['failed'] += 1

            result['variants'].append(variant_result)
            time.sleep(0.05)

        return result

    def run_discovery(self):
        """전체 API 탐색 실행"""
        print_header("전체 API 응답 키 탐색 (133개)")

        apis = self.load_successful_apis()
        if not apis:
            return

        self.stats['total_apis'] = len(apis)

        by_category = {}
        tested_count = 0

        for api_id, api_info in apis.items():
            category = api_info.get('category', 'unknown')

            print(f"[{tested_count + 1}/{len(apis)}] {api_id} ({api_info.get('api_name', '')})...")

            result = self.test_api(api_id, api_info)

            if category not in by_category:
                by_category[category] = []
            by_category[category].append(result)

            has_data_count = sum(1 for v in result['variants'] if v.get('has_data'))
            total_variants = len(result['variants'])

            if has_data_count > 0:
                print(f"   ✅ {has_data_count}/{total_variants} variants에서 데이터 확인")
            elif any(v.get('success') for v in result['variants']):
                print(f"   ⚠️  성공했지만 데이터 없음")
            else:
                print(f"   ❌ 실패")

            tested_count += 1
            self.stats['tested_apis'] += 1

        self.results = by_category

        # 통계 출력
        print_header("탐색 결과 통계")
        print(f"총 API: {self.stats['total_apis']}")
        print(f"테스트: {self.stats['tested_apis']}")
        print(f"✅ 성공 (데이터 O): {self.stats['success_with_data']}")
        print(f"⚠️  성공 (데이터 X): {self.stats['success_no_data']}")
        print(f"❌ 실패: {self.stats['failed']}")

    def save_results(self):
        """결과 저장"""
        output_path = Path(__file__).parent / '_immutable' / 'api_specs' / 'api_response_keys.json'

        output_data = {
            'metadata': {
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'stats': self.stats,
                'description': 'API 응답 키 탐색 결과 - 실제 데이터가 있는 키만 기록'
            },
            'by_category': self.results
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ JSON 결과 저장: {output_path}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='API 테스트 스크립트')
    parser.add_argument('--full', action='store_true', help='전체 133개 API 탐색 포함')
    args = parser.parse_args()

    # 결과 파일 경로 설정
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(__file__).parent / f"test_all_apis_{timestamp}.txt"

    # 화면과 파일에 동시 출력
    tee = TeeOutput(log_file)
    sys.stdout = tee

    try:
        print("=" * 80)
        print("  통합 API 테스트")
        print("=" * 80)
        print(f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"결과 파일: {log_file}")
        if args.full:
            print("모드: 전체 탐색 (133개 API)")
        else:
            print("모드: 주요 Ranking API만 (10개)")
        print()

        # 클라이언트 초기화
        print("초기화 중...")
        try:
            client = KiwoomRESTClient()
            market_api = MarketAPI(client)
            print("✅ 초기화 완료\n")
        except Exception as e:
            print(f"❌ 초기화 실패: {e}")
            import traceback
            print(traceback.format_exc())
            return 1

        # 1. 주요 Ranking API 테스트
        tester = RankingAPITester(market_api)
        tester.run_all_tests()
        all_success = tester.print_summary()

        # 2. 전체 API 탐색 (옵션)
        if args.full:
            print("\n" + "=" * 80)
            print("전체 API 탐색을 시작합니다...")
            print("=" * 80)

            try:
                discoverer = APIResponseKeyDiscovery(client)
                discoverer.run_discovery()
                discoverer.save_results()
            except Exception as e:
                print(f"\n❌ 탐색 중 에러: {e}")
                import traceback
                print(traceback.format_exc())

        print(f"\n종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"결과: {log_file}")

        return 0 if all_success else 1

    finally:
        tee.close()


if __name__ == '__main__':
    sys.exit(main())
