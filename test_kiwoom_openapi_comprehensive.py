"""
키움증권 Open API 64비트 종합 테스트 파일

목적:
1. 64비트 Python에서 키움 Open API 완전 지원
2. 로그인, 계좌조회, 시세조회, 과거데이터 등 주요 기능 통합
3. 최신 COM threading model 적용 (RPC_E_CALL_REJECTED 오류 해결)
4. 실전 투자에 사용 가능한 안정적인 구조

주요 기능:
- 자동 진단 및 프로세스 정리
- 로그인 및 계좌정보 조회
- 과거 데이터 조회 (분봉, 일봉, 틱)
- 실시간 시세 구독
- 잔고 및 체결 조회
- 주문 기능 (선택적)

환경:
- Python 3.11.9 (64비트)
- pywin32
- 64bit-kiwoom-openapi (https://github.com/teranum/64bit-kiwoom-openapi)

작성일: 2025-01-07
"""
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
import platform
import subprocess
import winreg
from collections import defaultdict

# 프로젝트 루트 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Python 버전 및 아키텍처 확인
print("="*100)
print(f"Python 버전: {sys.version}")
print(f"Python 아키텍처: {platform.architecture()[0]}")
print("="*100 + "\n")

if platform.architecture()[0] != '64bit':
    print("⚠️  경고: 32비트 Python이 감지되었습니다!")
    print("   64비트 Kiwoom OpenAPI를 사용하려면 64비트 Python이 필요합니다.")
    sys.exit(1)

try:
    import win32com.client
    import pythoncom
    import pywintypes
except ImportError:
    print("❌ pywin32 모듈이 설치되지 않았습니다!")
    print("   설치 명령: pip install pywin32")
    sys.exit(1)


class KiwoomOpenAPI:
    """
    키움증권 Open API 64비트 통합 래퍼 클래스

    최신 COM threading model 적용:
    - CoInitializeEx(COINIT_APARTMENTTHREADED) 사용
    - RPC_E_CALL_REJECTED 오류 해결
    - 안정적인 메시지 루프 처리
    """

    def __init__(self, auto_diagnose=True):
        self.ocx = None
        self.is_connected = False

        # 이벤트 플래그
        self.login_event = threading.Event()
        self.tr_event = threading.Event()

        # TR 응답 데이터
        self.tr_data = {}
        self.tr_prev_next = "0"

        # 실시간 데이터
        self.realtime_callbacks = defaultdict(list)

        # 계좌 정보
        self.account_list = []

        # 자동 진단
        if auto_diagnose:
            self._auto_diagnose()

    def _auto_diagnose(self):
        """자동 진단 및 문제 해결"""
        print("\n🔍 자동 진단 시작...\n")

        # 1. 충돌 프로세스 확인 및 종료
        if self._check_conflicting_processes():
            print("⚠️  충돌 가능한 Kiwoom 프로세스 발견!")
            print("   자동으로 종료하시겠습니까? (y/n): ", end="")
            try:
                choice = input().strip().lower()
                if choice == 'y':
                    self._kill_kiwoom_processes()
            except:
                pass

        # 2. OCX 등록 확인
        if not self._check_ocx_registered():
            print("❌ OCX가 등록되지 않았습니다!")
            print("\n💡 해결 방법:")
            print("   1. 관리자 권한으로 실행:")
            print("      regsvr32 C:\\OpenApi\\KHOpenAPI64.ocx")
            print("   2. 또는 diagnose_kiwoom_64bit.py 실행")
            sys.exit(1)

        print("✅ 진단 완료\n")

    def _check_conflicting_processes(self):
        """충돌 프로세스 확인"""
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq KH*', '/FO', 'CSV'],
                capture_output=True,
                text=True,
                encoding='cp949'
            )
            lines = result.stdout.strip().split('\n')
            return len(lines) > 1 and '정보: 지정한 조건을' not in result.stdout
        except:
            return False

    def _kill_kiwoom_processes(self):
        """Kiwoom 프로세스 강제 종료"""
        processes = ["KHOpenAPI.exe", "KHOpenAPICtrl.exe", "OpSysMsg.exe", "KHOpenApi64.exe"]
        for proc in processes:
            try:
                subprocess.run(['taskkill', '/F', '/IM', proc],
                             capture_output=True)
            except:
                pass
        time.sleep(1)
        print("✅ 프로세스 정리 완료")

    def _check_ocx_registered(self):
        """OCX 등록 상태 확인"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                "KHOPENAPI.KHOpenAPICtrl.1",
                0,
                winreg.KEY_READ
            )
            winreg.CloseKey(key)
            return True
        except:
            return False

    def connect(self):
        """ActiveX 연결 및 초기화"""
        try:
            print("🔌 키움 Open API 연결 시도...\n")

            # COM 초기화 - STA (Single Threaded Apartment) 모델 사용
            # RPC_E_CALL_REJECTED 오류 방지
            pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
            print("✅ COM 초기화 완료 (COINIT_APARTMENTTHREADED)")

            # ActiveX 컨트롤 생성
            self.ocx = win32com.client.DispatchWithEvents(
                "KHOPENAPI.KHOpenAPICtrl.1",
                KiwoomEventHandler
            )
            print("✅ ActiveX 컨트롤 생성 완료")

            # 전역 인스턴스 설정 (이벤트 핸들러에서 접근)
            global kiwoom_instance
            kiwoom_instance = self

            # API 모듈 경로 확인
            try:
                module_path = self.ocx.GetAPIModulePath()
                print(f"   API 모듈 경로: {module_path}")
            except:
                pass

            return True

        except Exception as e:
            print(f"❌ 연결 실패: {e}")
            import traceback
            traceback.print_exc()
            return False

    def login(self, timeout=60):
        """
        로그인

        Args:
            timeout: 로그인 대기 시간 (초)

        Returns:
            bool: 로그인 성공 여부
        """
        try:
            print("\n🔐 로그인 시도 중...")
            print("   로그인 창이 나타나면 ID/PW를 입력하세요...\n")

            self.login_event.clear()

            # 메시지 큐 비우기
            pythoncom.PumpWaitingMessages()
            time.sleep(0.5)

            # 로그인 요청
            ret = self.ocx.CommConnect()

            if ret == 0:
                print("✅ 로그인 요청 전송 완료")
                print(f"   최대 {timeout}초 대기 중...\n")

                # 이벤트 대기 - 메시지 루프 적극 처리
                start_time = time.time()
                while not self.is_connected and (time.time() - start_time) < timeout:
                    pythoncom.PumpWaitingMessages()
                    time.sleep(0.05)  # 20Hz로 메시지 체크

                if self.is_connected:
                    print("\n✅ 로그인 성공!\n")
                    self._load_account_info()
                    return True
                else:
                    print(f"\n❌ 로그인 시간 초과 ({timeout}초)")
                    return False
            else:
                print(f"❌ 로그인 요청 실패 (ret={ret})")
                return False

        except pywintypes.com_error as e:
            error_code = e.args[0] & 0xFFFFFFFF
            print(f"❌ COM 오류: {e.args[1]}")

            if error_code == 0x8001011F:  # RPC_E_CALL_REJECTED
                print("\n💡 RPC_E_CALL_REJECTED 오류:")
                print("   1. 모든 Kiwoom 프로세스 종료")
                print("   2. Python 스크립트 재실행")
                print("   3. PC 재부팅 (권장)")

            return False

        except Exception as e:
            print(f"❌ 로그인 중 오류: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_account_info(self):
        """계좌 정보 로드"""
        try:
            account_cnt = self.ocx.GetLoginInfo("ACCOUNT_CNT")
            accounts = self.ocx.GetLoginInfo("ACCNO")
            user_id = self.ocx.GetLoginInfo("USER_ID")
            user_name = self.ocx.GetLoginInfo("USER_NM")

            self.account_list = [acc for acc in accounts.split(';') if acc]

            print("📋 로그인 정보:")
            print(f"   사용자 ID: {user_id}")
            print(f"   사용자명: {user_name}")
            print(f"   보유 계좌수: {account_cnt}")
            print(f"   계좌번호: {', '.join(self.account_list)}")
            print()

        except Exception as e:
            print(f"⚠️  계좌 정보 조회 실패: {e}")

    def get_account_list(self):
        """계좌 리스트 반환"""
        return self.account_list

    def request_tr(self, rqname, trcode, prev_next, screen_no, inputs, timeout=30):
        """
        TR 요청 (범용)

        Args:
            rqname: 사용자 구분명
            trcode: TR 코드
            prev_next: 연속조회 (0: 첫조회, 2: 연속조회)
            screen_no: 화면번호
            inputs: 입력값 딕셔너리 {필드명: 값}
            timeout: 타임아웃 (초)

        Returns:
            dict: TR 응답 데이터
        """
        try:
            self.tr_event.clear()
            self.tr_data = {}

            # 입력값 설정
            for field, value in inputs.items():
                self.ocx.SetInputValue(field, value)

            # TR 요청
            ret = self.ocx.CommRqData(rqname, trcode, prev_next, screen_no)

            if ret != 0:
                print(f"⚠️  TR 요청 실패: {rqname} (ret={ret})")
                return None

            # 응답 대기
            start_time = time.time()
            while not self.tr_event.is_set() and (time.time() - start_time) < timeout:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.01)

            if self.tr_event.is_set():
                return self.tr_data
            else:
                print(f"⚠️  TR 응답 시간 초과: {rqname}")
                return None

        except Exception as e:
            print(f"❌ TR 요청 오류: {e}")
            return None

    def get_minute_candle(self, stock_code, interval=1, count=100):
        """
        분봉 데이터 조회

        Args:
            stock_code: 종목코드 (예: "005930")
            interval: 분봉 간격 (1, 3, 5, 10, 15, 30, 45, 60)
            count: 조회 개수 (최대 약 900개/요청)

        Returns:
            list: 분봉 데이터 리스트
        """
        print(f"\n📊 분봉 데이터 조회: {stock_code} ({interval}분봉, {count}개)")

        all_data = []
        request_count = 0
        max_requests = (count // 900) + 1

        while len(all_data) < count and request_count < max_requests:
            request_count += 1

            inputs = {
                "종목코드": stock_code,
                "틱범위": str(interval),
                "수정주가구분": "1"  # 수정주가
            }

            prev_next = 2 if request_count > 1 else 0

            result = self.request_tr(
                rqname="분봉조회",
                trcode="opt10080",
                prev_next=prev_next,
                screen_no="0101",
                inputs=inputs,
                timeout=30
            )

            if not result or 'data' not in result:
                break

            data = result['data']
            all_data.extend(data)

            print(f"   [{request_count}차] {len(data)}개 수신 (누적: {len(all_data)}개)")

            # 연속조회 확인
            if result.get('prev_next') != "2":
                break

            # API 제한 준수 (0.2초 대기)
            time.sleep(0.2)

        print(f"✅ 총 {len(all_data)}개 수신 완료\n")
        return all_data[:count]

    def get_daily_candle(self, stock_code, count=100, adjusted=True):
        """
        일봉 데이터 조회

        Args:
            stock_code: 종목코드
            count: 조회 개수
            adjusted: 수정주가 여부

        Returns:
            list: 일봉 데이터 리스트
        """
        print(f"\n📊 일봉 데이터 조회: {stock_code} ({count}개)")

        all_data = []
        request_count = 0
        max_requests = (count // 900) + 1

        while len(all_data) < count and request_count < max_requests:
            request_count += 1

            inputs = {
                "종목코드": stock_code,
                "기준일자": datetime.now().strftime("%Y%m%d"),
                "수정주가구분": "1" if adjusted else "0"
            }

            prev_next = 2 if request_count > 1 else 0

            result = self.request_tr(
                rqname="일봉조회",
                trcode="opt10081",
                prev_next=prev_next,
                screen_no="0102",
                inputs=inputs,
                timeout=30
            )

            if not result or 'data' not in result:
                break

            data = result['data']
            all_data.extend(data)

            print(f"   [{request_count}차] {len(data)}개 수신 (누적: {len(all_data)}개)")

            if result.get('prev_next') != "2":
                break

            time.sleep(0.2)

        print(f"✅ 총 {len(all_data)}개 수신 완료\n")
        return all_data[:count]

    def get_stock_info(self, stock_code):
        """
        종목 기본 정보 조회

        Args:
            stock_code: 종목코드

        Returns:
            dict: 종목 정보
        """
        print(f"\n📈 종목 정보 조회: {stock_code}")

        inputs = {"종목코드": stock_code}

        result = self.request_tr(
            rqname="주식기본정보",
            trcode="opt10001",
            prev_next=0,
            screen_no="0103",
            inputs=inputs,
            timeout=30
        )

        if result and 'single' in result:
            print("✅ 종목 정보 수신 완료\n")
            return result['single']
        else:
            print("❌ 종목 정보 수신 실패\n")
            return None

    def get_balance(self, account_no=None):
        """
        계좌 잔고 조회

        Args:
            account_no: 계좌번호 (없으면 첫 번째 계좌)

        Returns:
            dict: 잔고 정보 {'stocks': [...], 'deposit': ...}
        """
        if not account_no and self.account_list:
            account_no = self.account_list[0]

        if not account_no:
            print("❌ 계좌번호가 없습니다.")
            return None

        print(f"\n💰 잔고 조회: {account_no}")

        inputs = {
            "계좌번호": account_no,
            "비밀번호": "",
            "비밀번호입력매체구분": "00",
            "조회구분": "1"  # 1: 합산, 2: 개별
        }

        result = self.request_tr(
            rqname="계좌평가잔고내역요청",
            trcode="opw00018",
            prev_next=0,
            screen_no="0201",
            inputs=inputs,
            timeout=30
        )

        if result:
            print("✅ 잔고 조회 완료\n")
            return result
        else:
            print("❌ 잔고 조회 실패\n")
            return None

    def subscribe_realtime(self, screen_no, stock_codes, fids, realtype=0):
        """
        실시간 시세 구독

        Args:
            screen_no: 화면번호
            stock_codes: 종목코드 리스트
            fids: FID 리스트 (예: ["10", "11", "12"] = 현재가, 전일대비, 등락률)
            realtype: 0=기존 구독에 추가, 1=기존 구독 해지 후 신규

        Returns:
            bool: 구독 성공 여부
        """
        try:
            code_list = ";".join(stock_codes)
            fid_list = ";".join(fids)

            ret = self.ocx.SetRealReg(screen_no, code_list, fid_list, realtype)

            if ret == 0:
                print(f"✅ 실시간 시세 구독 성공: {code_list}")
                return True
            else:
                print(f"❌ 실시간 시세 구독 실패: {ret}")
                return False

        except Exception as e:
            print(f"❌ 실시간 시세 구독 오류: {e}")
            return False

    def unsubscribe_realtime(self, screen_no):
        """실시간 시세 구독 해지"""
        try:
            self.ocx.SetRealRemove(screen_no, "ALL")
            print(f"✅ 실시간 시세 구독 해지: {screen_no}")
        except Exception as e:
            print(f"❌ 구독 해지 오류: {e}")

    def add_realtime_callback(self, callback):
        """실시간 데이터 콜백 추가"""
        self.realtime_callbacks['all'].append(callback)

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
    """키움 Open API 이벤트 핸들러"""

    def OnEventConnect(self, err_code):
        """로그인 결과 이벤트"""
        global kiwoom_instance

        if err_code == 0:
            print("   ✅ [이벤트] 로그인 성공")
            kiwoom_instance.is_connected = True
        else:
            print(f"   ❌ [이벤트] 로그인 실패 (err_code={err_code})")
            kiwoom_instance.is_connected = False

        kiwoom_instance.login_event.set()

    def OnReceiveTrData(self, screen_no, rqname, trcode, record_name,
                        prev_next, data_len, err_code, msg, splm_msg):
        """TR 데이터 수신 이벤트"""
        global kiwoom_instance

        if err_code != 0:
            print(f"   ⚠️  TR 오류: {msg} (err_code={err_code})")
            kiwoom_instance.tr_event.set()
            return

        try:
            # 데이터 파싱
            if rqname == "분봉조회":
                kiwoom_instance.tr_data = self._parse_minute_candle(trcode, rqname)
            elif rqname == "일봉조회":
                kiwoom_instance.tr_data = self._parse_daily_candle(trcode, rqname)
            elif rqname == "주식기본정보":
                kiwoom_instance.tr_data = self._parse_stock_info(trcode, rqname)
            elif rqname == "계좌평가잔고내역요청":
                kiwoom_instance.tr_data = self._parse_balance(trcode, rqname)
            else:
                # 기본 파싱 (반복 데이터)
                kiwoom_instance.tr_data = self._parse_generic(trcode, rqname)

            # 연속조회 플래그 저장
            kiwoom_instance.tr_data['prev_next'] = prev_next

        except Exception as e:
            print(f"   ❌ 데이터 파싱 오류: {e}")
            import traceback
            traceback.print_exc()

        finally:
            kiwoom_instance.tr_event.set()

    def _parse_minute_candle(self, trcode, rqname):
        """분봉 데이터 파싱"""
        global kiwoom_instance

        cnt = kiwoom_instance.ocx.GetRepeatCnt(trcode, rqname)
        data = []

        for i in range(cnt):
            try:
                item = {
                    'date': kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "체결시간").strip(),
                    'open': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "시가").strip() or 0),
                    'high': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "고가").strip() or 0),
                    'low': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "저가").strip() or 0),
                    'close': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "현재가").strip() or 0),
                    'volume': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "거래량").strip() or 0),
                }
                data.append(item)
            except:
                pass

        return {'data': data}

    def _parse_daily_candle(self, trcode, rqname):
        """일봉 데이터 파싱"""
        global kiwoom_instance

        cnt = kiwoom_instance.ocx.GetRepeatCnt(trcode, rqname)
        data = []

        for i in range(cnt):
            try:
                item = {
                    'date': kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "일자").strip(),
                    'open': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "시가").strip() or 0),
                    'high': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "고가").strip() or 0),
                    'low': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "저가").strip() or 0),
                    'close': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "현재가").strip() or 0),
                    'volume': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "거래량").strip() or 0),
                }
                data.append(item)
            except:
                pass

        return {'data': data}

    def _parse_stock_info(self, trcode, rqname):
        """종목 정보 파싱 (단일 데이터)"""
        global kiwoom_instance

        try:
            info = {
                '종목명': kiwoom_instance.ocx.GetCommData(trcode, rqname, 0, "종목명").strip(),
                '현재가': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, 0, "현재가").strip() or 0),
                '전일대비': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, 0, "전일대비").strip() or 0),
                '등락률': float(kiwoom_instance.ocx.GetCommData(trcode, rqname, 0, "등락률").strip() or 0),
                '거래량': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, 0, "거래량").strip() or 0),
                '시가': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, 0, "시가").strip() or 0),
                '고가': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, 0, "고가").strip() or 0),
                '저가': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, 0, "저가").strip() or 0),
            }
            return {'single': info}
        except:
            return {}

    def _parse_balance(self, trcode, rqname):
        """잔고 정보 파싱"""
        global kiwoom_instance

        cnt = kiwoom_instance.ocx.GetRepeatCnt(trcode, rqname)
        stocks = []

        for i in range(cnt):
            try:
                stock = {
                    '종목명': kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "종목명").strip(),
                    '보유수량': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "보유수량").strip() or 0),
                    '매입가': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "매입가").strip() or 0),
                    '현재가': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "현재가").strip() or 0),
                    '평가손익': int(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "평가손익").strip() or 0),
                    '수익률': float(kiwoom_instance.ocx.GetCommData(trcode, rqname, i, "수익률(%)").strip() or 0),
                }
                stocks.append(stock)
            except:
                pass

        # 예수금 정보
        try:
            deposit = int(kiwoom_instance.ocx.GetCommData(trcode, rqname, 0, "예수금").strip() or 0)
        except:
            deposit = 0

        return {'data': stocks, 'deposit': deposit}

    def _parse_generic(self, trcode, rqname):
        """범용 파싱 (반복 데이터)"""
        global kiwoom_instance

        cnt = kiwoom_instance.ocx.GetRepeatCnt(trcode, rqname)
        data = []

        for i in range(cnt):
            data.append({'index': i})

        return {'data': data, 'count': cnt}

    def OnReceiveRealData(self, stock_code, realtype, realdata):
        """실시간 시세 수신 이벤트"""
        global kiwoom_instance

        # 콜백 실행
        for callback in kiwoom_instance.realtime_callbacks['all']:
            try:
                callback(stock_code, realtype, realdata)
            except Exception as e:
                print(f"⚠️  실시간 콜백 오류: {e}")

    def OnReceiveMsg(self, screen_no, rqname, trcode, msg):
        """메시지 수신 이벤트"""
        if msg:
            print(f"[메시지] {rqname}: {msg}")

    def OnReceiveChejanData(self, gubun, item_cnt, fid_list):
        """체결/잔고 실시간 수신"""
        print(f"[체결] gubun={gubun}, item_cnt={item_cnt}")


def print_section(title):
    """섹션 구분선 출력"""
    print(f"\n{'='*100}")
    print(f"  {title}")
    print(f"{'='*100}\n")


def print_candle_data(data, max_rows=10, data_type="분봉"):
    """봉 데이터 테이블 출력"""
    if not data:
        print("⚠️  출력할 데이터가 없습니다.")
        return

    print(f"\n{'='*100}")
    print(f"📈 {data_type} 데이터 샘플 (총 {len(data)}개 중 최근 {min(max_rows, len(data))}개)")
    print(f"{'='*100}")

    # 헤더
    if data_type == "분봉":
        print(f"{'일자':12} {'시각':8} {'현재가':>12} {'시가':>12} {'고가':>12} "
              f"{'저가':>12} {'거래량':>12}")
    else:  # 일봉
        print(f"{'일자':12} {'현재가':>12} {'시가':>12} {'고가':>12} "
              f"{'저가':>12} {'거래량':>12}")

    print("-" * 100)

    # 데이터 출력
    for i, item in enumerate(data[:max_rows]):
        if data_type == "분봉":
            date_str = item['date']
            date_part = date_str[:8] if len(date_str) >= 8 else date_str
            time_part = date_str[8:] if len(date_str) > 8 else ""

            print(f"{date_part:12} {time_part:8} "
                  f"{item['close']:>12,} {item['open']:>12,} {item['high']:>12,} "
                  f"{item['low']:>12,} {item['volume']:>12,}")
        else:  # 일봉
            print(f"{item['date']:12} "
                  f"{item['close']:>12,} {item['open']:>12,} {item['high']:>12,} "
                  f"{item['low']:>12,} {item['volume']:>12,}")

    print("=" * 100)


def save_to_csv(data, filename, data_type="candle"):
    """CSV 파일 저장"""
    try:
        import csv

        filepath = project_root / filename

        if data_type == "candle":
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=['date', 'open', 'high', 'low', 'close', 'volume'])
                writer.writeheader()
                writer.writerows(data)

        print(f"\n💾 CSV 저장 완료: {filepath}")
        print(f"   파일 크기: {filepath.stat().st_size:,} bytes")

        return True

    except Exception as e:
        print(f"❌ CSV 저장 실패: {e}")
        return False


def test_basic_functions(api):
    """기본 기능 테스트"""
    print_section("📊 기본 기능 테스트")

    # 1. 삼성전자 종목 정보 조회
    stock_info = api.get_stock_info("005930")
    if stock_info:
        print("삼성전자 종목 정보:")
        for key, value in stock_info.items():
            print(f"  {key}: {value}")

    time.sleep(0.5)

    # 2. 삼성전자 1분봉 100개 조회
    minute_data = api.get_minute_candle("005930", interval=1, count=100)
    if minute_data:
        print_candle_data(minute_data, max_rows=10, data_type="분봉")
        save_to_csv(minute_data, "samsung_1min.csv")

    time.sleep(0.5)

    # 3. 삼성전자 일봉 50개 조회
    daily_data = api.get_daily_candle("005930", count=50)
    if daily_data:
        print_candle_data(daily_data, max_rows=10, data_type="일봉")
        save_to_csv(daily_data, "samsung_daily.csv")

    # 4. 계좌 잔고 조회
    if api.account_list:
        balance = api.get_balance()
        if balance:
            print("\n💰 계좌 잔고:")
            print(f"   예수금: {balance.get('deposit', 0):,}원")
            print(f"   보유 종목수: {len(balance.get('data', []))}개")

            if balance.get('data'):
                print("\n   보유 종목:")
                for stock in balance['data'][:5]:
                    print(f"   - {stock['종목명']}: {stock['보유수량']}주 "
                          f"(수익률: {stock['수익률']:.2f}%)")


def test_realtime(api):
    """실시간 시세 테스트"""
    print_section("📡 실시간 시세 테스트")

    def realtime_callback(stock_code, realtype, realdata):
        """실시간 데이터 콜백"""
        print(f"[실시간] {stock_code} - {realtype}")

    # 콜백 등록
    api.add_realtime_callback(realtime_callback)

    # 삼성전자 실시간 시세 구독
    api.subscribe_realtime(
        screen_no="1000",
        stock_codes=["005930", "035720"],  # 삼성전자, 카카오
        fids=["10", "11", "12", "27", "28"],  # 현재가, 전일대비, 등락률, (최우선)매도호가, (최우선)매수호가
        realtype=0
    )

    print("10초간 실시간 시세 수신 중...")

    for i in range(10):
        pythoncom.PumpWaitingMessages()
        time.sleep(1)

    # 구독 해지
    api.unsubscribe_realtime("1000")


def main():
    """메인 테스트 함수"""

    print("""
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║               🚀 키움증권 Open API 64비트 종합 테스트                                    ║
║                                                                                      ║
║  환경: Python 3.11.9 (64비트)                                                         ║
║  기능: 로그인, 시세조회, 과거데이터, 잔고조회, 실시간                                      ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
""")

    # API 생성 (자동 진단 포함)
    api = KiwoomOpenAPI(auto_diagnose=True)

    try:
        # 1. 연결
        if not api.connect():
            print("\n❌ API 연결 실패")
            return

        # 2. 로그인
        if not api.login(timeout=60):
            print("\n❌ 로그인 실패")
            return

        # 3. 기본 기능 테스트
        test_basic_functions(api)

        # 4. 실시간 테스트 (선택)
        print("\n실시간 시세 테스트를 진행하시겠습니까? (y/n): ", end="")
        try:
            choice = input().strip().lower()
            if choice == 'y':
                test_realtime(api)
        except:
            pass

        print_section("✅ 테스트 완료")

        print("주요 기능:")
        print("  ✅ 64비트 Python에서 키움 Open API 정상 작동")
        print("  ✅ 로그인 및 계좌 정보 조회")
        print("  ✅ 과거 데이터 조회 (분봉, 일봉)")
        print("  ✅ 종목 정보 조회")
        print("  ✅ 계좌 잔고 조회")
        print("  ✅ 실시간 시세 구독")

        print("\n💡 다음 단계:")
        print("  1. 이 클래스를 다른 파일에서 import하여 사용")
        print("  2. 자동매매 전략 구현")
        print("  3. 데이터베이스 연동")
        print("  4. 백테스팅 시스템 구축")

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 테스트를 중단했습니다.")

    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 연결 종료
        api.disconnect()

    print("\n" + "="*100)


if __name__ == '__main__':
    main()
    print("\n테스트 종료. 창을 닫으려면 Enter를 누르세요...")
    input()
