"""
AutoTrade Pro v4.0 - FastAPI REST API Server
완전한 REST API 엔드포인트 제공

주요 기능:
- 계좌 조회 및 관리
- 종목 분석 및 검색
- 전략 실행 및 관리
- 백테스팅 및 최적화
- 시스템 모니터링
- 설정 관리
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import uvicorn

# App initialization
app = FastAPI(
    title="AutoTrade Pro API",
    description="Complete REST API for AutoTrade Pro Trading System",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - Security: Restrict to specific origins
import os
ALLOWED_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000,http://localhost:8000').split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global bot instance (will be injected)
bot_instance = None


# ============================================================================
# Pydantic Models
# ============================================================================

class SystemStatus(BaseModel):
    """시스템 상태"""
    running: bool
    trading_enabled: bool
    uptime: str
    last_update: str
    test_mode: Dict[str, Any]
    connections: Dict[str, bool]


class AccountInfo(BaseModel):
    """계좌 정보"""
    account_number: str
    total_assets: float
    cash: float
    stock_value: float
    profit_loss: float
    profit_loss_pct: float


class StockInfo(BaseModel):
    """종목 정보"""
    code: str
    name: str
    current_price: float
    change_rate: float
    volume: int
    market_cap: Optional[float] = None


class AnalysisRequest(BaseModel):
    """AI 분석 요청"""
    stock_code: str
    stock_name: str
    analyzer_type: str = Field(default="gemini", description="gemini, gpt4, claude, ensemble")
    include_news: bool = True


class BacktestRequest(BaseModel):
    """백테스팅 요청"""
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float = 10000000
    stock_codes: Optional[List[str]] = None


class OptimizationRequest(BaseModel):
    """파라미터 최적화 요청"""
    strategy_name: str
    param_ranges: Dict[str, List[float]]
    optimization_method: str = Field(default="bayesian", description="grid, random, bayesian")
    n_trials: int = 50


class TradeOrder(BaseModel):
    """주문 요청"""
    stock_code: str
    order_type: str = Field(description="buy, sell")
    price_type: str = Field(default="market", description="market, limit, stop")
    quantity: int
    price: Optional[float] = None


class SettingsUpdate(BaseModel):
    """설정 업데이트"""
    category: str
    settings: Dict[str, Any]


# ============================================================================
# Health Check & System Status
# ============================================================================

@app.get("/")
async def root():
    """API 루트"""
    return {
        "name": "AutoTrade Pro API",
        "version": "4.0.0",
        "status": "running",
        "docs": "/docs",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/status", response_model=SystemStatus)
async def get_system_status():
    """시스템 전체 상태 조회 (실제 연결 상태 확인)"""
    try:
        from features.status_monitor import get_status_monitor

        # 상태 모니터 인스턴스 가져오기
        monitor = get_status_monitor()

        # 모든 시스템 상태 확인
        status_summary = monitor.check_all_status()

        # 연결 상태 추출
        components = status_summary.get('components', {})
        connections = {
            "rest_api": components.get('rest_api', {}).get('connected', False),
            "websocket": components.get('websocket', {}).get('connected', False),
            "gemini": components.get('gemini', {}).get('connected', False)
        }

        # 테스트 모드 정보
        test_mode_info = components.get('test_mode', {})
        test_mode = {
            "active": test_mode_info.get('enabled', False),
            "test_date": test_mode_info.get('test_date'),
            "reason": test_mode_info.get('reason')
        }

        # 시스템 실행 상태 (bot_instance 확인)
        running = bot_instance is not None
        trading_enabled = running and connections.get('rest_api', False)

        # 업타임 계산 (TODO: 실제 시작 시간 추적 필요)
        uptime = "Running"

        return SystemStatus(
            running=running,
            trading_enabled=trading_enabled,
            uptime=uptime,
            last_update=status_summary.get('timestamp', datetime.now().isoformat()),
            test_mode=test_mode,
            connections=connections
        )
    except Exception as e:
        logger.error(f"Error getting system status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Account APIs
# ============================================================================

@app.get("/api/account/info", response_model=AccountInfo)
async def get_account_info():
    """계좌 정보 조회"""
    try:
        if bot_instance is None or bot_instance.account_api is None:
            logger.warning("Bot instance not initialized, returning default data")
            return AccountInfo(
                account_number="Not Connected",
                total_assets=0,
                cash=0,
                stock_value=0,
                profit_loss=0,
                profit_loss_pct=0
            )

        # 예수금 조회
        deposit_info = bot_instance.account_api.get_deposit()
        # 계좌평가잔고 조회
        balance_info = bot_instance.account_api.get_account_balance()

        if not deposit_info or not balance_info:
            logger.error("Failed to get account info from API")
            return AccountInfo(
                account_number="Error",
                total_assets=0,
                cash=0,
                stock_value=0,
                profit_loss=0,
                profit_loss_pct=0
            )

        # 데이터 파싱
        deposit_data = deposit_info.get('output', {})
        balance_data = balance_info.get('output1', [{}])[0] if balance_info.get('output1') else {}

        # 현금 및 자산 정보
        cash = float(deposit_data.get('d_ord_aval_cash', 0) or 0)  # 주문가능현금
        stock_value = float(balance_data.get('sttl_prsm', 0) or 0)  # 평가금액
        total_assets = float(deposit_data.get('tot_evl_amt', 0) or 0)  # 총평가금액
        profit_loss = float(balance_data.get('prsm_sum', 0) or 0)  # 평가손익합계

        # 수익률 계산
        if total_assets > 0:
            profit_loss_pct = (profit_loss / (total_assets - profit_loss)) * 100
        else:
            profit_loss_pct = 0

        logger.info(f"Account info retrieved: total={total_assets:,.0f}, cash={cash:,.0f}")

        return AccountInfo(
            account_number=bot_instance.client.account_no if bot_instance.client else "Unknown",
            total_assets=total_assets,
            cash=cash,
            stock_value=stock_value,
            profit_loss=profit_loss,
            profit_loss_pct=round(profit_loss_pct, 2)
        )
    except Exception as e:
        logger.error(f"Error getting account info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/account/positions")
async def get_positions():
    """보유 포지션 조회"""
    try:
        if bot_instance is None or bot_instance.account_api is None:
            logger.warning("Bot instance not initialized")
            return {"positions": [], "total_count": 0}

        # 체결잔고 조회 (KRX)
        balance_krx = bot_instance.account_api.get_balance(market_type="KRX")
        # NXT 시장도 조회
        balance_nxt = bot_instance.account_api.get_balance(market_type="NXT")

        positions = []

        # KRX 시장 포지션 처리
        if balance_krx and balance_krx.get('return_code') == 0:
            output2 = balance_krx.get('output2', [])
            for item in output2:
                stock_code = item.get('종목코드', '')
                # ✅ v5.16: _NX 접미사 유지

                stock_name = item.get('종목명', '')
                quantity = int(item.get('보유수량', 0) or 0)
                avg_price = float(item.get('매입단가', 0) or 0)
                current_price = float(item.get('현재가', 0) or 0)
                profit_loss = float(item.get('평가손익', 0) or 0)

                # 수익률 계산
                if avg_price > 0:
                    profit_loss_pct = ((current_price - avg_price) / avg_price) * 100
                else:
                    profit_loss_pct = 0

                positions.append({
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "quantity": quantity,
                    "avg_price": avg_price,
                    "current_price": current_price,
                    "profit_loss": profit_loss,
                    "profit_loss_pct": round(profit_loss_pct, 2),
                    "market": "KRX"
                })

        # NXT 시장 포지션 처리
        if balance_nxt and balance_nxt.get('return_code') == 0:
            output2 = balance_nxt.get('output2', [])
            for item in output2:
                stock_code = item.get('종목코드', '')
                # ✅ v5.16: _NX 접미사 유지

                stock_name = item.get('종목명', '')
                quantity = int(item.get('보유수량', 0) or 0)
                avg_price = float(item.get('매입단가', 0) or 0)
                current_price = float(item.get('현재가', 0) or 0)
                profit_loss = float(item.get('평가손익', 0) or 0)

                # 수익률 계산
                if avg_price > 0:
                    profit_loss_pct = ((current_price - avg_price) / avg_price) * 100
                else:
                    profit_loss_pct = 0

                positions.append({
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "quantity": quantity,
                    "avg_price": avg_price,
                    "current_price": current_price,
                    "profit_loss": profit_loss,
                    "profit_loss_pct": round(profit_loss_pct, 2),
                    "market": "NXT"
                })

        logger.info(f"Retrieved {len(positions)} positions")

        return {
            "positions": positions,
            "total_count": len(positions)
        }
    except Exception as e:
        logger.error(f"Error getting positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Market & Stock APIs
# ============================================================================

@app.get("/api/market/stocks")
async def search_stocks(query: str = "", limit: int = 20):
    """종목 검색 - 거래량 상위 종목 반환"""
    try:
        if bot_instance is None or bot_instance.market_api is None:
            logger.warning("Bot instance not initialized")
            return {"stocks": [], "total": 0}

        # 거래량 순위로 종목 조회 (검색어 필터링은 추후 구현)
        volume_rank = bot_instance.market_api.get_volume_rank(
            market='ALL',
            limit=limit
        )

        stocks = []
        for item in volume_rank:
            stocks.append({
                "code": item.get('code', ''),
                "name": item.get('name', ''),
                "current_price": item.get('current_price', 0),
                "change_rate": item.get('change_rate', 0),
                "volume": item.get('volume', 0)
            })

        # 검색어가 있으면 필터링
        if query:
            query_lower = query.lower()
            stocks = [
                s for s in stocks
                if query_lower in s['name'].lower() or query_lower in s['code']
            ]

        logger.info(f"Found {len(stocks)} stocks")

        return {
            "stocks": stocks,
            "total": len(stocks)
        }
    except Exception as e:
        logger.error(f"Error searching stocks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/stock/{stock_code}")
async def get_stock_detail(stock_code: str):
    """종목 상세 정보 (✅ v5.15: NXT 시간대 실시간 현재가 반영)"""
    try:
        if bot_instance is None or bot_instance.market_api is None:
            logger.warning("Bot instance not initialized")
            return {
                "code": stock_code,
                "name": "Error",
                "current_price": 0,
                "change_rate": 0,
                "volume": 0
            }

        # ✅ v5.15: NXT 실시간 가격 관리자 사용
        from utils.nxt_realtime_price import get_nxt_price_manager
        nxt_manager = get_nxt_price_manager(bot_instance.market_api)

        # 종목 현재가 조회 (NXT 시간대 자동 처리)
        price_result = nxt_manager.get_realtime_price(stock_code)

        if not price_result:
            # Fallback to direct API call
            price_result = bot_instance.market_api.get_stock_price(stock_code)
            if not price_result:
                logger.error(f"Failed to get stock price for {stock_code}")
                return {
                    "code": stock_code,
                    "name": "Unknown",
                    "current_price": 0,
                    "change_rate": 0,
                    "volume": 0
                }
            # Convert to expected format
            price_info = price_result
        else:
            # NXT manager returns different format - convert to API format
            price_info = {
                'stock_name': stock_code,  # Will try to get from orderbook
                'current_price': price_result['current_price'],
                'change_rate': price_result.get('change_rate', 0),
                'volume': price_result.get('volume', 0),
                'high_price': 0,
                'low_price': 0,
                'open_price': 0
            }

        if not price_info:
            logger.error(f"Failed to get stock price for {stock_code}")
            return {
                "code": stock_code,
                "name": "Unknown",
                "current_price": 0,
                "change_rate": 0,
                "volume": 0
            }

        # 호가 정보 조회
        orderbook = bot_instance.market_api.get_orderbook(stock_code)

        result = {
            "code": stock_code,
            "name": price_info.get('stock_name', stock_code),
            "current_price": int(price_info.get('current_price', 0) or 0),
            "change_rate": float(price_info.get('change_rate', 0) or 0),
            "volume": int(price_info.get('volume', 0) or 0),
            "high_price": int(price_info.get('high_price', 0) or 0),
            "low_price": int(price_info.get('low_price', 0) or 0),
            "open_price": int(price_info.get('open_price', 0) or 0),
        }

        # 호가 정보 추가
        if orderbook:
            result["orderbook"] = {
                "buy_price1": orderbook.get('buy_price1', 0),
                "sell_price1": orderbook.get('sell_price1', 0),
                "buy_volume1": orderbook.get('buy_volume1', 0),
                "sell_volume1": orderbook.get('sell_volume1', 0),
            }

        logger.info(f"Stock detail retrieved: {stock_code} - {result['name']}")

        return result
    except Exception as e:
        logger.error(f"Error getting stock detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AI Analysis APIs
# ============================================================================

@app.post("/api/analysis/analyze")
async def analyze_stock(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """AI 종목 분석"""
    try:
        # TODO: Implement real AI analysis
        return {
            "stock_code": request.stock_code,
            "stock_name": request.stock_name,
            "analyzer": request.analyzer_type,
            "status": "analyzing",
            "message": "분석이 시작되었습니다. 결과는 잠시 후 확인하세요."
        }
    except Exception as e:
        logger.error(f"Error analyzing stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analysis/results/{stock_code}")
async def get_analysis_results(stock_code: str):
    """AI 분석 결과 조회"""
    try:
        # TODO: Implement real analysis results retrieval
        return {
            "stock_code": stock_code,
            "timestamp": datetime.now().isoformat(),
            "recommendation": "BUY",
            "confidence": 0.85,
            "score": 8.5,
            "reasoning": "긍정적인 시장 전망과 강력한 기술적 지표",
            "details": {}
        }
    except Exception as e:
        logger.error(f"Error getting analysis results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Backtesting APIs
# ============================================================================

@app.post("/api/backtest/run")
async def run_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """백테스팅 실행"""
    try:
        # TODO: Implement real backtesting
        return {
            "backtest_id": "bt_" + datetime.now().strftime("%Y%m%d%H%M%S"),
            "status": "running",
            "message": "백테스팅이 시작되었습니다."
        }
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest/results/{backtest_id}")
async def get_backtest_results(backtest_id: str):
    """백테스팅 결과 조회"""
    try:
        # TODO: Implement real backtest results retrieval
        return {
            "backtest_id": backtest_id,
            "status": "completed",
            "results": {
                "total_return": 15.5,
                "sharpe_ratio": 1.8,
                "max_drawdown": -8.5,
                "win_rate": 65.0
            }
        }
    except Exception as e:
        logger.error(f"Error getting backtest results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest/report/{backtest_id}")
async def download_backtest_report(backtest_id: str, format: str = "html"):
    """백테스팅 리포트 다운로드 (HTML/PDF)"""
    try:
        # TODO: Implement real report generation
        report_path = f"/tmp/{backtest_id}_report.{format}"
        return FileResponse(
            path=report_path,
            filename=f"backtest_report_{backtest_id}.{format}",
            media_type="application/pdf" if format == "pdf" else "text/html"
        )
    except Exception as e:
        logger.error(f"Error downloading report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Optimization APIs
# ============================================================================

@app.post("/api/optimization/run")
async def run_optimization(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """전략 파라미터 최적화 실행"""
    try:
        # TODO: Implement real optimization
        return {
            "optimization_id": "opt_" + datetime.now().strftime("%Y%m%d%H%M%S"),
            "status": "running",
            "message": "최적화가 시작되었습니다."
        }
    except Exception as e:
        logger.error(f"Error running optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/optimization/results/{optimization_id}")
async def get_optimization_results(optimization_id: str):
    """최적화 결과 조회"""
    try:
        # TODO: Implement real optimization results retrieval
        return {
            "optimization_id": optimization_id,
            "status": "completed",
            "best_params": {
                "param1": 0.5,
                "param2": 20
            },
            "best_score": 0.85
        }
    except Exception as e:
        logger.error(f"Error getting optimization results: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Trading APIs
# ============================================================================

@app.post("/api/trading/order")
async def place_order(order: TradeOrder):
    """주문 실행"""
    try:
        # TODO: Implement real order placement
        return {
            "order_id": "ord_" + datetime.now().strftime("%Y%m%d%H%M%S"),
            "status": "submitted",
            "message": "주문이 제출되었습니다."
        }
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trading/orders")
async def get_orders(status: Optional[str] = None):
    """주문 내역 조회"""
    try:
        # TODO: Implement real orders retrieval
        return {
            "orders": [],
            "total": 0
        }
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Settings APIs
# ============================================================================

@app.get("/api/settings")
async def get_all_settings():
    """모든 설정 조회"""
    try:
        # TODO: Implement real settings retrieval
        return {
            "risk_management": {},
            "trading_params": {},
            "ai_settings": {},
            "notification_settings": {}
        }
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/settings/{category}")
async def get_settings_by_category(category: str):
    """카테고리별 설정 조회"""
    try:
        # TODO: Implement real settings retrieval
        return {
            "category": category,
            "settings": {}
        }
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/settings/{category}")
async def update_settings(category: str, settings: Dict[str, Any]):
    """설정 업데이트"""
    try:
        # TODO: Implement real settings update
        return {
            "category": category,
            "status": "updated",
            "message": "설정이 업데이트되었습니다."
        }
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Strategy APIs
# ============================================================================

@app.get("/api/strategies")
async def get_strategies():
    """전략 목록 조회"""
    try:
        return {
            "strategies": [
                {"name": "momentum", "description": "모멘텀 전략"},
                {"name": "volatility_breakout", "description": "변동성 돌파 전략"},
                {"name": "pairs_trading", "description": "페어 트레이딩"}
            ]
        }
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/strategies/{strategy_name}/execute")
async def execute_strategy(strategy_name: str, params: Optional[Dict[str, Any]] = None):
    """전략 실행"""
    try:
        return {
            "strategy": strategy_name,
            "status": "executing",
            "message": f"{strategy_name} 전략이 실행되었습니다."
        }
    except Exception as e:
        logger.error(f"Error executing strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Monitoring & Logs
# ============================================================================

@app.get("/api/monitoring/system")
async def get_system_monitoring():
    """시스템 모니터링 정보"""
    try:
        return {
            "cpu_usage": 45.5,
            "memory_usage": 60.2,
            "api_response_time": 0.15,
            "active_connections": 5
        }
    except Exception as e:
        logger.error(f"Error getting monitoring info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs/recent")
async def get_recent_logs(limit: int = 100):
    """최근 로그 조회"""
    try:
        return {
            "logs": [],
            "total": 0
        }
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Main Entry Point
# ============================================================================

def set_bot_instance(instance):
    """봇 인스턴스 설정"""
    global bot_instance
    bot_instance = instance


if __name__ == "__main__":
    logger.info("Starting AutoTrade Pro API Server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
