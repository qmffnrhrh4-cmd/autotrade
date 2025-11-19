"""
database/models.py
SQLAlchemy 데이터베이스 모델

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
쿼리 최적화 가이드라인 (Query Optimization Guidelines)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Eager Loading (N+1 문제 방지)
   - joinedload: 관계된 객체를 JOIN으로 한 번에 로드
   - selectinload: 관계된 객체를 별도 SELECT로 로드 (많은 데이터에 유리)

   Example:
       from sqlalchemy.orm import joinedload

       # Bad: N+1 쿼리 발생
       positions = session.query(Position).filter_by(is_active=True).all()
       for pos in positions:
           print(pos.trades)  # 각 position마다 추가 쿼리 발생

       # Good: Eager loading
       positions = session.query(Position).options(
           joinedload(Position.trades)
       ).filter_by(is_active=True).all()

2. 필요한 컬럼만 조회 (SELECT 최적화)
   - defer(): 특정 컬럼 로딩 지연
   - load_only(): 특정 컬럼만 로드

   Example:
       from sqlalchemy.orm import load_only

       # Bad: 모든 컬럼 조회
       trades = session.query(Trade).all()

       # Good: 필요한 컬럼만 조회
       trades = session.query(Trade).options(
           load_only(Trade.stock_code, Trade.action, Trade.timestamp)
       ).all()

3. 대량 데이터 삽입 (Bulk Insert)
   - bulk_insert_mappings(): 대량 삽입 최적화

   Example:
       # Bad: 개별 삽입
       for data in data_list:
           session.add(Trade(**data))
       session.commit()

       # Good: Bulk insert
       session.bulk_insert_mappings(Trade, data_list)
       session.commit()

4. 인덱스 활용 쿼리
   - 복합 인덱스는 순서가 중요 (왼쪽부터 사용)

   Example:
       # idx_stock_action_timestamp (stock_code, action, timestamp)

       # Good: 인덱스 활용
       trades = session.query(Trade).filter(
           Trade.stock_code == '005930',
           Trade.action == 'buy',
           Trade.timestamp >= start_date
       ).all()

       # Partial: 인덱스 부분 활용 (stock_code만)
       trades = session.query(Trade).filter(
           Trade.stock_code == '005930',
           Trade.timestamp >= start_date  # action이 빠져서 인덱스 일부만 사용
       ).all()

5. 집계 쿼리 최적화
   - 데이터베이스 레벨에서 집계

   Example:
       from sqlalchemy import func

       # Bad: Python에서 집계
       trades = session.query(Trade).filter_by(action='buy').all()
       total_amount = sum(t.total_amount for t in trades)

       # Good: DB에서 집계
       total_amount = session.query(
           func.sum(Trade.total_amount)
       ).filter_by(action='buy').scalar()

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pathlib import Path

from utils.logger_new import get_logger

from config.manager import get_config


logger = get_logger()
Base = declarative_base()


class Trade(Base):
    """거래 기록"""

    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 종목 정보
    stock_code = Column(String(10), nullable=False, index=True)
    stock_name = Column(String(50), nullable=False)

    # 거래 정보
    action = Column(String(10), nullable=False, index=True)  # 'buy' or 'sell' - indexed for filtering
    quantity = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    total_amount = Column(Integer, nullable=False)

    # 수익/손실 (매도 시에만)
    profit_loss = Column(Integer, default=0)
    profit_loss_ratio = Column(Float, default=0.0)

    # 리스크 모드
    risk_mode = Column(String(20), nullable=True)

    # AI 분석 결과
    ai_score = Column(Float, nullable=True)
    ai_signal = Column(String(10), nullable=True)
    ai_confidence = Column(String(10), nullable=True)

    # 스코어링 결과
    scoring_total = Column(Float, nullable=True)
    scoring_percentage = Column(Float, nullable=True)

    # 거래 유형 구분 (v6.1.1: 실제/가상 거래 분리)
    is_virtual = Column(Boolean, default=False, nullable=False, index=True)

    # 기타
    notes = Column(Text, nullable=True)

    __table_args__ = (
        # 기존 인덱스: 종목별 시간순 조회
        Index('idx_stock_timestamp', 'stock_code', 'timestamp'),

        # 매수/매도 기록 조회 최적화
        Index('idx_action_timestamp', 'action', 'timestamp'),

        # 종목별 거래 이력 조회 최적화
        Index('idx_stock_action_timestamp', 'stock_code', 'action', 'timestamp'),
    )

    def __repr__(self):
        return f"<Trade(id={self.id}, {self.action} {self.stock_name} {self.quantity}주 @ {self.price}원)>"


class Position(Base):
    """포지션 (보유 종목)"""

    __tablename__ = 'positions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 종목 정보
    stock_code = Column(String(10), nullable=False, unique=True, index=True)
    stock_name = Column(String(50), nullable=False)

    # 포지션 정보
    quantity = Column(Integer, nullable=False)
    entry_price = Column(Integer, nullable=False)
    current_price = Column(Integer, nullable=False)

    # 목표가
    take_profit_price = Column(Integer, nullable=True)
    stop_loss_price = Column(Integer, nullable=True)

    # 수익/손실
    profit_loss = Column(Integer, default=0)
    profit_loss_ratio = Column(Float, default=0.0)

    # 진입 시 모드
    entry_risk_mode = Column(String(20), nullable=True)

    # 활성 여부
    is_active = Column(Boolean, default=True, index=True)

    __table_args__ = (
        # 활성 포지션 조회 최적화 (최근 업데이트된 활성 포지션)
        Index('idx_is_active_updated_at', 'is_active', 'updated_at'),
    )

    def __repr__(self):
        return f"<Position(id={self.id}, {self.stock_name} {self.quantity}주 @ {self.entry_price}원)>"

    def to_core_position(self):
        """
        ORM Position → Core Position 변환

        Returns:
            core.Position instance
        """
        from core import Position as CorePosition

        return CorePosition(
            stock_code=self.stock_code,
            stock_name=self.stock_name,
            quantity=self.quantity,
            purchase_price=float(self.entry_price),
            current_price=float(self.current_price),
            entry_time=self.created_at,
            stop_loss_price=float(self.stop_loss_price) if self.stop_loss_price else None,
            take_profit_price=float(self.take_profit_price) if self.take_profit_price else None,
            metadata={
                'db_id': self.id,
                'entry_risk_mode': self.entry_risk_mode,
                'is_active': self.is_active
            }
        )

    @classmethod
    def from_core_position(cls, pos, session=None):
        """
        Core Position → ORM Position 변환

        Args:
            pos: core.Position instance
            session: SQLAlchemy session (for saving)

        Returns:
            database.Position instance
        """
        db_pos = cls(
            stock_code=pos.stock_code,
            stock_name=pos.stock_name,
            quantity=pos.quantity,
            entry_price=int(pos.purchase_price),
            current_price=int(pos.current_price),
            take_profit_price=int(pos.take_profit_price) if pos.take_profit_price else None,
            stop_loss_price=int(pos.stop_loss_price) if pos.stop_loss_price else None,
            profit_loss=int(pos.profit_loss),
            profit_loss_ratio=pos.profit_loss_rate / 100.0 if pos.profit_loss_rate else 0.0,
            entry_risk_mode=pos.metadata.get('entry_risk_mode') if pos.metadata else None,
            is_active=pos.metadata.get('is_active', True) if pos.metadata else True
        )

        if session:
            session.add(db_pos)

        return db_pos


class PortfolioSnapshot(Base):
    """포트폴리오 스냅샷 (일일 기록)"""

    __tablename__ = 'portfolio_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 자본금
    total_capital = Column(Integer, nullable=False)
    cash = Column(Integer, nullable=False)
    stock_value = Column(Integer, nullable=False)

    # 수익/손실
    total_profit_loss = Column(Integer, default=0)
    total_profit_loss_ratio = Column(Float, default=0.0)

    # 포지션 정보
    open_positions = Column(Integer, default=0)

    # 리스크 모드
    risk_mode = Column(String(20), nullable=True)

    # 일일 통계
    daily_trades = Column(Integer, default=0)
    daily_profit_loss = Column(Integer, default=0)

    __table_args__ = (
        # 날짜 범위 쿼리 최적화 (일별/주별/월별 분석)
        Index('idx_timestamp_desc', 'timestamp'),
    )

    def __repr__(self):
        return f"<PortfolioSnapshot(timestamp={self.timestamp}, capital={self.total_capital:,}원)>"


class ScanResult(Base):
    """스캔 결과 기록"""

    __tablename__ = 'scan_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 스캔 단계
    scan_stage = Column(String(20), nullable=False, index=True)  # 'fast', 'deep', 'ai'

    # 종목 정보
    stock_code = Column(String(10), nullable=False, index=True)
    stock_name = Column(String(50), nullable=False)

    # 점수
    score = Column(Float, default=0.0)

    # AI 분석 (AI 스캔만)
    ai_score = Column(Float, nullable=True)
    ai_signal = Column(String(10), nullable=True)
    ai_confidence = Column(String(10), nullable=True)
    ai_reasons = Column(Text, nullable=True)  # JSON 문자열

    # 승인 여부
    approved = Column(Boolean, default=False, index=True)

    __table_args__ = (
        Index('idx_scan_stage_timestamp', 'scan_stage', 'timestamp'),
    )

    def __repr__(self):
        return f"<ScanResult({self.scan_stage} scan: {self.stock_name}, score={self.score:.1f})>"


class SystemLog(Base):
    """시스템 로그"""

    __tablename__ = 'system_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 로그 레벨
    level = Column(String(10), nullable=False, index=True)  # 'INFO', 'WARNING', 'ERROR', etc.

    # 로그 내용
    message = Column(Text, nullable=False)

    # 카테고리
    category = Column(String(50), nullable=True, index=True)  # 'trading', 'scanning', 'risk', etc.

    # 추가 데이터 (JSON)
    extra_data = Column(Text, nullable=True)

    def __repr__(self):
        return f"<SystemLog({self.level}: {self.message[:50]})>"


# 데이터베이스 엔진 및 세션
class Database:
    """데이터베이스 관리자"""

    _instance: Optional['Database'] = None
    _engine = None
    _Session = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """초기화"""
        if self._engine is None:
            self._initialize_database()

    def _initialize_database(self):
        """데이터베이스 초기화"""
        try:
            config = get_config()
            db_config = config.database

            db_type = db_config.get('type', 'sqlite')

            if db_type == 'sqlite':
                db_path = db_config.get('path', 'data/autotrade.db')
                db_file = Path(db_path)
                db_file.parent.mkdir(parents=True, exist_ok=True)

                connection_string = f"sqlite:///{db_path}"
            else:
                # PostgreSQL 등 다른 DB 지원 (향후 확장)
                raise NotImplementedError(f"Database type '{db_type}' not implemented yet")

            # 엔진 생성
            self._engine = create_engine(
                connection_string,
                echo=db_config.get('echo', False),
                pool_size=db_config.get('pool_size', 5),
                max_overflow=db_config.get('max_overflow', 10),
            )

            # 테이블 생성 (인덱스 포함)
            Base.metadata.create_all(self._engine)
            logger.info("✅ 데이터베이스 테이블 및 인덱스 생성 완료")

            # Fix v6.1.3: 자동 마이그레이션 - is_virtual 컬럼 추가
            if db_type == 'sqlite':
                self._auto_migrate_is_virtual()

            # 생성된 인덱스 로깅
            for table in Base.metadata.tables.values():
                for index in table.indexes:
                    logger.debug(f"  Index: {index.name} on {table.name}({', '.join([c.name for c in index.columns])})")

            # 세션 팩토리 생성
            self._Session = sessionmaker(bind=self._engine)

            logger.info(f"💾 데이터베이스 초기화 완료: {connection_string}")

        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}", exc_info=True)
            raise

    def _auto_migrate_is_virtual(self):
        """자동 마이그레이션: is_virtual 컬럼 추가"""
        try:
            import sqlite3
            from sqlalchemy import inspect

            # 테이블 스키마 확인
            inspector = inspect(self._engine)
            columns = [col['name'] for col in inspector.get_columns('trades')]

            if 'is_virtual' not in columns:
                logger.info("🔄 자동 마이그레이션: is_virtual 컬럼 추가 중...")

                # Raw SQL로 컬럼 추가
                with self._engine.connect() as conn:
                    conn.execute("ALTER TABLE trades ADD COLUMN is_virtual INTEGER DEFAULT 0 NOT NULL")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_is_virtual ON trades(is_virtual)")
                    conn.commit()

                logger.info("✅ is_virtual 컬럼 추가 완료")
            else:
                logger.debug("  is_virtual 컬럼이 이미 존재합니다")

        except Exception as e:
            # 마이그레이션 실패는 치명적이지 않으므로 경고만 출력
            logger.warning(f"⚠️ is_virtual 자동 마이그레이션 실패 (무시됨): {e}")

    def get_session(self):
        """세션 가져오기"""
        if self._Session is None:
            self._initialize_database()
        return self._Session()

    def close(self):
        """데이터베이스 종료"""
        if self._engine:
            self._engine.dispose()
            logger.info("💾 데이터베이스 종료")


# 싱글톤 인스턴스
_database = Database()


def get_db_session():
    """데이터베이스 세션 가져오기"""
    return _database.get_session()


def close_database():
    """데이터베이스 종료"""
    _database.close()


class BacktestResult(Base):
    """백테스팅 결과"""

    __tablename__ = 'backtest_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 백테스트 정보
    backtest_id = Column(String(50), unique=True, nullable=False, index=True)
    strategy_name = Column(String(50), nullable=False)
    start_date = Column(String(10), nullable=False)
    end_date = Column(String(10), nullable=False)

    # 자본금
    initial_capital = Column(Float, nullable=False)
    final_capital = Column(Float, nullable=False)

    # 수익률
    total_return = Column(Float, nullable=False)
    total_return_pct = Column(Float, nullable=False)

    # 성과 지표
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, nullable=True)
    calmar_ratio = Column(Float, nullable=True)

    # 거래 통계
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)

    # 평균 손익
    avg_win = Column(Float, nullable=True)
    avg_loss = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)

    # 리포트 파일 경로
    report_html_path = Column(String(200), nullable=True)
    report_pdf_path = Column(String(200), nullable=True)

    # 파라미터 (JSON)
    parameters = Column(Text, nullable=True)

    def __repr__(self):
        return f"<BacktestResult({self.strategy_name}: {self.total_return_pct:.2f}%)>"


class OptimizationResult(Base):
    """파라미터 최적화 결과"""

    __tablename__ = 'optimization_results'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 최적화 정보
    optimization_id = Column(String(50), unique=True, nullable=False, index=True)
    strategy_name = Column(String(50), nullable=False)
    method = Column(String(20), nullable=False)  # grid, random, bayesian

    # 최적 파라미터
    best_params = Column(Text, nullable=False)  # JSON
    best_score = Column(Float, nullable=False)

    # 최적화 통계
    n_trials = Column(Integer, nullable=False)
    n_completed = Column(Integer, nullable=False)
    duration_seconds = Column(Float, nullable=False)

    # 결과 상세 (JSON)
    trials_data = Column(Text, nullable=True)

    def __repr__(self):
        return f"<OptimizationResult({self.strategy_name}: score={self.best_score:.4f})>"


class Alert(Base):
    """알림 기록"""

    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 알림 유형
    alert_type = Column(String(50), nullable=False, index=True)  # order_executed, ai_signal, stop_loss, etc.
    severity = Column(String(20), default='info')  # info, warning, error, critical

    # 알림 내용
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)

    # 관련 종목 (선택)
    stock_code = Column(String(10), nullable=True, index=True)
    stock_name = Column(String(50), nullable=True)

    # 전송 채널
    sent_email = Column(Boolean, default=False)
    sent_sms = Column(Boolean, default=False)
    sent_telegram = Column(Boolean, default=False)
    sent_web_push = Column(Boolean, default=False)

    # 읽음 여부
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime, nullable=True)

    # 추가 데이터 (JSON)
    extra_data = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Alert({self.alert_type}: {self.title})>"


class StrategyPerformance(Base):
    """전략 성과 기록"""

    __tablename__ = 'strategy_performances'

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 전략 정보
    strategy_name = Column(String(50), nullable=False, index=True)

    # 기간
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # 성과
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)

    # 수익
    total_profit = Column(Float, default=0.0)
    total_profit_pct = Column(Float, default=0.0)
    avg_profit_per_trade = Column(Float, default=0.0)

    # 파라미터 (JSON)
    parameters = Column(Text, nullable=True)

    def __repr__(self):
        return f"<StrategyPerformance({self.strategy_name}: {self.win_rate:.2f}% win rate)>"


class AnomalyLog(Base):
    """시스템 이상 감지 로그"""

    __tablename__ = 'anomaly_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    detected_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 이상 유형
    anomaly_type = Column(String(50), nullable=False, index=True)  # api_slow, order_failure, balance_drop, etc.
    severity = Column(String(20), default='medium')  # low, medium, high, critical

    # 이상 값
    expected_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)  # 0.0 ~ 1.0

    # 설명
    description = Column(Text, nullable=False)

    # 조치 여부
    action_taken = Column(Boolean, default=False)
    action_description = Column(Text, nullable=True)

    # 추가 데이터 (JSON)
    extra_data = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AnomalyLog({self.anomaly_type}: score={self.anomaly_score:.2f})>"


class MarketRegime(Base):
    """시장 레짐 분류 기록"""

    __tablename__ = 'market_regimes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    classified_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 시장 레짐
    regime_type = Column(String(20), nullable=False)  # bull, bear, sideways
    volatility_level = Column(String(20), nullable=False)  # low, medium, high

    # 신뢰도
    confidence = Column(Float, nullable=False)  # 0.0 ~ 1.0

    # 지표 값
    vix_level = Column(Float, nullable=True)
    trend_strength = Column(Float, nullable=True)
    market_momentum = Column(Float, nullable=True)

    # 추천 전략
    recommended_strategy = Column(String(50), nullable=True)

    # 추가 데이터 (JSON)
    indicators = Column(Text, nullable=True)

    def __repr__(self):
        return f"<MarketRegime({self.regime_type}, {self.volatility_level})>"


__all__ = [
    'Trade',
    'Position',
    'PortfolioSnapshot',
    'ScanResult',
    'SystemLog',
    'BacktestResult',
    'OptimizationResult',
    'Alert',
    'StrategyPerformance',
    'AnomalyLog',
    'MarketRegime',
    'Database',
    'get_db_session',
    'close_database',
]
