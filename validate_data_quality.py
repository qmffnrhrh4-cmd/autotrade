#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAPI 데이터 품질 검증 스크립트
- 빈 문자열, 공백 체크
- 각 TR별 필수 필드 검증
- 데이터 품질 점수 계산
"""

import json
from pathlib import Path
from datetime import datetime


# 각 TR별 필수 필드 정의
TR_REQUIRED_FIELDS = {
    '01_마스터': ['종목명', '현재가', '상장주식수'],
    '02_주식기본정보': ['종목명', '현재가', '거래량'],
    '03_호가잔량': ['매도호가1', '매수호가1'],
    '04_일봉차트': ['items'],  # items 배열 필수
    '05_분봉차트': ['items'],
    '06_주식거래량': ['items'],
    '07_체결정보': ['items'],
    '08_시세표성정보': ['종목명', '현재가'],
    '09_전일대비등락률': ['items'],
    '10_투자자별매매동향': ['items'],
    '11_종목별투자자기관': ['items'],
    '12_외인기관종목별매매': ['items'],
    '13_프로그램매매종목별': ['items'],
    '14_시간대별체결가': ['items'],
    '15_일자별매매상위': ['items'],
    '16_월별투자자매매': ['items'],
    '17_신용잔고': ['신용잔고율'],
    '18_시간대별체결조회': ['items'],
    '19_외인기관순매매': ['items'],
    '20_일별체결정보': ['items'],
}


def is_valid_value(value):
    """값이 유효한지 확인 (빈 문자열, 공백, None 제외)"""
    if value is None:
        return False
    if isinstance(value, str):
        # 빈 문자열이거나 공백만 있으면 무효
        return len(value.strip()) > 0
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, list):
        return len(value) > 0
    return bool(value)


def validate_single_data(data_dict):
    """단일 데이터 검증"""
    valid_count = 0
    total_count = len(data_dict)

    for key, value in data_dict.items():
        if is_valid_value(value):
            valid_count += 1

    return valid_count, total_count


def validate_items_data(items):
    """복수 데이터(items) 검증"""
    if not items or len(items) == 0:
        return 0, 0, []

    total_items = len(items)
    valid_items = 0
    empty_fields_summary = {}

    for item in items:
        # 각 아이템에서 유효한 필드 수 카운트
        valid_fields = 0
        total_fields = len(item)

        for key, value in item.items():
            if is_valid_value(value):
                valid_fields += 1
            else:
                # 빈 필드 추적
                if key not in empty_fields_summary:
                    empty_fields_summary[key] = 0
                empty_fields_summary[key] += 1

        # 50% 이상 필드가 채워졌으면 유효한 아이템
        if total_fields > 0 and valid_fields / total_fields >= 0.5:
            valid_items += 1

    return valid_items, total_items, empty_fields_summary


def validate_tr_data(tr_key, tr_data):
    """TR 데이터 검증"""
    result = {
        'tr_key': tr_key,
        'status': 'unknown',
        'quality_score': 0.0,
        'details': '',
        'issues': []
    }

    # 데이터가 없음
    if not tr_data:
        result['status'] = 'no_data'
        result['details'] = '데이터 없음'
        return result

    # 오류가 있음
    if isinstance(tr_data, dict) and 'error' in tr_data:
        result['status'] = 'error'
        result['details'] = f"오류: {tr_data.get('error')}"
        return result

    # TR 데이터 구조 확인
    if isinstance(tr_data, dict):
        # 마스터 정보 (직접 필드)
        if tr_key == '01_마스터':
            valid, total = validate_single_data(tr_data)
            result['quality_score'] = (valid / total * 100) if total > 0 else 0
            result['details'] = f"{valid}/{total} 필드 유효"

            # 필수 필드 체크
            required = TR_REQUIRED_FIELDS.get(tr_key, [])
            missing = [f for f in required if not is_valid_value(tr_data.get(f))]
            if missing:
                result['issues'].append(f"필수 필드 누락: {', '.join(missing)}")
                result['status'] = 'incomplete'
            else:
                result['status'] = 'valid' if result['quality_score'] >= 80 else 'partial'

        # TR 응답 구조 (trcode, data 포함)
        elif 'trcode' in tr_data:
            data = tr_data.get('data', {})

            # 복수 데이터 (items)
            if isinstance(data, dict) and 'items' in data:
                items = data['items']
                valid_items, total_items, empty_fields = validate_items_data(items)

                result['quality_score'] = (valid_items / total_items * 100) if total_items > 0 else 0
                result['details'] = f"{valid_items}/{total_items} 항목 유효"

                if total_items == 0:
                    result['status'] = 'no_data'
                    result['issues'].append("항목이 0개")
                elif result['quality_score'] >= 80:
                    result['status'] = 'valid'
                elif result['quality_score'] >= 50:
                    result['status'] = 'partial'
                    result['issues'].append(f"{total_items - valid_items}개 항목 불완전")
                else:
                    result['status'] = 'incomplete'
                    result['issues'].append(f"대부분 항목 불완전 ({result['quality_score']:.0f}%)")

                # 빈 필드 요약
                if empty_fields:
                    top_empty = sorted(empty_fields.items(), key=lambda x: x[1], reverse=True)[:3]
                    empty_summary = ", ".join([f"{k}({v}개)" for k, v in top_empty])
                    result['issues'].append(f"빈 필드: {empty_summary}")

            # 단일 데이터
            elif isinstance(data, dict):
                valid, total = validate_single_data(data)
                result['quality_score'] = (valid / total * 100) if total > 0 else 0
                result['details'] = f"{valid}/{total} 필드 유효"

                # 필수 필드 체크
                required = TR_REQUIRED_FIELDS.get(tr_key, [])
                missing = [f for f in required if not is_valid_value(data.get(f))]
                if missing:
                    result['issues'].append(f"필수 필드 누락: {', '.join(missing)}")

                if total == 0:
                    result['status'] = 'no_data'
                elif result['quality_score'] >= 80:
                    result['status'] = 'valid'
                elif result['quality_score'] >= 50:
                    result['status'] = 'partial'
                else:
                    result['status'] = 'incomplete'
            else:
                result['status'] = 'invalid_structure'
                result['details'] = f"잘못된 데이터 구조: {type(data)}"
        else:
            result['status'] = 'invalid_structure'
            result['details'] = "TR 응답 구조 없음"
    else:
        result['status'] = 'invalid_type'
        result['details'] = f"잘못된 타입: {type(tr_data)}"

    return result


def analyze_file_quality(filepath):
    """파일 품질 분석"""
    print(f"\n{'='*80}")
    print(f"  파일: {filepath.name}")
    print(f"{'='*80}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stock_code = data.get('stock_code', 'Unknown')
    stock_name = data.get('stock_name', 'Unknown')
    timestamp = data.get('timestamp', 'Unknown')
    stock_data = data.get('data', {})

    print(f"\n📋 기본 정보:")
    print(f"   종목: {stock_code} ({stock_name})")
    print(f"   수집 시각: {timestamp}")
    print(f"   파일 크기: {filepath.stat().st_size:,} bytes")
    print(f"   데이터 종류: {len(stock_data)}가지")

    # 각 TR 데이터 검증
    validation_results = []

    for tr_key in sorted(stock_data.keys()):
        tr_data = stock_data[tr_key]
        result = validate_tr_data(tr_key, tr_data)
        validation_results.append(result)

    # 상태별 카운트
    status_counts = {
        'valid': 0,      # 완전
        'partial': 0,    # 부분적
        'incomplete': 0, # 불완전
        'no_data': 0,    # 데이터 없음
        'error': 0,      # 오류
        'unknown': 0     # 알 수 없음
    }

    total_quality = 0

    for result in validation_results:
        status = result['status']
        status_counts[status] = status_counts.get(status, 0) + 1
        total_quality += result['quality_score']

    avg_quality = total_quality / len(validation_results) if validation_results else 0

    # 결과 출력
    print(f"\n📊 데이터 품질 분석:")
    print(f"   전체 품질 점수: {avg_quality:.1f}%")
    print(f"   ✅ 완전: {status_counts['valid']}개")
    print(f"   ⚠️  부분적: {status_counts['partial']}개")
    print(f"   ❌ 불완전: {status_counts['incomplete']}개")
    print(f"   💨 데이터없음: {status_counts['no_data']}개")
    print(f"   🚫 오류: {status_counts['error']}개")

    # 상세 내역
    print(f"\n📝 상세 내역:")
    for result in validation_results:
        status_icon = {
            'valid': '✅',
            'partial': '⚠️ ',
            'incomplete': '❌',
            'no_data': '💨',
            'error': '🚫',
            'unknown': '❓'
        }.get(result['status'], '❓')

        print(f"\n   {status_icon} [{result['tr_key']}]")
        print(f"      상태: {result['status']}")
        print(f"      품질: {result['quality_score']:.0f}%")
        print(f"      {result['details']}")

        if result['issues']:
            for issue in result['issues']:
                print(f"      ⚠️  {issue}")

    return {
        'stock_code': stock_code,
        'stock_name': stock_name,
        'avg_quality': avg_quality,
        'status_counts': status_counts,
        'total_count': len(validation_results),
        'validation_results': validation_results
    }


def main():
    """메인"""
    tests_dir = Path("tests")

    # 최근 JSON 파일 찾기
    json_files = sorted(tests_dir.glob("stock_*.json"),
                       key=lambda x: x.stat().st_mtime,
                       reverse=True)

    if not json_files:
        print("❌ tests/ 폴더에 JSON 파일이 없습니다.")
        return

    print("="*80)
    print("  OpenAPI 데이터 품질 검증 (엄격 모드)")
    print("  - 빈 문자열/공백 체크")
    print("  - 필수 필드 검증")
    print("  - 데이터 품질 점수")
    print("="*80)

    print(f"\n총 {len(json_files)}개 파일 발견")

    # 최근 파일들만 분석 (complete20)
    recent_files = [f for f in json_files if 'complete20' in f.name][:3]

    if not recent_files:
        print("\n⚠️  complete20 파일이 없습니다. 최근 파일 3개 분석:")
        recent_files = json_files[:3]

    all_results = []

    for filepath in recent_files:
        try:
            result = analyze_file_quality(filepath)
            all_results.append(result)
        except Exception as e:
            print(f"\n❌ 파일 분석 오류: {filepath.name}")
            print(f"   오류: {e}")
            import traceback
            traceback.print_exc()

    # 전체 요약
    if all_results:
        print("\n" + "="*80)
        print("  📈 전체 요약")
        print("="*80)

        total_quality = sum(r['avg_quality'] for r in all_results)
        avg_quality = total_quality / len(all_results)

        print(f"\n   분석 파일: {len(all_results)}개")
        print(f"   전체 평균 품질: {avg_quality:.1f}%")

        for r in all_results:
            print(f"\n   {r['stock_code']} ({r['stock_name']}): {r['avg_quality']:.1f}%")
            print(f"      ✅ 완전: {r['status_counts']['valid']}개")
            print(f"      ⚠️  부분: {r['status_counts']['partial']}개")
            print(f"      ❌ 불완전: {r['status_counts']['incomplete']}개")
            print(f"      💨 없음: {r['status_counts']['no_data']}개")
            print(f"      🚫 오류: {r['status_counts']['error']}개")

        # 평가
        print("\n" + "="*80)
        print("  💡 평가")
        print("="*80)

        if avg_quality >= 85:
            print("\n   ✅ 우수: 대부분의 데이터가 완전히 수집됨")
        elif avg_quality >= 70:
            print("\n   ⚠️  양호: 데이터 수집되었으나 일부 필드 누락")
        elif avg_quality >= 50:
            print("\n   ⚠️  보통: 많은 필드가 빈 값이거나 누락됨")
        else:
            print("\n   ❌ 불량: 대부분의 데이터가 불완전")

        print("\n   권장사항:")
        if avg_quality < 70:
            print("   - 장 시간(09:00-15:30)에 실행")
            print("   - 일부 TR은 특정 시간대에만 데이터 제공")
            print("   - 주말/공휴일에는 일부 데이터 제한")
        else:
            print("   - 데이터 품질 우수!")
            print("   - main.py 통합 준비 완료")

    print("\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n중단됨")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
