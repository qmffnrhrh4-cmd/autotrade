#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
분봉 데이터 추출 테스트 - 모든 가능한 방법 시도
실제로 데이터가 받아지는 조건을 찾기 위한 디버깅 스크립트
"""

import os
import sys
import logging
import time
from pathlib import Path

# Set Qt environment before importing
os.environ['QT_API'] = 'pyqt5'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_all_extraction_methods():
    """모든 가능한 데이터 추출 방법 테스트"""

    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QEventLoop, QTimer
    from kiwoom import Kiwoom
    import kiwoom

    # 경고 숨기기
    kiwoom.config.MUTE = True

    # Qt 앱 생성
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    logger.info("=" * 80)
    logger.info("분봉 데이터 추출 테스트 - 모든 방법 시도")
    logger.info("=" * 80)

    # Kiwoom 초기화 및 로그인
    logger.info("\n1️⃣ Kiwoom API 초기화 및 로그인")
    logger.info("-" * 80)

    kiwoom_api = Kiwoom()
    app.processEvents()

    login_complete = {'done': False}

    def on_login(err_code):
        login_complete['done'] = True
        if err_code == 0:
            logger.info("✅ 로그인 성공!")
        else:
            logger.error(f"❌ 로그인 실패: {err_code}")

    kiwoom_api.OnEventConnect.connect(on_login)
    kiwoom_api.CommConnect()

    # 로그인 대기
    timeout = 30
    start = time.time()
    while not login_complete['done'] and (time.time() - start) < timeout:
        app.processEvents()
        time.sleep(0.1)

    if not login_complete['done']:
        logger.error("❌ 로그인 타임아웃")
        return

    # 테스트 시작
    logger.info("\n2️⃣ 분봉 데이터 추출 테스트")
    logger.info("-" * 80)

    stock_code = "005930"  # 삼성전자
    interval = 1  # 1분봉

    logger.info(f"📊 종목: {stock_code}, 간격: {interval}분")
    logger.info("")

    # 가능한 필드명 리스트 (여러 소스에서 수집)
    possible_fields = [
        # 일반적인 필드명
        '체결시간', '현재가', '시가', '고가', '저가', '거래량',
        # 영문 필드명
        'time', 'close', 'open', 'high', 'low', 'volume',
        # 한글 변형
        '시간', '종가', '시작가', '최고가', '최저가', '거래량',
        # opt10080 문서 필드명
        '수정주가구분', '수정비율', '대업종구분', '소업종구분',
        '종목정보', '수정주가이벤트', '전일종가',
        # 다른 가능성
        '일자', '날짜', '등락률', '거래대금',
    ]

    test_results = []

    def test_extraction(test_name, extraction_func):
        """데이터 추출 테스트 실행"""
        logger.info(f"\n{'='*60}")
        logger.info(f"테스트: {test_name}")
        logger.info(f"{'='*60}")

        received_data = {'result': None, 'completed': False}

        def on_receive(scr_no, rq_name, tr_code, record_name, prev_next):
            if rq_name != 'test_minute':
                return

            try:
                logger.info(f"📥 OnReceiveTrData 호출됨")
                logger.info(f"   tr_code: {tr_code}")
                logger.info(f"   rq_name: {rq_name}")
                logger.info(f"   record_name: '{record_name}'")
                logger.info(f"   prev_next: {prev_next}")

                # GetRepeatCnt 확인
                cnt = kiwoom_api.GetRepeatCnt(tr_code, rq_name)
                logger.info(f"   📊 GetRepeatCnt: {cnt}개")

                if cnt == 0:
                    logger.warning("   ⚠️ GetRepeatCnt가 0입니다!")
                    received_data['result'] = {'items': [], 'count': 0}
                    received_data['completed'] = True
                    return

                # 커스텀 추출 함수 실행
                items = extraction_func(kiwoom_api, tr_code, rq_name, cnt)

                received_data['result'] = {
                    'items': items,
                    'count': cnt,
                    'total_extracted': len(items)
                }

                logger.info(f"   ✅ 추출 완료: {len(items)}개 (전체 {cnt}개 중)")

            except Exception as e:
                logger.error(f"   ❌ 오류: {e}")
                import traceback
                traceback.print_exc()
                received_data['result'] = {'error': str(e)}

            received_data['completed'] = True
            if event_loop.isRunning():
                event_loop.quit()

        # 이벤트 핸들러 연결
        kiwoom_api.OnReceiveTrData.connect(on_receive)

        # 입력값 설정
        kiwoom_api.SetInputValue('종목코드', stock_code)
        kiwoom_api.SetInputValue('틱범위', str(interval))
        kiwoom_api.SetInputValue('수정주가구분', '1')

        # TR 요청
        event_loop = QEventLoop()
        ret = kiwoom_api.CommRqData('test_minute', 'opt10080', 0, '0101')

        if ret != 0:
            logger.error(f"   ❌ CommRqData 실패: {ret}")
            try:
                kiwoom_api.OnReceiveTrData.disconnect(on_receive)
            except:
                pass
            return None

        # 타임아웃 설정
        QTimer.singleShot(10000, event_loop.quit)
        event_loop.exec_()

        # 이벤트 핸들러 해제
        try:
            kiwoom_api.OnReceiveTrData.disconnect(on_receive)
        except:
            pass

        result = received_data['result'] if received_data['completed'] else {'error': 'Timeout'}

        # 결과 분석
        if result and 'items' in result:
            items = result['items']
            non_empty_count = len([item for item in items if any(v for v in item.values() if v)])
            logger.info(f"\n📊 결과 분석:")
            logger.info(f"   전체 항목: {len(items)}개")
            logger.info(f"   비어있지 않은 항목: {non_empty_count}개")

            if non_empty_count > 0:
                logger.info(f"\n   ✅ 성공! 비어있지 않은 첫 3개 샘플:")
                count = 0
                for i, item in enumerate(items):
                    if any(v for v in item.values() if v):
                        logger.info(f"      [{i}] {item}")
                        count += 1
                        if count >= 3:
                            break

            test_results.append({
                'name': test_name,
                'success': non_empty_count > 0,
                'total': len(items),
                'non_empty': non_empty_count,
                'sample': items[0] if items else None
            })
        else:
            logger.error(f"   ❌ 데이터 없음 또는 오류: {result}")
            test_results.append({
                'name': test_name,
                'success': False,
                'error': result
            })

        time.sleep(0.3)  # API 제한 준수
        return result

    # ============================================================
    # 테스트 1: 기본 방법 (현재 코드)
    # ============================================================
    def extract_method1(api, tr_code, rq_name, cnt):
        """현재 사용 중인 방법"""
        items = []
        for i in range(min(cnt, 5)):  # 처음 5개만 테스트
            item = {
                '체결시간': api.GetCommData(tr_code, rq_name, i, "체결시간").strip(),
                '현재가': api.GetCommData(tr_code, rq_name, i, "현재가").strip(),
                '시가': api.GetCommData(tr_code, rq_name, i, "시가").strip(),
                '고가': api.GetCommData(tr_code, rq_name, i, "고가").strip(),
                '저가': api.GetCommData(tr_code, rq_name, i, "저가").strip(),
                '거래량': api.GetCommData(tr_code, rq_name, i, "거래량").strip(),
            }
            items.append(item)
        return items

    test_extraction("방법1: 기본 GetCommData (tr_code, rq_name, i, field)", extract_method1)

    # ============================================================
    # 테스트 2: 필드명 순서 변경
    # ============================================================
    def extract_method2(api, tr_code, rq_name, cnt):
        """필드명 순서 변경"""
        items = []
        fields_order = ['거래량', '저가', '고가', '시가', '현재가', '체결시간']
        for i in range(min(cnt, 5)):
            item = {}
            for field in fields_order:
                item[field] = api.GetCommData(tr_code, rq_name, i, field).strip()
            items.append(item)
        return items

    test_extraction("방법2: 필드명 순서 변경 (거래량부터)", extract_method2)

    # ============================================================
    # 테스트 3: 모든 가능한 필드명 시도
    # ============================================================
    def extract_method3(api, tr_code, rq_name, cnt):
        """모든 가능한 필드명 시도"""
        items = []
        for i in range(min(cnt, 3)):  # 처음 3개만
            item = {}
            for field in possible_fields:
                try:
                    value = api.GetCommData(tr_code, rq_name, i, field).strip()
                    if value:  # 값이 있는 것만 저장
                        item[field] = value
                except:
                    pass
            items.append(item)
        return items

    test_extraction("방법3: 모든 가능한 필드명 시도", extract_method3)

    # ============================================================
    # 테스트 4: 인덱스 거꾸로
    # ============================================================
    def extract_method4(api, tr_code, rq_name, cnt):
        """인덱스를 거꾸로 (마지막부터)"""
        items = []
        for i in range(max(0, cnt-5), cnt):  # 마지막 5개
            item = {
                '체결시간': api.GetCommData(tr_code, rq_name, i, "체결시간").strip(),
                '현재가': api.GetCommData(tr_code, rq_name, i, "현재가").strip(),
                '거래량': api.GetCommData(tr_code, rq_name, i, "거래량").strip(),
            }
            items.append(item)
        return items

    test_extraction("방법4: 인덱스 거꾸로 (마지막 5개)", extract_method4)

    # ============================================================
    # 테스트 5: record_name에 빈 문자열 대신 다른 값
    # ============================================================
    def extract_method5(api, tr_code, rq_name, cnt):
        """다양한 접근 (strip 없이, 원본 그대로)"""
        items = []
        for i in range(min(cnt, 5)):
            item = {
                '체결시간_raw': api.GetCommData(tr_code, rq_name, i, "체결시간"),
                '현재가_raw': api.GetCommData(tr_code, rq_name, i, "현재가"),
                '체결시간_strip': api.GetCommData(tr_code, rq_name, i, "체결시간").strip(),
                '현재가_strip': api.GetCommData(tr_code, rq_name, i, "현재가").strip(),
            }
            items.append(item)
        return items

    test_extraction("방법5: strip 유무 비교", extract_method5)

    # ============================================================
    # 테스트 6: GetCommRealData 시도 (실시간 데이터 함수)
    # ============================================================
    def extract_method6(api, tr_code, rq_name, cnt):
        """첫 번째 항목만 모든 필드 출력"""
        items = []
        if cnt > 0:
            logger.info("   🔍 첫 번째 항목 상세 분석:")
            for field in possible_fields:
                try:
                    value = api.GetCommData(tr_code, rq_name, 0, field)
                    if value and value.strip():
                        logger.info(f"      {field}: '{value}' (strip: '{value.strip()}')")
                        items.append({field: value.strip()})
                except Exception as e:
                    pass
        return items

    test_extraction("방법6: 첫 번째 항목 모든 필드 분석", extract_method6)

    # ============================================================
    # 테스트 7: GetDataCount 확인
    # ============================================================
    def extract_method7(api, tr_code, rq_name, cnt):
        """다양한 카운트 함수 확인"""
        logger.info("   🔍 카운트 함수 확인:")
        try:
            repeat_cnt = api.GetRepeatCnt(tr_code, rq_name)
            logger.info(f"      GetRepeatCnt: {repeat_cnt}")
        except Exception as e:
            logger.info(f"      GetRepeatCnt 오류: {e}")

        # 실제 데이터 추출 (기본 방법)
        items = []
        for i in range(min(cnt, 5)):
            item = {
                '체결시간': api.GetCommData(tr_code, rq_name, i, "체결시간").strip(),
                '현재가': api.GetCommData(tr_code, rq_name, i, "현재가").strip(),
            }
            items.append(item)
        return items

    test_extraction("방법7: 카운트 함수 확인", extract_method7)

    # ============================================================
    # 최종 결과 출력
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("📊 최종 결과 요약")
    logger.info("=" * 80)

    for i, result in enumerate(test_results, 1):
        logger.info(f"\n{i}. {result['name']}")
        if result['success']:
            logger.info(f"   ✅ 성공! 비어있지 않은 데이터: {result['non_empty']}/{result['total']}개")
            if result.get('sample'):
                logger.info(f"   샘플: {result['sample']}")
        else:
            logger.info(f"   ❌ 실패")
            if 'error' in result:
                logger.info(f"   오류: {result['error']}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ 모든 테스트 완료!")
    logger.info("=" * 80)


if __name__ == '__main__':
    try:
        test_all_extraction_methods()
    except KeyboardInterrupt:
        logger.info("\n\n중단됨")
    except Exception as e:
        logger.error(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

    logger.info("\n프로그램을 종료하려면 Ctrl+C를 누르세요...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("종료됨")
