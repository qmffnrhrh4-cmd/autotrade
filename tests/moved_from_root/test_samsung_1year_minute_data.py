"""
64비트 Kiwoom Open API - 삼성전자 1년 전 분봉 데이터 조회 테스트

목적:
1. 64비트 Python 3.11.9 환경에서 Kiwoom Open API 작동 확인
2. 삼성전자(005930) 1년 전 분봉 데이터 조회
3. 연속 조회를 통한 대량 데이터 수집

필요사항:
- 64bit-kiwoom-openapi 설치 (https://github.com/teranum/64bit-kiwoom-openapi)
- Python 3.11.9 (64비트)
- pywin32 설치: pip install pywin32
- Kiwoom 계정 로그인

사용 TR:
- OPT10080: 주식분봉조회 (연속 조회 지원)

작성일: 2025-01-07
"""
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import platform

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Python 버전 및 아키텍처 확인
print("="*80)
print(f"Python 버전: {sys.version}")
print(f"Python 아키텍처: {platform.architecture()[0]}")
print(f"권장 버전: Python 3.11.9 (64비트)")
print("="*80 + "\n")

if platform.architecture()[0] != '64bit':
    print("⚠️  경고: 32비트 Python이 감지되었습니다!")
    print("   64비트 Kiwoom OpenAPI를 사용하려면 64비트 Python이 필요합니다.")
    print("   https://www.python.org/downloads/ 에서 64비트 버전을 다운로드하세요.\n")

try:
    import win32com.client
    import pythoncom
except ImportError:
    print("❌ pywin32 모듈이 설치되지 않았습니다!")
    print("   설치 명령: pip install pywin32")
    print("   설치 후 다시 실행해주세요.")
    sys.exit(1)

def check_ocx_registered():
    """OCX 등록 상태 확인"""
    import winreg
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            "KHOPENAPI.KHOpenAPICtrl.1",
            0,
            winreg.KEY_READ
        )
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


class Kiwoom64BitAPI:
    """64비트 Kiwoom Open API 래퍼 - 연속 조회 지원"""

    def __init__(self):
        self.ocx = None
        self.is_connected = False

        # TR 응답 데이터
        self.tr_data = []
        self.prev_next = "0"  # 연속 조회 플래그
        self.tr_completed = False

    def connect(self):
        """ActiveX 연결"""
        try:
            print("🔌 64비트 Kiwoom Open API 연결 시도...\n")

            # OCX 등록 확인
            print("🔍 OCX 등록 상태 확인 중...")
            if not check_ocx_registered():
                print("❌ OCX가 등록되지 않았습니다!")
                print("\n💡 해결 방법:")
                print("   1. 진단 도구 실행:")
                print("      python diagnose_kiwoom_64bit.py")
                print("   2. 관리자 권한으로 OCX 등록:")
                print("      regsvr32 C:\\OpenApi\\KHOpenAPI64.ocx")
                print("   3. 또는 생성된 register_kiwoom_ocx.bat 파일을 관리자 권한으로 실행")
                return False
            print("✅ OCX 등록 확인됨\n")

            # COM 아파트먼트 초기화 (STA 모델 명시)
            pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)

            # ProgID 확인 (DispatchWithEvents 사용)
            try:
                self.ocx = win32com.client.DispatchWithEvents(
                    "KHOPENAPI.KHOpenAPICtrl.1",
                    KiwoomEventHandler
                )
                print("✅ ActiveX 컨트롤 생성 성공 (KHOPENAPI.KHOpenAPICtrl.1)")

                # 전역 인스턴스 설정 (이벤트 핸들러에서 접근)
                global kiwoom_instance
                kiwoom_instance = self

            except Exception as e:
                print(f"❌ ActiveX 컨트롤 생성 실패: {e}")
                print("\n💡 해결 방법:")
                print("   1. 진단 도구 실행:")
                print("      python diagnose_kiwoom_64bit.py")
                print("   2. 64bit-kiwoom-openapi 설치 확인")
                print("   3. 관리자 권한으로 OCX 등록:")
                print("      regsvr32 C:\\OpenApi\\KHOpenAPI64.ocx")
                print("   4. 다른 Kiwoom 프로그램 종료 (HTS, API 등)")
                print("   5. PC 재부팅 후 재시도")
                return False

            return True

        except Exception as e:
            print(f"❌ 연결 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def login(self, timeout=60):
        """로그인"""
        try:
            print("🔐 로그인 시도 중...")
            print("   로그인 창이 나타나면 ID/PW를 입력하세요...\n")

            # 메시지 큐를 먼저 비움
            pythoncom.PumpWaitingMessages()
            time.sleep(0.5)

            ret = self.ocx.CommConnect()

            if ret == 0:
                print("✅ 로그인 요청 전송 완료")
                print(f"   최대 {timeout}초 대기 중...\n")

                # 이벤트 대기 - 메시지 루프를 더 적극적으로 처리
                start_time = time.time()
                while not self.is_connected and (time.time() - start_time) < timeout:
                    pythoncom.PumpWaitingMessages()
                    time.sleep(0.05)  # 더 짧은 간격으로 체크

                if self.is_connected:
                    print("\n✅ 로그인 성공!\n")

                    # 계정 정보 출력
                    try:
                        account_cnt = self.ocx.GetLoginInfo("ACCOUNT_CNT")
                        accounts = self.ocx.GetLoginInfo("ACCNO")
                        user_id = self.ocx.GetLoginInfo("USER_ID")
                        user_name = self.ocx.GetLoginInfo("USER_NM")

                        print("📋 로그인 정보:")
                        print(f"   사용자 ID: {user_id}")
                        print(f"   사용자명: {user_name}")
                        print(f"   보유 계좌수: {account_cnt}")
                        print(f"   계좌번호: {accounts}")
                        print()
                    except Exception as e:
                        print(f"⚠️  로그인 정보 조회 중 오류: {e}")

                    return True
                else:
                    print(f"\n❌ 로그인 시간 초과 ({timeout}초)")
                    print("\n💡 해결 방법:")
                    print("   1. 로그인 창이 표시되지 않았다면:")
                    print("      - 작업 관리자에서 모든 KH* 프로세스 종료")
                    print("      - PC 재부팅")
                    print("   2. 로그인 창은 나타났지만 로그인이 안된다면:")
                    print("      - ID/PW 확인")
                    print("      - 인증서 확인")
                    return False
            else:
                print(f"❌ 로그인 요청 실패 (ret={ret})")
                print("\n💡 가능한 원인:")
                if ret == -100:
                    print("   - 사용자 정보 교환 실패")
                elif ret == -101:
                    print("   - 서버 접속 실패")
                elif ret == -102:
                    print("   - 버전처리 실패")
                else:
                    print(f"   - 알 수 없는 오류 코드: {ret}")
                print("\n   해결: 진단 도구 실행 (python diagnose_kiwoom_64bit.py)")
                return False

        except Exception as e:
            error_code = getattr(e, 'args', [None])[0]
            print(f"❌ 로그인 중 오류: {e}")

            if error_code == -2147418113:  # RPC_E_CALL_REJECTED
                print("\n💡 오류 분석 (0x8001011F = RPC_E_CALL_REJECTED):")
                print("   COM 호출이 거부되었습니다.")
                print("\n   가능한 원인:")
                print("   1. 다른 Kiwoom 프로세스가 이미 COM 객체를 사용 중")
                print("   2. 이전 세션이 완전히 종료되지 않음")
                print("   3. 메시지 큐가 응답하지 않음")
                print("\n   해결 방법:")
                print("   1. 작업 관리자에서 모든 KH* 프로세스 강제 종료:")
                print("      taskkill /F /IM KHOpenAPI.exe")
                print("      taskkill /F /IM KHOpenAPICtrl.exe")
                print("      taskkill /F /IM OpSysMsg.exe")
                print("   2. Python 스크립트 재실행")
                print("   3. 그래도 안되면 PC 재부팅 (권장)")
            else:
                import traceback
                traceback.print_exc()
            return False

    def request_minute_chart(self, stock_code, interval=1, target_count=1000):
        """
        분봉 데이터 연속 조회

        Args:
            stock_code: 종목코드 (6자리)
            interval: 틱범위 (1, 3, 5, 10, 15, 30, 45, 60분)
            target_count: 목표 데이터 개수

        Returns:
            list: 분봉 데이터 리스트
        """
        try:
            print(f"📊 분봉 데이터 연속 조회 시작")
            print(f"   종목코드: {stock_code} (삼성전자)")
            print(f"   틱범위: {interval}분")
            print(f"   목표 개수: {target_count}개")
            print(f"   예상 기간: 약 {target_count * interval / 60 / 24:.1f}일치 데이터\n")

            all_data = []
            request_count = 0
            max_requests = 50  # 최대 요청 횟수 (API 제한 고려)

            while len(all_data) < target_count and request_count < max_requests:
                request_count += 1

                # 초기화
                self.tr_data = []
                self.tr_completed = False

                # 입력값 설정
                self.ocx.SetInputValue("종목코드", stock_code)
                self.ocx.SetInputValue("틱범위", str(interval))
                self.ocx.SetInputValue("수정주가구분", "1")  # 수정주가

                # 연속 조회 플래그 (0: 첫 요청, 2: 연속 요청)
                next_flag = 2 if request_count > 1 else 0

                # 요청
                ret = self.ocx.CommRqData(
                    "주식분봉조회",
                    "OPT10080",
                    next_flag,
                    "0101"
                )

                if ret != 0:
                    print(f"⚠️  TR 요청 실패 (ret={ret})")
                    break

                # 응답 대기
                timeout = 10
                start_time = time.time()

                while not self.tr_completed and (time.time() - start_time) < timeout:
                    pythoncom.PumpWaitingMessages()
                    time.sleep(0.01)

                if not self.tr_completed:
                    print("⚠️  응답 시간 초과")
                    break

                # 데이터 추가
                if self.tr_data:
                    all_data.extend(self.tr_data)
                    print(f"   [{request_count}차] {len(self.tr_data)}개 수신 (누적: {len(all_data)}개)")

                # 연속 조회 플래그 확인
                if self.prev_next != "2":
                    print(f"   → 마지막 페이지 도달 (prev_next={self.prev_next})")
                    break

                # API 호출 간격 (초당 5건 제한)
                time.sleep(0.25)

            print(f"\n✅ 총 {len(all_data)}개 데이터 수신 완료")

            if len(all_data) > 0:
                # 데이터 기간 확인
                first_date = all_data[0]['date']
                last_date = all_data[-1]['date']

                print(f"   기간: {last_date} ~ {first_date}")

                # 1년 전 데이터 포함 여부 확인
                one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
                if last_date[:8] <= one_year_ago:
                    print(f"   🎉 1년 전 데이터 포함! (목표: {one_year_ago}, 실제: {last_date[:8]})")
                else:
                    print(f"   📅 최대 조회 가능: {last_date[:8]} (1년 전: {one_year_ago})")

            return all_data

        except Exception as e:
            print(f"❌ TR 요청 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return []

    def print_data_summary(self, data, max_rows=10):
        """데이터 요약 출력"""
        if not data:
            print("⚠️  출력할 데이터가 없습니다.")
            return

        print(f"\n{'='*100}")
        print(f"📈 분봉 데이터 샘플 (총 {len(data)}개 중 최근 {min(max_rows, len(data))}개)")
        print(f"{'='*100}")

        # 헤더
        print(f"{'일자':12} {'시각':8} {'현재가':>12} {'시가':>12} {'고가':>12} "
              f"{'저가':>12} {'거래량':>12}")
        print("-" * 100)

        # 데이터 출력 (최근 데이터부터)
        for i, item in enumerate(data[:max_rows]):
            date_str = item['date']
            date_part = date_str[:8] if len(date_str) >= 8 else date_str
            time_part = date_str[8:] if len(date_str) > 8 else ""

            print(f"{date_part:12} {time_part:8} "
                  f"{item['close']:>12,} {item['open']:>12,} {item['high']:>12,} "
                  f"{item['low']:>12,} {item['volume']:>12,}")

        print("=" * 100)

        # 통계 정보
        if len(data) > 0:
            prices = [d['close'] for d in data if d['close'] > 0]
            if prices:
                print(f"\n📊 통계 정보:")
                print(f"   최고가: {max(prices):,}원")
                print(f"   최저가: {min(prices):,}원")
                print(f"   평균가: {sum(prices)//len(prices):,}원")
                print(f"   데이터 개수: {len(data):,}개")

    def save_to_csv(self, data, filename="samsung_minute_data.csv"):
        """CSV 파일로 저장"""
        try:
            import csv

            filepath = project_root / filename

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'open', 'high', 'low', 'close', 'volume'])
                writer.writeheader()
                writer.writerows(data)

            print(f"\n💾 CSV 저장 완료: {filepath}")
            print(f"   파일 크기: {filepath.stat().st_size:,} bytes")

        except Exception as e:
            print(f"❌ CSV 저장 실패: {e}")


class KiwoomEventHandler:
    """Kiwoom API 이벤트 핸들러"""

    def OnEventConnect(self, err_code):
        """로그인 결과 이벤트"""
        global kiwoom_instance

        if err_code == 0:
            print("   ✅ [이벤트] 로그인 성공")
            kiwoom_instance.is_connected = True
        else:
            print(f"   ❌ [이벤트] 로그인 실패 (err_code={err_code})")
            kiwoom_instance.is_connected = False

    def OnReceiveTrData(self, screen_no, rqname, trcode, record_name, prev_next,
                        data_len, err_code, msg, splm_msg):
        """TR 데이터 수신 이벤트"""
        global kiwoom_instance

        if rqname == "주식분봉조회":
            # 연속 조회 플래그 저장
            kiwoom_instance.prev_next = prev_next

            # 데이터 개수 확인
            cnt = kiwoom_instance.ocx.GetRepeatCnt(trcode, rqname)

            # 데이터 파싱
            for i in range(cnt):
                try:
                    data = {
                        'date': kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "체결시간").strip(),
                        'open': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "시가").strip() or 0),
                        'high': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "고가").strip() or 0),
                        'low': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "저가").strip() or 0),
                        'close': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "현재가").strip() or 0),
                        'volume': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "거래량").strip() or 0),
                    }
                    kiwoom_instance.tr_data.append(data)
                except Exception as e:
                    print(f"   ⚠️  데이터 파싱 오류: {e}")

            kiwoom_instance.tr_completed = True


def print_section(title):
    """섹션 구분선"""
    print(f"\n{'='*100}")
    print(f"  {title}")
    print(f"{'='*100}\n")


def main():
    """메인 테스트 함수"""

    print_section("🚀 삼성전자 1년 전 분봉 데이터 조회 테스트")

    # API 생성
    kiwoom = Kiwoom64BitAPI()

    # 연결
    if not kiwoom.connect():
        print("\n❌ ActiveX 연결 실패")
        print("\n💡 해결 방법:")
        print("   1. https://github.com/teranum/64bit-kiwoom-openapi 에서 설치")
        print("   2. 관리자 권한으로 OCX 등록")
        print("   3. 다른 Kiwoom 프로그램 종료")
        return

    # 로그인
    if not kiwoom.login(timeout=60):
        print("\n❌ 로그인 실패")
        return

    print_section("📊 삼성전자(005930) 분봉 데이터 수집")

    # 테스트 1: 1분봉 1000개 조회 (약 16시간치)
    print("🔍 테스트 1: 1분봉 1000개 조회 (약 2~3 거래일)")
    data_1min = kiwoom.request_minute_chart(
        stock_code="005930",
        interval=1,
        target_count=1000
    )

    if data_1min:
        kiwoom.print_data_summary(data_1min, max_rows=10)
        kiwoom.save_to_csv(data_1min, "samsung_1min_data.csv")

    print("\n" + "─"*100 + "\n")
    time.sleep(1)

    # 테스트 2: 60분봉 1000개 조회 (약 2~3개월치)
    print("🔍 테스트 2: 60분봉 1000개 조회 (약 2~3개월)")
    data_60min = kiwoom.request_minute_chart(
        stock_code="005930",
        interval=60,
        target_count=1000
    )

    if data_60min:
        kiwoom.print_data_summary(data_60min, max_rows=10)
        kiwoom.save_to_csv(data_60min, "samsung_60min_data.csv")

    print_section("📊 테스트 결과 요약")

    print(f"✅ 1분봉 데이터: {len(data_1min):,}개")
    print(f"✅ 60분봉 데이터: {len(data_60min):,}개\n")

    # 1년 전 데이터 확인
    one_year_ago = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

    has_1year_data_1min = False
    has_1year_data_60min = False

    if data_1min and len(data_1min) > 0:
        oldest_date_1min = data_1min[-1]['date'][:8]
        has_1year_data_1min = oldest_date_1min <= one_year_ago
        print(f"📅 1분봉 최대 조회일: {oldest_date_1min} (1년 전: {one_year_ago})")

    if data_60min and len(data_60min) > 0:
        oldest_date_60min = data_60min[-1]['date'][:8]
        has_1year_data_60min = oldest_date_60min <= one_year_ago
        print(f"📅 60분봉 최대 조회일: {oldest_date_60min} (1년 전: {one_year_ago})")

    print_section("💡 결론 및 권장사항")

    if has_1year_data_1min or has_1year_data_60min:
        print("🎉 1년 전 데이터 조회 성공!\n")
        print("✅ 확인된 사항:")
        print("   - 64비트 Python 3.11.9에서 Open API 정상 작동")
        print("   - 연속 조회를 통한 대량 데이터 수집 가능")
        print("   - 1년 전 과거 데이터 조회 가능")
        print("\n💡 다음 단계:")
        print("   1. 더 많은 데이터를 원하면 target_count를 증가 (최대 ~10000)")
        print("   2. 여러 종목으로 확장")
        print("   3. DB 저장 로직 추가 (SQLite, PostgreSQL 등)")
        print("   4. 스케줄러로 정기적 데이터 수집")
    else:
        print("⚠️  1년 전 데이터 조회 제한\n")
        print("확인 사항:")
        print(f"   - 1분봉 최대: {data_1min[-1]['date'][:8] if data_1min else 'N/A'}")
        print(f"   - 60분봉 최대: {data_60min[-1]['date'][:8] if data_60min else 'N/A'}")
        print("\n💡 대안:")
        print("   1. API 제한으로 1년 전 데이터가 없을 수 있음")
        print("   2. 오늘부터 매일 데이터 수집 시작")
        print("   3. 시간이 지나면서 히스토리 누적")
        print("   4. 또는 Kiwoom API 데이터 제공 기간 확인 필요")

    print("\n" + "="*100)


if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║      🚀 64비트 Kiwoom Open API - 삼성전자 1년 전 분봉 데이터 조회 테스트                  ║
║                                                                                      ║
║  환경: Python 3.11.9 (64비트)                                                         ║
║  종목: 삼성전자 (005930)                                                              ║
║  목적: 1년 전 과거 분봉 데이터 조회 가능 여부 확인                                        ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
""")

    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 테스트를 중단했습니다.")
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류 발생:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()

    print("\n테스트 종료. 창을 닫으려면 Enter를 누르세요...")
    input()
