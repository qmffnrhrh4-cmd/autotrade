#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAPI 데이터 수집 결과 검증 스크립트
tests/ 폴더의 JSON 파일을 분석하여 데이터 품질을 확인합니다.
"""

import json
from pathlib import Path
from datetime import datetime


def verify_data_quality():
    """수집된 데이터 품질 검증"""

    print("=" * 80)
    print("  OpenAPI 데이터 수집 결과 검증")
    print("=" * 80)

    tests_dir = Path("tests")

    # 1. 최근 생성된 JSON 파일 찾기
    print("\n📁 1. 파일 검색...")
    json_files = list(tests_dir.glob("stock_*.json"))

    if not json_files:
        print("   ❌ tests/ 폴더에 수집 결과 파일이 없습니다.")
        print("\n💡 먼저 다음 명령어로 데이터를 수집하세요:")
        print("   conda activate kiwoom32")
        print("   python test_stock_comprehensive_20.py")
        return False

    # 최근 파일 정렬
    json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    print(f"   ✅ 총 {len(json_files)}개 파일 발견")
    print(f"\n   최근 파일 (최대 5개):")
    for i, file in enumerate(json_files[:5], 1):
        mtime = datetime.fromtimestamp(file.stat().st_mtime)
        size = file.stat().st_size
        print(f"   {i}. {file.name}")
        print(f"      생성: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      크기: {size:,} bytes")

    # 2. 최근 파일 분석
    print(f"\n📊 2. 데이터 분석...")

    recent_files = [f for f in json_files if 'summary' not in f.name][:3]

    if not recent_files:
        print("   ⚠️  종목별 데이터 파일 없음 (summary만 있음)")
        return False

    total_stats = {
        'files': 0,
        'stocks': [],
        'total_data_types': 0,
        'success_rate': 0,
        'errors': []
    }

    for file_path in recent_files:
        print(f"\n   📄 {file_path.name}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            stock_code = data.get('stock_code', 'Unknown')
            stock_name = data.get('stock_name', 'Unknown')
            timestamp = data.get('timestamp', 'Unknown')
            stock_data = data.get('data', {})

            print(f"      종목: {stock_code} ({stock_name})")
            print(f"      수집 시각: {timestamp}")
            print(f"      데이터 종류: {len(stock_data)}가지")

            total_stats['files'] += 1
            total_stats['stocks'].append(f"{stock_code}({stock_name})")
            total_stats['total_data_types'] += len(stock_data)

            # 데이터 상세 분석
            empty_count = 0
            error_count = 0
            success_count = 0

            for key, value in stock_data.items():
                if not value:
                    empty_count += 1
                elif isinstance(value, dict):
                    if 'error' in value:
                        error_count += 1
                        total_stats['errors'].append(f"{stock_name} - {key}: {value.get('error')}")
                    elif value.get('data'):
                        success_count += 1
                    else:
                        empty_count += 1
                else:
                    success_count += 1

            print(f"      성공: {success_count}개 ✅")
            if empty_count > 0:
                print(f"      비어있음: {empty_count}개 ⚠️")
            if error_count > 0:
                print(f"      오류: {error_count}개 ❌")

            # 주요 데이터 샘플 표시
            print(f"\n      🔍 주요 데이터 샘플:")

            # 마스터 정보
            if '01_마스터' in stock_data:
                master = stock_data['01_마스터']
                print(f"         마스터: {master}")

            # 주식기본정보
            if '02_주식기본정보' in stock_data:
                basic = stock_data['02_주식기본정보']
                if 'data' in basic and isinstance(basic['data'], dict):
                    sample = {k: v for k, v in list(basic['data'].items())[:3]}
                    print(f"         기본정보: {sample}...")

            # 일봉차트
            if '04_일봉차트' in stock_data:
                chart = stock_data['04_일봉차트']
                if 'data' in chart and 'items' in chart['data']:
                    items = chart['data']['items']
                    print(f"         일봉차트: {len(items)}개 항목")
                    if items:
                        print(f"            첫 항목: {items[0]}")

        except json.JSONDecodeError as e:
            print(f"      ❌ JSON 파싱 오류: {e}")
            total_stats['errors'].append(f"{file_path.name}: JSON 파싱 실패")
        except Exception as e:
            print(f"      ❌ 오류: {e}")
            total_stats['errors'].append(f"{file_path.name}: {str(e)}")

    # 3. 전체 요약
    print("\n" + "=" * 80)
    print("  📈 전체 요약")
    print("=" * 80)

    print(f"\n   분석 파일: {total_stats['files']}개")
    print(f"   종목: {', '.join(total_stats['stocks'])}")
    print(f"   총 데이터 종류: {total_stats['total_data_types']}개")

    if total_stats['files'] > 0:
        avg_data = total_stats['total_data_types'] / total_stats['files']
        print(f"   평균 데이터 종류: {avg_data:.1f}개/종목")

        if avg_data >= 18:
            print(f"   ✅ 우수: 대부분의 데이터 수집 성공")
        elif avg_data >= 15:
            print(f"   ⚠️  양호: 일부 데이터 누락")
        elif avg_data >= 10:
            print(f"   ⚠️  보통: 많은 데이터 누락")
        else:
            print(f"   ❌ 불량: 대부분의 데이터 수집 실패")

    if total_stats['errors']:
        print(f"\n   ❌ 오류 목록 ({len(total_stats['errors'])}개):")
        for error in total_stats['errors'][:5]:
            print(f"      - {error}")
        if len(total_stats['errors']) > 5:
            print(f"      ... 외 {len(total_stats['errors']) - 5}개")
    else:
        print(f"\n   ✅ 오류 없음!")

    # 4. 권장사항
    print("\n" + "=" * 80)
    print("  💡 권장사항")
    print("=" * 80)

    if total_stats['files'] == 0:
        print("\n   1. 먼저 데이터를 수집하세요:")
        print("      conda activate kiwoom32")
        print("      python test_stock_comprehensive_20.py")
    elif avg_data < 15:
        print("\n   1. 일부 데이터 수집 실패")
        print("      - 장 시간 (09:00-15:30)에 다시 시도")
        print("      - 일부 TR 코드는 권한 필요할 수 있음")
        print("      - 주말/공휴일에는 일부 데이터 제공 안됨")
    else:
        print("\n   ✅ 데이터 수집 성공!")
        print("\n   다음 단계:")
        print("   1. main.py에 데이터 통합")
        print("   2. AI 분석 모듈과 연동")
        print("   3. 실시간 데이터 스트림 구현")

    print("\n")
    return True


if __name__ == '__main__':
    try:
        verify_data_quality()
    except KeyboardInterrupt:
        print("\n\n중단됨")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
