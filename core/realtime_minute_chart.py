"""
실시간 분봉 차트 생성기

WebSocket으로 받은 체결 데이터를 1분 단위로 집계하여 OHLCV 생성
"""

import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from utils.logger_new import get_logger

logger = get_logger()


@dataclass
class MinuteCandle:
    """1분봉 캔들"""
    timestamp: datetime
    open: int = 0
    high: int = 0
    low: int = 999999999
    close: int = 0
    volume: int = 0

    def update(self, price: int, volume: int):
        """체결 데이터로 캔들 업데이트"""
        if self.open == 0:
            self.open = price

        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'date': self.timestamp.strftime('%Y%m%d'),
            'time': self.timestamp.strftime('%H%M%S'),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'timestamp': int(self.timestamp.timestamp())
        }


class RealtimeMinuteChart:
    """실시간 분봉 차트 생성기"""

    def __init__(self, stock_code: str, websocket_manager):
        """
        초기화

        Args:
            stock_code: 종목코드
            websocket_manager: WebSocketManager 인스턴스
        """
        self.stock_code = stock_code
        self.ws_manager = websocket_manager

        # 분봉 데이터 저장 (최대 1일치: 390분 = 6.5시간)
        self.candles: Dict[datetime, MinuteCandle] = {}
        self.max_candles = 390  # 09:00 ~ 15:30

        # 현재 처리 중인 분봉 타임스탬프
        self.current_minute = None

        # 구독 상태
        self.is_subscribed = False

        logger.info(f"RealtimeMinuteChart 초기화: {stock_code}")

    async def start(self) -> bool:
        """
        실시간 분봉 수집 시작

        Returns:
            시작 성공 여부
        """
        if self.is_subscribed:
            logger.warning(f"{self.stock_code} 이미 구독 중")
            return True

        try:
            # WebSocket 연결 확인
            if not self.ws_manager.is_connected:
                logger.info("WebSocket 연결 시작...")
                success = await self.ws_manager.connect()
                if not success:
                    logger.error("WebSocket 연결 실패")
                    return False

            # 체결 데이터 구독
            logger.info(f"{self.stock_code} 체결 데이터 구독 중...")
            success = await self.ws_manager.subscribe(
                stock_codes=[self.stock_code],
                types=["0B"],  # 주식체결
                grp_no=f"minute_{self.stock_code}"
            )

            if success:
                # 콜백 등록
                self.ws_manager.register_callback('0B', self._on_tick)
                self.is_subscribed = True
                logger.info(f"✅ {self.stock_code} 실시간 분봉 수집 시작")
                return True
            else:
                logger.error(f"❌ {self.stock_code} 구독 실패")
                return False

        except Exception as e:
            logger.error(f"❌ 실시간 분봉 시작 실패: {e}")
            return False

    async def stop(self):
        """실시간 분봉 수집 중지"""
        if not self.is_subscribed:
            return

        try:
            await self.ws_manager.unsubscribe(f"minute_{self.stock_code}")
            self.is_subscribed = False
            logger.info(f"✅ {self.stock_code} 실시간 분봉 수집 중지")
        except Exception as e:
            logger.error(f"❌ 실시간 분봉 중지 실패: {e}")

    async def _on_tick(self, data: Dict[str, Any]):
        """
        체결 데이터 콜백

        Args:
            data: WebSocket 체결 데이터
                {
                    'type': '0B',
                    'item': '005930',
                    'values': {
                        '10': '71000',  # 현재가
                        '15': '100',    # 체결량
                        '16': '140523'  # 체결시각 (HHMMSS)
                    }
                }
        """
        try:
            # 종목 필터링
            item_code = data.get('item', '')
            if item_code != self.stock_code:
                return

            values = data.get('values', {})

            # 체결 데이터 파싱
            price = int(values.get('10', 0))  # 현재가
            volume = int(values.get('15', 0))  # 체결량
            time_str = values.get('16', '')  # 체결시각 HHMMSS

            if price == 0 or volume == 0:
                return

            # 현재 시각 (체결시각 사용 또는 현재 시각)
            now = datetime.now()
            if time_str and len(time_str) == 6:
                try:
                    hour = int(time_str[:2])
                    minute = int(time_str[2:4])
                    now = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                except (ValueError, TypeError):
                    pass  # Keep current time if parsing fails
            else:
                now = now.replace(second=0, microsecond=0)

            # 장외 시간 필터링 (08:00 ~ 20:00)
            # 한국 정규 장: 09:00-15:30
            # 확장 시간: 08:00-20:00 (프리마켓/애프터마켓 포함)
            if now.hour < 8 or now.hour >= 20:
                return

            # 분봉 업데이트
            if now not in self.candles:
                # 새로운 분봉 생성
                self.candles[now] = MinuteCandle(timestamp=now)

                # 오래된 데이터 제거 (최대 390개 유지)
                if len(self.candles) > self.max_candles:
                    oldest = min(self.candles.keys())
                    del self.candles[oldest]

                logger.debug(f"새 분봉 생성: {now.strftime('%H:%M')} (총 {len(self.candles)}개)")

            # 캔들 업데이트
            self.candles[now].update(price, volume)
            self.current_minute = now

        except Exception as e:
            logger.error(f"체결 데이터 처리 오류: {e}")

    def get_minute_data(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """
        최근 N분 데이터 조회

        Args:
            minutes: 조회할 분봉 개수

        Returns:
            분봉 데이터 리스트 (시간순 정렬)
        """
        if not self.candles:
            return []

        # 시간순 정렬
        sorted_candles = sorted(self.candles.items(), key=lambda x: x[0])

        # 최근 N개 추출
        recent_candles = sorted_candles[-minutes:] if len(sorted_candles) > minutes else sorted_candles

        # 딕셔너리로 변환
        return [candle.to_dict() for timestamp, candle in recent_candles]

    def get_current_candle(self) -> Optional[Dict[str, Any]]:
        """
        현재 진행 중인 분봉 조회

        Returns:
            현재 분봉 데이터 또는 None
        """
        if not self.current_minute or self.current_minute not in self.candles:
            return None

        return self.candles[self.current_minute].to_dict()

    def get_candle_count(self) -> int:
        """저장된 분봉 개수 반환"""
        return len(self.candles)


class RealtimeMinuteChartManager:
    """여러 종목의 실시간 분봉 관리"""

    def __init__(self, websocket_manager):
        """
        초기화

        Args:
            websocket_manager: WebSocketManager 인스턴스
        """
        self.ws_manager = websocket_manager
        self.charts: Dict[str, RealtimeMinuteChart] = {}

        logger.info("RealtimeMinuteChartManager 초기화")

    async def add_stock(self, stock_code: str) -> bool:
        """
        종목 추가 및 실시간 분봉 수집 시작

        Args:
            stock_code: 종목코드

        Returns:
            성공 여부
        """
        if stock_code in self.charts:
            logger.warning(f"{stock_code} 이미 추가됨")
            return True

        chart = RealtimeMinuteChart(stock_code, self.ws_manager)
        success = await chart.start()

        if success:
            self.charts[stock_code] = chart
            logger.info(f"✅ {stock_code} 실시간 분봉 추가")
            return True
        else:
            logger.error(f"❌ {stock_code} 실시간 분봉 추가 실패")
            return False

    async def remove_stock(self, stock_code: str):
        """
        종목 제거 및 실시간 분봉 수집 중지

        Args:
            stock_code: 종목코드
        """
        if stock_code not in self.charts:
            return

        chart = self.charts[stock_code]
        await chart.stop()
        del self.charts[stock_code]

        logger.info(f"✅ {stock_code} 실시간 분봉 제거")

    def get_minute_data(self, stock_code: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """
        특정 종목의 분봉 데이터 조회

        Args:
            stock_code: 종목코드
            minutes: 조회할 분봉 개수

        Returns:
            분봉 데이터 리스트
        """
        if stock_code not in self.charts:
            return []

        return self.charts[stock_code].get_minute_data(minutes)

    def get_current_candle(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        특정 종목의 현재 분봉 조회

        Args:
            stock_code: 종목코드

        Returns:
            현재 분봉 데이터 또는 None
        """
        if stock_code not in self.charts:
            return None

        return self.charts[stock_code].get_current_candle()

    def get_status(self) -> Dict[str, Any]:
        """
        전체 상태 조회

        Returns:
            상태 딕셔너리
        """
        return {
            'connected': self.ws_manager.is_connected if self.ws_manager else False,
            'stocks': {
                code: {
                    'subscribed': chart.is_subscribed,
                    'candle_count': chart.get_candle_count(),
                    'current_minute': chart.current_minute.strftime('%H:%M') if chart.current_minute else None
                }
                for code, chart in self.charts.items()
            }
        }
