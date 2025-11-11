"""
64비트 Open API 로그인 및 과거 분봉 데이터 조회 테스트

목적:
1. 64비트 환경에서 Open API 로그인 성공
2. 과거 분봉 데이터 조회 테스트
"""
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import win32com.client
    import pythoncom
    import pywintypes
except ImportError:
    print("❌ pywin32 모듈이 설치되지 않았습니다!")
    print("   pip install pywin32 실행하세요")
    sys.exit(1)


class KiwoomAPI64:
    """64비트 Kiwoom Open API 래퍼 클래스"""

    def __init__(self):
        self.ocx = None
        self.connected = False
        self.login_event = threading.Event()
        self.tr_event = threading.Event()
        self.tr_data = {}

    def print_header(self, title):
        """섹션 헤더 출력"""
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")

    def initialize(self):
        """API 초기화"""
        self.print_header("🚀 Kiwoom 64비트 Open API 초기화")

        try:
            # COM 초기화
            pythoncom.CoInitialize()
            print("✅ COM 초기화 성공")

            # ActiveX 컨트롤 생성
            self.ocx = win32com.client.DispatchWithEvents(
                "KHOPENAPI.KHOpenAPICtrl.1",
                KiwoomEventHandler
            )
            print("✅ ActiveX 컨트롤 생성 성공")

            # 이벤트 핸들러에 부모 객체 연결
            self.ocx.parent = self

            # API 모듈 경로 출력
            try:
                module_path = self.ocx.GetAPIModulePath()
                print(f"   API 모듈 경로: {module_path}")
            except:
                pass

            return True

        except Exception as e:
            print(f"❌ 초기화 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def connect(self, timeout=30):
        """로그인 (타임아웃 포함)"""
        self.print_header("🔐 로그인 시도")

        try:
            self.login_event.clear()

            # CommConnect 호출
            ret = self.ocx.CommConnect()
            print(f"CommConnect 반환값: {ret}")

            if ret != 0:
                print(f"❌ CommConnect 호출 실패: {ret}")
                return False

            print("✅ CommConnect 호출 성공")
            print("   로그인 창이 나타나면 ID/PW를 입력하세요...")
            print(f"   최대 {timeout}초 대기합니다.")

            # 메시지 루프를 별도 스레드에서 실행
            message_thread = threading.Thread(target=self._message_loop, daemon=True)
            message_thread.start()

            # 로그인 이벤트 대기
            if self.login_event.wait(timeout):
                if self.connected:
                    print("\n✅ 로그인 성공!")
                    return True
                else:
                    print("\n❌ 로그인 실패")
                    return False
            else:
                print(f"\n❌ 타임아웃: {timeout}초 내에 로그인하지 못했습니다")
                return False

        except pywintypes.com_error as e:
            print(f"\n❌ COM 오류 발생:")
            print(f"   오류 코드: {e.args[0]} (0x{e.args[0] & 0xFFFFFFFF:08X})")
            print(f"   오류 메시지: {e.args[1]}")

            error_code = e.args[0] & 0xFFFFFFFF

            if error_code == 0x8000FFFF:
                print("\n💡 오류 분석 (0x8000FFFF = E_UNEXPECTED):")
                print("   가능한 원인:")
                print("   1. 다른 Kiwoom 프로그램이 이미 실행 중 (HTS 영웅문 등)")
                print("   2. 로그인 서버 연결 실패")
                print("   3. OCX 파일 권한 문제")
                print("   4. 방화벽/백신 프로그램 차단")
                print()
                print("   해결 방법:")
                print("   1. 작업 관리자에서 KH로 시작하는 모든 프로세스 종료")
                print("   2. Python 인터프리터 재시작")
                print("   3. 관리자 권한으로 실행")
                print("   4. 재부팅 후 재시도")

            return False

        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _message_loop(self):
        """메시지 루프 (별도 스레드에서 실행)"""
        while True:
            pythoncom.PumpWaitingMessages()
            time.sleep(0.01)  # CPU 사용률 낮추기

    def get_login_info(self):
        """로그인 정보 조회"""
        self.print_header("👤 로그인 정보")

        try:
            account_cnt = self.ocx.GetLoginInfo("ACCOUNT_CNT")
            accounts = self.ocx.GetLoginInfo("ACCNO")
            user_id = self.ocx.GetLoginInfo("USER_ID")
            user_name = self.ocx.GetLoginInfo("USER_NAME")

            print(f"사용자 ID: {user_id}")
            print(f"사용자 이름: {user_name}")
            print(f"보유 계좌수: {account_cnt}")
            print(f"계좌번호 목록: {accounts}")

            # 계좌 리스트 파싱
            account_list = accounts.strip().split(';')
            account_list = [acc for acc in account_list if acc]

            return {
                'user_id': user_id,
                'user_name': user_name,
                'accounts': account_list
            }

        except Exception as e:
            print(f"❌ 로그인 정보 조회 실패: {e}")
            return None

    def request_minute_candle(self, stock_code, tick_range="1", count=100):
        """
        분봉 데이터 요청

        Args:
            stock_code: 종목코드 (예: "005930" = 삼성전자)
            tick_range: 분봉 단위 (1, 3, 5, 10, 15, 30, 45, 60)
            count: 요청할 봉 개수
        """
        self.print_header(f"📊 분봉 데이터 요청: {stock_code} ({tick_range}분봉)")

        try:
            self.tr_event.clear()
            self.tr_data = {}

            # TR 입력값 설정
            self.ocx.SetInputValue("종목코드", stock_code)
            self.ocx.SetInputValue("틱범위", tick_range)
            self.ocx.SetInputValue("수정주가구분", "1")  # 수정주가 사용

            print(f"입력값 설정 완료:")
            print(f"  종목코드: {stock_code}")
            print(f"  틱범위: {tick_range}분")
            print(f"  수정주가구분: 1 (수정주가)")

            # TR 요청 (opt10080 = 주식분봉조회)
            ret = self.ocx.CommRqData(
                "분봉조회",      # 사용자 구분명
                "opt10080",      # TR 이름
                0,               # 0: 조회, 2: 연속조회
                "0101"           # 화면번호
            )

            if ret != 0:
                print(f"❌ TR 요청 실패: {ret}")
                return None

            print("✅ TR 요청 성공, 응답 대기 중...")

            # 응답 대기 (최대 30초)
            if self.tr_event.wait(30):
                print(f"✅ 데이터 수신 완료: {len(self.tr_data.get('data', []))}개 봉")
                return self.tr_data
            else:
                print("❌ 타임아웃: 30초 내에 데이터를 받지 못했습니다")
                return None

        except Exception as e:
            print(f"❌ 분봉 데이터 요청 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

    def print_candle_data(self, data, max_rows=10):
        """분봉 데이터 출력"""
        if not data or 'data' not in data:
            print("❌ 출력할 데이터가 없습니다")
            return

        candles = data['data']
        if not candles:
            print("❌ 데이터가 비어있습니다")
            return

        self.print_header(f"📈 분봉 데이터 ({len(candles)}개)")

        # 헤더 출력
        print(f"{'날짜':12} {'시각':8} {'현재가':>10} {'시가':>10} {'고가':>10} "
              f"{'저가':>10} {'거래량':>12}")
        print("-" * 80)

        # 최근 데이터부터 출력
        for i, candle in enumerate(candles[:max_rows]):
            print(f"{candle['날짜']:12} {candle['시각']:8} "
                  f"{candle['현재가']:>10} {candle['시가']:>10} {candle['고가']:>10} "
                  f"{candle['저가']:>10} {candle['거래량']:>12}")

        if len(candles) > max_rows:
            print(f"... ({len(candles) - max_rows}개 더 있음)")

    def disconnect(self):
        """연결 종료"""
        try:
            if self.ocx:
                self.ocx.CommTerminate()
                print("✅ 연결 종료")
        except:
            pass

        try:
            pythoncom.CoUninitialize()
        except:
            pass


class KiwoomEventHandler:
    """Kiwoom Open API 이벤트 핸들러"""

    def OnEventConnect(self, err_code):
        """로그인 이벤트"""
        print(f"\n[이벤트] OnEventConnect 발생: err_code={err_code}")

        if err_code == 0:
            print("   ✅ 로그인 성공!")
            self.parent.connected = True
        else:
            print(f"   ❌ 로그인 실패: {err_code}")
            self.parent.connected = False

        self.parent.login_event.set()

    def OnReceiveTrData(self, screen_no, rqname, trcode, record_name,
                        prev_next, data_len, err_code, msg, splm_msg):
        """TR 데이터 수신 이벤트"""
        print(f"\n[이벤트] OnReceiveTrData 발생:")
        print(f"   rqname={rqname}, trcode={trcode}, err_code={err_code}")

        if err_code != 0:
            print(f"   ❌ TR 오류: {msg}")
            self.parent.tr_event.set()
            return

        try:
            if rqname == "분봉조회":
                # 데이터 개수 확인
                cnt = self.parent.ocx.GetRepeatCnt(trcode, rqname)
                print(f"   수신된 데이터 개수: {cnt}")

                candles = []

                for i in range(cnt):
                    candle = {
                        '날짜': self.parent.ocx.GetCommData(trcode, rqname, i, "체결시간").strip()[:8],
                        '시각': self.parent.ocx.GetCommData(trcode, rqname, i, "체결시간").strip()[8:],
                        '현재가': self.parent.ocx.GetCommData(trcode, rqname, i, "현재가").strip(),
                        '시가': self.parent.ocx.GetCommData(trcode, rqname, i, "시가").strip(),
                        '고가': self.parent.ocx.GetCommData(trcode, rqname, i, "고가").strip(),
                        '저가': self.parent.ocx.GetCommData(trcode, rqname, i, "저가").strip(),
                        '거래량': self.parent.ocx.GetCommData(trcode, rqname, i, "거래량").strip(),
                    }
                    candles.append(candle)

                self.parent.tr_data = {
                    'rqname': rqname,
                    'trcode': trcode,
                    'data': candles,
                    'prev_next': prev_next
                }

                print(f"   ✅ 분봉 데이터 파싱 완료: {len(candles)}개")

        except Exception as e:
            print(f"   ❌ 데이터 파싱 오류: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.parent.tr_event.set()

    def OnReceiveMsg(self, screen_no, rqname, trcode, msg):
        """메시지 수신 이벤트"""
        print(f"[메시지] {rqname}: {msg}")


def main():
    """메인 테스트 함수"""
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║           🚀 64비트 Open API 로그인 및 분봉 조회 테스트                   ║
║                                                                          ║
║  목표:                                                                   ║
║  1. 64비트 환경에서 Open API 로그인 성공                                  ║
║  2. 과거 분봉 데이터 조회                                                 ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
""")

    api = KiwoomAPI64()

    try:
        # 1. 초기화
        if not api.initialize():
            print("\n❌ 초기화 실패")
            return

        # 2. 로그인
        if not api.connect(timeout=60):
            print("\n❌ 로그인 실패")
            print("\n💡 문제 해결 방법:")
            print("   1. 작업 관리자에서 'KH'로 시작하는 프로세스 모두 종료")
            print("   2. 영웅문(HTS)이 실행 중이면 종료")
            print("   3. Python 인터프리터 재시작")
            print("   4. 관리자 권한으로 실행")
            return

        # 3. 로그인 정보 확인
        login_info = api.get_login_info()
        if not login_info:
            print("\n❌ 로그인 정보 조회 실패")
            return

        # 4. 분봉 데이터 요청
        print("\n" + "="*80)
        print("  📊 분봉 데이터 조회 시작")
        print("="*80)

        # 삼성전자 1분봉 조회
        stock_code = "005930"  # 삼성전자
        tick_range = "1"       # 1분봉

        data = api.request_minute_candle(stock_code, tick_range)

        if data:
            api.print_candle_data(data, max_rows=20)

            print("\n✅ 테스트 성공!")
            print(f"   - {len(data['data'])}개의 {tick_range}분봉 데이터를 성공적으로 조회했습니다")
        else:
            print("\n❌ 분봉 데이터 조회 실패")

        # 5. 다른 분봉도 테스트 (선택사항)
        print("\n" + "="*80)
        print("  다른 분봉 단위도 테스트하시겠습니까?")
        print("  (y/n): ", end="")

        # 자동으로 'n' 선택 (스크립트 실행용)
        choice = 'n'
        print(choice)

        if choice.lower() == 'y':
            for tick in ["3", "5", "10"]:
                print(f"\n{tick}분봉 조회 중...")
                time.sleep(0.5)  # TR 요청 간격 (0.5초)
                data = api.request_minute_candle(stock_code, tick)
                if data:
                    api.print_candle_data(data, max_rows=10)

    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자가 중단했습니다")

    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 연결 종료
        api.disconnect()

    print("\n" + "="*80)
    print("  테스트 종료")
    print("="*80)


if __name__ == '__main__':
    main()
    print("\n창을 닫으려면 Enter를 누르세요...")
    input()
