"""
실시간 데이터 스트림 (Realtime Data Stream)

OpenAPI에서 지속적으로 데이터를 받아 WebSocket으로 전송합니다.
- 호가 데이터
- 체결 데이터
- 외국인/기관 순매수
- 거래량 데이터
"""
import logging
import threading
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class RealtimeDataStream:
    """실시간 데이터 스트림 관리"""

    def __init__(self, market_api=None, data_fetcher=None):
        """
        Args:
            market_api: MarketAPI 인스턴스
            data_fetcher: DataFetcher 인스턴스
        """
        self.market_api = market_api
        self.data_fetcher = data_fetcher

        self.is_running = False
        self.stream_thread = None

        # 콜백 함수들
        self.callbacks: Dict[str, Callable] = {}

        # 모니터링할 종목 리스트
        self.watch_list = ['005930', '000660', '035720']  # 삼성전자, SK하이닉스, 카카오

        # 캐시 (중복 방지)
        self.last_data: Dict[str, Any] = {}

        logger.info("실시간 데이터 스트림 초기화 완료")

    def register_callback(self, event_name: str, callback: Callable):
        """
        콜백 등록

        Args:
            event_name: 이벤트 이름 ('price', 'volume', 'foreign_net', etc.)
            callback: 콜백 함수
        """
        self.callbacks[event_name] = callback
        logger.info(f"콜백 등록: {event_name}")

    def start(self):
        """실시간 데이터 스트림 시작"""
        if self.is_running:
            logger.warning("이미 실행 중입니다")
            return

        self.is_running = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()

        logger.info("✅ 실시간 데이터 스트림 시작")

    def stop(self):
        """실시간 데이터 스트림 중지"""
        self.is_running = False

        if self.stream_thread:
            self.stream_thread.join(timeout=5)

        logger.info("실시간 데이터 스트림 중지")

    def _stream_loop(self):
        """메인 스트림 루프"""
        logger.info("스트림 루프 시작")

        while self.is_running:
            try:
                # 각 종목별 데이터 수집
                for stock_code in self.watch_list:
                    self._fetch_and_emit_stock_data(stock_code)

                # 2초 대기 (API 호출 제한 고려)
                time.sleep(2)

            except Exception as e:
                logger.error(f"스트림 루프 오류: {e}", exc_info=True)
                time.sleep(5)  # 오류 시 5초 대기

        logger.info("스트림 루프 종료")

    def _fetch_and_emit_stock_data(self, stock_code: str):
        """종목 데이터 수집 및 전송"""
        try:
            if not self.market_api:
                return

            # 현재가 조회
            current_price = self.market_api.get_current_price(stock_code)

            if not current_price:
                return

            # 데이터 파싱
            data = {
                'stock_code': stock_code,
                'timestamp': datetime.now().isoformat(),
                'price': int(current_price.get('stck_prpr', 0)),
                'change_rate': float(current_price.get('prdy_ctrt', 0)),
                'volume': int(current_price.get('acml_vol', 0)),
                'trade_value': int(current_price.get('acml_tr_pbmn', 0)),
            }

            # 호가 데이터 추가
            bid_ask = self.market_api.get_bid_ask(stock_code)
            if bid_ask:
                data['bid_price'] = int(bid_ask.get('bidp1', 0))
                data['ask_price'] = int(bid_ask.get('askp1', 0))
                data['bid_volume'] = int(bid_ask.get('bidp_rsqn1', 0))
                data['ask_volume'] = int(bid_ask.get('askp_rsqn1', 0))

            # 외국인/기관 순매수 (일봉 데이터에서)
            try:
                if self.data_fetcher:
                    daily_data = self.data_fetcher.get_daily_price(
                        stock_code=stock_code,
                        count=1
                    )

                    if daily_data and len(daily_data) > 0:
                        latest = daily_data[0]
                        data['foreign_net'] = int(latest.get('frgn_ntby_qty', 0))
                        data['inst_net'] = int(latest.get('inst_ntby_qty', 0))
            except:
                pass

            # 변경사항이 있는 경우에만 전송 (중복 방지)
            cache_key = f"{stock_code}_price"
            if cache_key not in self.last_data or self.last_data[cache_key] != data['price']:
                self.last_data[cache_key] = data['price']

                # 콜백 호출
                if 'market_data' in self.callbacks:
                    self.callbacks['market_data'](data)

                logger.debug(f"[{stock_code}] 현재가: {data['price']:,}원 ({data['change_rate']:+.2f}%)")

        except Exception as e:
            logger.error(f"[{stock_code}] 데이터 수집 실패: {e}")

    def add_watch_stock(self, stock_code: str):
        """모니터링 종목 추가"""
        if stock_code not in self.watch_list:
            self.watch_list.append(stock_code)
            logger.info(f"모니터링 종목 추가: {stock_code}")

    def remove_watch_stock(self, stock_code: str):
        """모니터링 종목 제거"""
        if stock_code in self.watch_list:
            self.watch_list.remove(stock_code)
            logger.info(f"모니터링 종목 제거: {stock_code}")

    def get_status(self) -> Dict[str, Any]:
        """현재 상태 조회"""
        return {
            'is_running': self.is_running,
            'watch_list': self.watch_list,
            'callback_count': len(self.callbacks),
            'last_update': self.last_data.get('timestamp')
        }


# 싱글톤 인스턴스
_realtime_data_stream = None


def get_realtime_data_stream(market_api=None, data_fetcher=None) -> RealtimeDataStream:
    """실시간 데이터 스트림 싱글톤 가져오기"""
    global _realtime_data_stream

    if _realtime_data_stream is None and market_api:
        _realtime_data_stream = RealtimeDataStream(
            market_api=market_api,
            data_fetcher=data_fetcher
        )

    return _realtime_data_stream
