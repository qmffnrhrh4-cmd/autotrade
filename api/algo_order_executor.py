"""
Algorithmic Order Execution
Advanced order execution strategies: TWAP, VWAP, Iceberg, etc.
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import math

from ..config.constants import DELAYS
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class AlgoType(Enum):
    """Algorithm execution types"""
    TWAP = "twap"  # Time-Weighted Average Price
    VWAP = "vwap"  # Volume-Weighted Average Price
    ICEBERG = "iceberg"  # Hide large orders
    POV = "pov"  # Percentage of Volume
    ADAPTIVE = "adaptive"  # Adaptive execution
    MARKET = "market"  # Immediate market order


class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class AlgoOrderExecutor:
    """
    Advanced algorithmic order executor

    Features:
    - TWAP (Time-Weighted Average Price)
    - VWAP (Volume-Weighted Average Price)
    - Iceberg orders
    - POV (Percentage of Volume)
    - Adaptive execution
    - Slippage optimization
    """

    def __init__(self, order_api, market_api):
        """
        Initialize algo executor

        Args:
            order_api: Order API instance
            market_api: Market data API instance
        """
        self.order_api = order_api
        self.market_api = market_api

        # Execution tracking
        self.active_algos: Dict[str, Dict] = {}
        self.completed_algos: List[Dict] = []

        logger.info("Algorithmic Order Executor initialized")

    def execute_twap(
        self,
        stock_code: str,
        total_quantity: int,
        side: OrderSide,
        duration_minutes: int = 60,
        num_slices: int = 10
    ) -> Dict[str, Any]:
        """
        Execute TWAP (Time-Weighted Average Price) order

        Splits order into equal slices over time period

        Args:
            stock_code: Stock code
            total_quantity: Total quantity to execute
            side: BUY or SELL
            duration_minutes: Total duration in minutes
            num_slices: Number of order slices

        Returns:
            Execution summary
        """
        algo_id = self._generate_algo_id("TWAP")

        logger.info(
            f"[{algo_id}] Starting TWAP: {stock_code} "
            f"{side.value.upper()} {total_quantity:,} shares "
            f"over {duration_minutes}min in {num_slices} slices"
        )

        # Calculate slice parameters
        slice_quantity = math.ceil(total_quantity / num_slices)
        slice_interval = duration_minutes * 60 / num_slices  # seconds

        # Track execution
        self.active_algos[algo_id] = {
            'algo_type': 'TWAP',
            'stock_code': stock_code,
            'total_quantity': total_quantity,
            'executed_quantity': 0,
            'side': side.value,
            'num_slices': num_slices,
            'completed_slices': 0,
            'start_time': datetime.now(),
            'fills': [],
            'status': 'running'
        }

        # Execute slices
        for slice_num in range(num_slices):
            # Calculate quantity for this slice
            remaining = total_quantity - self.active_algos[algo_id]['executed_quantity']
            current_slice_qty = min(slice_quantity, remaining)

            if current_slice_qty <= 0:
                break

            try:
                # Get current market price
                market_data = self.market_api.get_current_price(stock_code)
                current_price = market_data.get('current_price', 0)

                # Place order
                if side == OrderSide.BUY:
                    order = self.order_api.buy(
                        stock_code=stock_code,
                        quantity=current_slice_qty,
                        price=current_price,
                        order_type='02'  # 지정가
                    )
                else:
                    order = self.order_api.sell(
                        stock_code=stock_code,
                        quantity=current_slice_qty,
                        price=current_price,
                        order_type='02'
                    )

                # Record fill
                self.active_algos[algo_id]['fills'].append({
                    'slice_num': slice_num + 1,
                    'quantity': current_slice_qty,
                    'price': current_price,
                    'timestamp': datetime.now().isoformat(),
                    'order': order
                })

                self.active_algos[algo_id]['executed_quantity'] += current_slice_qty
                self.active_algos[algo_id]['completed_slices'] += 1

                logger.info(
                    f"[{algo_id}] Slice {slice_num + 1}/{num_slices}: "
                    f"{current_slice_qty:,} @ {current_price:,}원"
                )

                # Wait before next slice (unless last slice)
                if slice_num < num_slices - 1:
                    time.sleep(slice_interval)

            except Exception as e:
                logger.error(f"[{algo_id}] Slice {slice_num + 1} failed: {e}")
                self.active_algos[algo_id]['status'] = 'error'
                break

        # Mark as completed
        self.active_algos[algo_id]['status'] = 'completed'
        self.active_algos[algo_id]['end_time'] = datetime.now()

        # Calculate summary
        summary = self._calculate_execution_summary(algo_id)

        # Move to completed
        self.completed_algos.append(self.active_algos[algo_id])
        del self.active_algos[algo_id]

        logger.info(f"[{algo_id}] TWAP completed: {summary}")

        return summary

    def execute_vwap(
        self,
        stock_code: str,
        total_quantity: int,
        side: OrderSide,
        duration_minutes: int = 60,
        target_participation: float = 0.10
    ) -> Dict[str, Any]:
        """
        Execute VWAP (Volume-Weighted Average Price) order

        Adjusts order rate based on market volume

        Args:
            stock_code: Stock code
            total_quantity: Total quantity
            side: BUY or SELL
            duration_minutes: Duration
            target_participation: Target % of market volume (0-1)

        Returns:
            Execution summary
        """
        algo_id = self._generate_algo_id("VWAP")

        logger.info(
            f"[{algo_id}] Starting VWAP: {stock_code} "
            f"{side.value.upper()} {total_quantity:,} shares "
            f"with {target_participation*100:.1f}% participation"
        )

        self.active_algos[algo_id] = {
            'algo_type': 'VWAP',
            'stock_code': stock_code,
            'total_quantity': total_quantity,
            'executed_quantity': 0,
            'side': side.value,
            'target_participation': target_participation,
            'start_time': datetime.now(),
            'fills': [],
            'status': 'running'
        }

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        # Execute with volume awareness
        while time.time() < end_time:
            remaining = total_quantity - self.active_algos[algo_id]['executed_quantity']

            if remaining <= 0:
                break

            try:
                # Get current market volume
                market_data = self.market_api.get_current_price(stock_code)
                current_volume = market_data.get('volume', 0)
                current_price = market_data.get('current_price', 0)

                # Calculate order quantity based on volume
                # (In reality, would use rolling volume window)
                estimated_market_volume = current_volume * 0.01  # 1% of daily volume
                order_qty = min(
                    int(estimated_market_volume * target_participation),
                    remaining
                )

                if order_qty > 0:
                    # Place order
                    if side == OrderSide.BUY:
                        order = self.order_api.buy(
                            stock_code=stock_code,
                            quantity=order_qty,
                            price=current_price,
                            order_type='02'
                        )
                    else:
                        order = self.order_api.sell(
                            stock_code=stock_code,
                            quantity=order_qty,
                            price=current_price,
                            order_type='02'
                        )

                    # Record fill
                    self.active_algos[algo_id]['fills'].append({
                        'quantity': order_qty,
                        'price': current_price,
                        'timestamp': datetime.now().isoformat(),
                        'order': order
                    })

                    self.active_algos[algo_id]['executed_quantity'] += order_qty

                    logger.info(
                        f"[{algo_id}] Executed {order_qty:,} @ {current_price:,}원 "
                        f"({self.active_algos[algo_id]['executed_quantity']:,}/{total_quantity:,})"
                    )

                time.sleep(DELAYS['order_check'])

            except Exception as e:
                logger.error(f"[{algo_id}] VWAP execution error: {e}")
                self.active_algos[algo_id]['status'] = 'error'
                break

        # Complete
        self.active_algos[algo_id]['status'] = 'completed'
        self.active_algos[algo_id]['end_time'] = datetime.now()

        summary = self._calculate_execution_summary(algo_id)

        self.completed_algos.append(self.active_algos[algo_id])
        del self.active_algos[algo_id]

        logger.info(f"[{algo_id}] VWAP completed: {summary}")

        return summary

    def execute_iceberg(
        self,
        stock_code: str,
        total_quantity: int,
        display_quantity: int,
        side: OrderSide,
        limit_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Execute Iceberg order

        Hides large order by showing only small portion

        Args:
            stock_code: Stock code
            total_quantity: Total hidden quantity
            display_quantity: Visible quantity per order
            side: BUY or SELL
            limit_price: Limit price (None for market)

        Returns:
            Execution summary
        """
        algo_id = self._generate_algo_id("ICEBERG")

        logger.info(
            f"[{algo_id}] Starting ICEBERG: {stock_code} "
            f"{side.value.upper()} {total_quantity:,} shares "
            f"(display: {display_quantity:,})"
        )

        self.active_algos[algo_id] = {
            'algo_type': 'ICEBERG',
            'stock_code': stock_code,
            'total_quantity': total_quantity,
            'display_quantity': display_quantity,
            'executed_quantity': 0,
            'side': side.value,
            'start_time': datetime.now(),
            'fills': [],
            'status': 'running'
        }

        # Execute in hidden slices
        while self.active_algos[algo_id]['executed_quantity'] < total_quantity:
            remaining = total_quantity - self.active_algos[algo_id]['executed_quantity']
            order_qty = min(display_quantity, remaining)

            try:
                # Get current price if not specified
                if limit_price is None:
                    market_data = self.market_api.get_current_price(stock_code)
                    price = market_data.get('current_price', 0)
                else:
                    price = limit_price

                # Place order
                if side == OrderSide.BUY:
                    order = self.order_api.buy(
                        stock_code=stock_code,
                        quantity=order_qty,
                        price=price,
                        order_type='02'
                    )
                else:
                    order = self.order_api.sell(
                        stock_code=stock_code,
                        quantity=order_qty,
                        price=price,
                        order_type='02'
                    )

                # Record fill
                self.active_algos[algo_id]['fills'].append({
                    'quantity': order_qty,
                    'price': price,
                    'timestamp': datetime.now().isoformat(),
                    'order': order
                })

                self.active_algos[algo_id]['executed_quantity'] += order_qty

                logger.info(
                    f"[{algo_id}] Slice executed: {order_qty:,} @ {price:,}원 "
                    f"({self.active_algos[algo_id]['executed_quantity']:,}/{total_quantity:,})"
                )

                # Small delay between slices
                time.sleep(5)

            except Exception as e:
                logger.error(f"[{algo_id}] Iceberg slice failed: {e}")
                self.active_algos[algo_id]['status'] = 'error'
                break

        # Complete
        self.active_algos[algo_id]['status'] = 'completed'
        self.active_algos[algo_id]['end_time'] = datetime.now()

        summary = self._calculate_execution_summary(algo_id)

        self.completed_algos.append(self.active_algos[algo_id])
        del self.active_algos[algo_id]

        logger.info(f"[{algo_id}] ICEBERG completed: {summary}")

        return summary

    def execute_adaptive(
        self,
        stock_code: str,
        total_quantity: int,
        side: OrderSide,
        urgency: float = 0.5,
        duration_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Execute Adaptive algorithm

        Adapts to market conditions in real-time

        Args:
            stock_code: Stock code
            total_quantity: Total quantity
            side: BUY or SELL
            urgency: Urgency level (0=patient, 1=aggressive)
            duration_minutes: Maximum duration

        Returns:
            Execution summary
        """
        algo_id = self._generate_algo_id("ADAPTIVE")

        logger.info(
            f"[{algo_id}] Starting ADAPTIVE: {stock_code} "
            f"{side.value.upper()} {total_quantity:,} shares "
            f"(urgency: {urgency:.2f})"
        )

        self.active_algos[algo_id] = {
            'algo_type': 'ADAPTIVE',
            'stock_code': stock_code,
            'total_quantity': total_quantity,
            'executed_quantity': 0,
            'side': side.value,
            'urgency': urgency,
            'start_time': datetime.now(),
            'fills': [],
            'status': 'running'
        }

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        while time.time() < end_time:
            remaining = total_quantity - self.active_algos[algo_id]['executed_quantity']

            if remaining <= 0:
                break

            try:
                # Get market conditions
                market_data = self.market_api.get_current_price(stock_code)
                current_price = market_data.get('current_price', 0)
                volume = market_data.get('volume', 0)

                # Adapt order size based on:
                # - Remaining time
                # - Market volatility
                # - Urgency level
                time_remaining = end_time - time.time()
                time_fraction = time_remaining / (duration_minutes * 60)

                # More aggressive as time runs out
                aggression = 1 - (time_fraction * (1 - urgency))

                # Calculate order size
                order_qty = int(remaining * aggression * 0.2)  # Up to 20% of remaining
                order_qty = max(1, min(order_qty, remaining))

                # Place order
                if side == OrderSide.BUY:
                    order = self.order_api.buy(
                        stock_code=stock_code,
                        quantity=order_qty,
                        price=current_price,
                        order_type='02'
                    )
                else:
                    order = self.order_api.sell(
                        stock_code=stock_code,
                        quantity=order_qty,
                        price=current_price,
                        order_type='02'
                    )

                # Record fill
                self.active_algos[algo_id]['fills'].append({
                    'quantity': order_qty,
                    'price': current_price,
                    'aggression': aggression,
                    'timestamp': datetime.now().isoformat(),
                    'order': order
                })

                self.active_algos[algo_id]['executed_quantity'] += order_qty

                logger.info(
                    f"[{algo_id}] Executed {order_qty:,} @ {current_price:,}원 "
                    f"(aggression: {aggression:.2f})"
                )

                # Adaptive wait time
                wait_time = 10 * (1 - aggression) + 5  # 5-15 seconds
                time.sleep(wait_time)

            except Exception as e:
                logger.error(f"[{algo_id}] Adaptive execution error: {e}")
                self.active_algos[algo_id]['status'] = 'error'
                break

        # Complete
        self.active_algos[algo_id]['status'] = 'completed'
        self.active_algos[algo_id]['end_time'] = datetime.now()

        summary = self._calculate_execution_summary(algo_id)

        self.completed_algos.append(self.active_algos[algo_id])
        del self.active_algos[algo_id]

        logger.info(f"[{algo_id}] ADAPTIVE completed: {summary}")

        return summary

    def _generate_algo_id(self, algo_type: str) -> str:
        """Generate unique algorithm ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{algo_type}_{timestamp}"

    def _calculate_execution_summary(self, algo_id: str) -> Dict[str, Any]:
        """
        Calculate execution summary statistics
        """
        algo = self.active_algos.get(algo_id, {})

        if not algo.get('fills'):
            return {
                'algo_id': algo_id,
                'status': algo.get('status', 'unknown'),
                'executed_quantity': 0,
                'average_price': 0,
                'total_value': 0
            }

        # Calculate weighted average price
        total_value = sum(f['quantity'] * f['price'] for f in algo['fills'])
        total_qty = sum(f['quantity'] for f in algo['fills'])
        avg_price = total_value / total_qty if total_qty > 0 else 0

        # Calculate duration
        duration = None
        if 'end_time' in algo and 'start_time' in algo:
            duration = (algo['end_time'] - algo['start_time']).total_seconds()

        return {
            'algo_id': algo_id,
            'algo_type': algo.get('algo_type'),
            'stock_code': algo.get('stock_code'),
            'status': algo.get('status'),
            'total_quantity': algo.get('total_quantity'),
            'executed_quantity': total_qty,
            'fill_rate': (total_qty / algo.get('total_quantity', 1)) * 100,
            'average_price': round(avg_price, 2),
            'total_value': round(total_value, 2),
            'num_fills': len(algo['fills']),
            'duration_seconds': duration,
            'start_time': algo.get('start_time'),
            'end_time': algo.get('end_time')
        }

    def get_active_algorithms(self) -> List[Dict]:
        """Get all active algorithms"""
        return list(self.active_algos.values())

    def get_completed_algorithms(self, limit: int = 20) -> List[Dict]:
        """Get recent completed algorithms"""
        return self.completed_algos[-limit:]

    def cancel_algorithm(self, algo_id: str) -> bool:
        """
        Cancel running algorithm

        Args:
            algo_id: Algorithm ID

        Returns:
            Success status
        """
        if algo_id in self.active_algos:
            self.active_algos[algo_id]['status'] = 'cancelled'
            logger.info(f"Algorithm {algo_id} cancelled")
            return True
        return False
