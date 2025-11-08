#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
수집된 JSON 파일 상세 분석
"""

import json
from pathlib import Path
from datetime import datetime


def analyze_json_file(filepath):
    """JSON 파일 상세 분석"""
    print(f"\n{'='*80}")
    print(f"  파일: {filepath.name}")
    print(f"{'='*80}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 기본 정보
    print(f"\n📋 기본 정보:")
    print(f"   종목코드: {data.get('stock_code')}")
    print(f"   종목명: {data.get('stock_name')}")
    print(f"   수집시각: {data.get('timestamp')}")
    print(f"   파일크기: {filepath.stat().st_size:,} bytes")

    # 데이터 상세
    stock_data = data.get('data', {})
    print(f"\n📊 수집 데이터: {len(stock_data)}가지")

    for key in sorted(stock_data.keys()):
        value = stock_data[key]

        print(f"\n   [{key}]")

        if isinstance(value, dict):
            # TR 데이터
            if 'trcode' in value:
                trcode = value.get('trcode')
                rqname = value.get('rqname')
                tr_data = value.get('data', {})

                print(f"      TR: {trcode} ({rqname})")

                if isinstance(tr_data, dict):
                    if 'items' in tr_data:
                        # 복수 데이터
                        items = tr_data['items']
                        count = tr_data.get('count', len(items))
                        print(f"      항목 수: {len(items)}개 (전체: {count}개)")

                        if items:
                            print(f"      첫 항목: {items[0]}")
                            if len(items) > 1:
                                print(f"      마지막 항목: {items[-1]}")
                    elif 'error' in tr_data:
                        # 오류
                        print(f"      ❌ 오류: {tr_data['error']}")
                    else:
                        # 단일 데이터
                        print(f"      데이터: {tr_data}")
                else:
                    print(f"      데이터 없음: {tr_data}")
            else:
                # 마스터 정보 등
                print(f"      데이터: {value}")
        else:
            print(f"      값: {value}")

    # JSON 전체 출력 (작은 파일만)
    if filepath.stat().st_size < 1000:
        print(f"\n📄 전체 내용 (파일이 작음):")
        print(json.dumps(data, ensure_ascii=False, indent=2))


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
    print("  수집된 데이터 파일 상세 분석")
    print("="*80)

    print(f"\n총 {len(json_files)}개 파일 발견")

    # 최근 5개 파일만 분석
    for filepath in json_files[:5]:
        try:
            analyze_json_file(filepath)
        except Exception as e:
            print(f"\n❌ 파일 분석 오류: {filepath.name}")
            print(f"   오류: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*80)
    print("  분석 완료")
    print("="*80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n중단됨")
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()
