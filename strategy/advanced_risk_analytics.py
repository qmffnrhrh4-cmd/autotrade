"""
Advanced Risk Analytics
Professional-grade risk management and analytics
- Value at Risk (VaR)
- Monte Carlo Simulation
- Sharpe/Sortino Ratios
- Maximum Drawdown
- Risk-adjusted returns
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from scipy import stats
import math

from utils.logger import setup_logger

logger = setup_logger(__name__)


class AdvancedRiskAnalytics:
    """
    Professional risk analytics engine

    Features:
    - Value at Risk (VaR) - Historical, Parametric, Monte Carlo
    - Conditional VaR (CVaR/Expected Shortfall)
    - Sharpe Ratio
    - Sortino Ratio
    - Maximum Drawdown
    - Calmar Ratio
    - Beta and Alpha calculations
    - Monte Carlo simulations
    - Stress testing
    """

    def __init__(self, confidence_level: float = 0.95):
        """
        Initialize risk analytics

        Args:
            confidence_level: Confidence level for VaR (e.g., 0.95 for 95%)
        """
        self.confidence_level = confidence_level

        logger.info(f"Advanced Risk Analytics initialized (confidence: {confidence_level})")

    def calculate_var_historical(
        self,
        returns: List[float],
        confidence_level: Optional[float] = None
    ) -> float:
        """
        Calculate Value at Risk using historical method

        Args:
            returns: Historical returns (as percentages)
            confidence_level: Confidence level (overrides default)

        Returns:
            VaR value (negative number representing potential loss)
        """
        if not returns or len(returns) < 2:
            return 0.0

        conf_level = confidence_level or self.confidence_level

        # Sort returns
        sorted_returns = sorted(returns)

        # Find percentile
        index = int((1 - conf_level) * len(sorted_returns))
        var = sorted_returns[index]

        logger.debug(
            f"Historical VaR ({conf_level*100:.0f}% confidence): {var:.2f}%"
        )

        return var

    def calculate_var_parametric(
        self,
        returns: List[float],
        confidence_level: Optional[float] = None
    ) -> float:
        """
        Calculate Value at Risk using parametric (variance-covariance) method

        Assumes returns are normally distributed

        Args:
            returns: Historical returns
            confidence_level: Confidence level

        Returns:
            VaR value
        """
        if not returns or len(returns) < 2:
            return 0.0

        conf_level = confidence_level or self.confidence_level

        # Calculate mean and std
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        # Z-score for confidence level
        z_score = stats.norm.ppf(1 - conf_level)

        # VaR = mean + (z_score * std)
        var = mean_return + (z_score * std_return)

        logger.debug(
            f"Parametric VaR ({conf_level*100:.0f}% confidence): {var:.2f}%"
        )

        return var

    def calculate_var_monte_carlo(
        self,
        current_value: float,
        mean_return: float,
        std_return: float,
        time_horizon: int = 1,
        num_simulations: int = 10000,
        confidence_level: Optional[float] = None
    ) -> Tuple[float, List[float]]:
        """
        Calculate Value at Risk using Monte Carlo simulation

        Args:
            current_value: Current portfolio value
            mean_return: Expected daily return (as decimal)
            std_return: Standard deviation of returns
            time_horizon: Time horizon in days
            num_simulations: Number of simulations to run
            confidence_level: Confidence level

        Returns:
            (VaR value, simulated final values)
        """
        conf_level = confidence_level or self.confidence_level

        # Run simulations
        simulated_values = []

        for _ in range(num_simulations):
            # Simulate returns for each day in horizon
            portfolio_value = current_value

            for _ in range(time_horizon):
                # Random return from normal distribution
                daily_return = np.random.normal(mean_return, std_return)
                portfolio_value *= (1 + daily_return)

            simulated_values.append(portfolio_value)

        # Calculate VaR from simulated values
        sorted_values = sorted(simulated_values)
        var_index = int((1 - conf_level) * len(sorted_values))
        var_value = sorted_values[var_index]

        # VaR as loss from current value
        var = current_value - var_value

        logger.debug(
            f"Monte Carlo VaR ({conf_level*100:.0f}% confidence, "
            f"{num_simulations:,} simulations): "
            f"-{var:,.0f} ({(var/current_value)*100:.2f}%)"
        )

        return var, simulated_values

    def calculate_cvar(
        self,
        returns: List[float],
        confidence_level: Optional[float] = None
    ) -> float:
        """
        Calculate Conditional VaR (CVaR) / Expected Shortfall

        Average loss beyond VaR threshold

        Args:
            returns: Historical returns
            confidence_level: Confidence level

        Returns:
            CVaR value
        """
        if not returns or len(returns) < 2:
            return 0.0

        conf_level = confidence_level or self.confidence_level

        # Get VaR threshold
        var = self.calculate_var_historical(returns, conf_level)

        # Average of returns worse than VaR
        tail_returns = [r for r in returns if r <= var]

        if not tail_returns:
            return var

        cvar = np.mean(tail_returns)

        logger.debug(
            f"CVaR ({conf_level*100:.0f}% confidence): {cvar:.2f}%"
        )

        return cvar

    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.03,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sharpe Ratio

        (Mean Return - Risk Free Rate) / Standard Deviation

        Args:
            returns: Period returns (daily)
            risk_free_rate: Annual risk-free rate
            periods_per_year: Number of periods per year (252 for daily)

        Returns:
            Annualized Sharpe Ratio
        """
        if not returns or len(returns) < 2:
            return 0.0

        # Calculate average return and std
        avg_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualize
        annual_return = avg_return * periods_per_year
        annual_std = std_return * np.sqrt(periods_per_year)

        # Sharpe ratio
        sharpe = (annual_return - risk_free_rate) / annual_std

        logger.debug(f"Sharpe Ratio: {sharpe:.2f}")

        return sharpe

    def calculate_sortino_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.03,
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sortino Ratio

        Like Sharpe, but only considers downside volatility

        Args:
            returns: Period returns
            risk_free_rate: Annual risk-free rate
            periods_per_year: Periods per year

        Returns:
            Annualized Sortino Ratio
        """
        if not returns or len(returns) < 2:
            return 0.0

        avg_return = np.mean(returns)

        # Only downside returns
        downside_returns = [r for r in returns if r < 0]

        if not downside_returns:
            return float('inf')  # No downside risk

        downside_std = np.std(downside_returns)

        if downside_std == 0:
            return float('inf')

        # Annualize
        annual_return = avg_return * periods_per_year
        annual_downside_std = downside_std * np.sqrt(periods_per_year)

        # Sortino ratio
        sortino = (annual_return - risk_free_rate) / annual_downside_std

        logger.debug(f"Sortino Ratio: {sortino:.2f}")

        return sortino

    def calculate_maximum_drawdown(
        self,
        equity_curve: List[float]
    ) -> Dict[str, Any]:
        """
        Calculate Maximum Drawdown

        Args:
            equity_curve: Portfolio values over time

        Returns:
            Dict with max_drawdown, max_drawdown_pct, peak, trough
        """
        if not equity_curve or len(equity_curve) < 2:
            return {
                'max_drawdown': 0,
                'max_drawdown_pct': 0,
                'peak_idx': 0,
                'trough_idx': 0,
                'recovery_idx': None,
                'underwater_days': 0
            }

        peak = equity_curve[0]
        peak_idx = 0
        max_dd = 0
        max_dd_pct = 0
        trough_idx = 0

        for i, value in enumerate(equity_curve):
            if value > peak:
                peak = value
                peak_idx = i

            dd = peak - value
            dd_pct = (dd / peak) * 100 if peak > 0 else 0

            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
                trough_idx = i

        # Find recovery point (if any)
        recovery_idx = None
        for i in range(trough_idx, len(equity_curve)):
            if equity_curve[i] >= equity_curve[peak_idx]:
                recovery_idx = i
                break

        # Calculate underwater period
        underwater_days = recovery_idx - peak_idx if recovery_idx else len(equity_curve) - peak_idx

        result = {
            'max_drawdown': round(max_dd, 2),
            'max_drawdown_pct': round(max_dd_pct, 2),
            'peak_idx': peak_idx,
            'trough_idx': trough_idx,
            'recovery_idx': recovery_idx,
            'underwater_days': underwater_days
        }

        logger.debug(
            f"Maximum Drawdown: {max_dd_pct:.2f}% "
            f"(underwater: {underwater_days} periods)"
        )

        return result

    def calculate_calmar_ratio(
        self,
        annual_return: float,
        max_drawdown_pct: float
    ) -> float:
        """
        Calculate Calmar Ratio

        Annual Return / Maximum Drawdown

        Args:
            annual_return: Annualized return (%)
            max_drawdown_pct: Maximum drawdown (%)

        Returns:
            Calmar ratio
        """
        if max_drawdown_pct == 0:
            return float('inf') if annual_return > 0 else 0

        calmar = annual_return / abs(max_drawdown_pct)

        logger.debug(f"Calmar Ratio: {calmar:.2f}")

        return calmar

    def calculate_beta(
        self,
        portfolio_returns: List[float],
        benchmark_returns: List[float]
    ) -> float:
        """
        Calculate portfolio Beta vs benchmark

        Args:
            portfolio_returns: Portfolio returns
            benchmark_returns: Benchmark returns

        Returns:
            Beta coefficient
        """
        if len(portfolio_returns) != len(benchmark_returns):
            logger.error("Portfolio and benchmark returns must have same length")
            return 1.0

        if len(portfolio_returns) < 2:
            return 1.0

        # Calculate covariance and variance
        covariance = np.cov(portfolio_returns, benchmark_returns)[0][1]
        benchmark_variance = np.var(benchmark_returns)

        if benchmark_variance == 0:
            return 1.0

        beta = covariance / benchmark_variance

        logger.debug(f"Beta: {beta:.2f}")

        return beta

    def calculate_alpha(
        self,
        portfolio_return: float,
        benchmark_return: float,
        beta: float,
        risk_free_rate: float = 0.03
    ) -> float:
        """
        Calculate Jensen's Alpha

        Alpha = Portfolio Return - [Risk Free Rate + Beta * (Benchmark Return - Risk Free Rate)]

        Args:
            portfolio_return: Portfolio return
            benchmark_return: Benchmark return
            beta: Portfolio beta
            risk_free_rate: Risk-free rate

        Returns:
            Alpha value
        """
        alpha = portfolio_return - (risk_free_rate + beta * (benchmark_return - risk_free_rate))

        logger.debug(f"Alpha: {alpha:.2f}%")

        return alpha

    def run_monte_carlo_simulation(
        self,
        initial_value: float,
        mean_return: float,
        std_return: float,
        time_horizon: int = 252,
        num_simulations: int = 1000
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for portfolio projection

        Args:
            initial_value: Starting portfolio value
            mean_return: Expected daily return
            std_return: Standard deviation of returns
            time_horizon: Number of days to simulate
            num_simulations: Number of simulation paths

        Returns:
            Simulation results with statistics
        """
        logger.info(
            f"Running Monte Carlo: {num_simulations:,} simulations "
            f"over {time_horizon} days"
        )

        all_paths = []

        for _ in range(num_simulations):
            path = [initial_value]

            for _ in range(time_horizon):
                # Random return
                daily_return = np.random.normal(mean_return, std_return)
                new_value = path[-1] * (1 + daily_return)
                path.append(new_value)

            all_paths.append(path)

        # Convert to numpy array for analysis
        all_paths = np.array(all_paths)

        # Calculate statistics for final values
        final_values = all_paths[:, -1]

        results = {
            'initial_value': initial_value,
            'num_simulations': num_simulations,
            'time_horizon': time_horizon,
            'mean_final_value': np.mean(final_values),
            'median_final_value': np.median(final_values),
            'std_final_value': np.std(final_values),
            'min_final_value': np.min(final_values),
            'max_final_value': np.max(final_values),
            'percentile_5': np.percentile(final_values, 5),
            'percentile_25': np.percentile(final_values, 25),
            'percentile_75': np.percentile(final_values, 75),
            'percentile_95': np.percentile(final_values, 95),
            'probability_profit': (final_values > initial_value).sum() / num_simulations,
            'paths': all_paths.tolist()  # All simulation paths
        }

        logger.info(
            f"Monte Carlo Results: "
            f"Mean={results['mean_final_value']:,.0f}, "
            f"P(profit)={results['probability_profit']:.1%}"
        )

        return results

    def calculate_risk_metrics(
        self,
        returns: List[float],
        equity_curve: List[float],
        benchmark_returns: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive risk metrics

        Args:
            returns: Historical returns
            equity_curve: Portfolio values over time
            benchmark_returns: Benchmark returns (optional)

        Returns:
            Dict with all risk metrics
        """
        logger.info("Calculating comprehensive risk metrics")

        metrics = {}

        # VaR calculations
        metrics['var_95_historical'] = self.calculate_var_historical(returns, 0.95)
        metrics['var_99_historical'] = self.calculate_var_historical(returns, 0.99)
        metrics['var_95_parametric'] = self.calculate_var_parametric(returns, 0.95)

        # CVaR
        metrics['cvar_95'] = self.calculate_cvar(returns, 0.95)

        # Ratios
        metrics['sharpe_ratio'] = self.calculate_sharpe_ratio(returns)
        metrics['sortino_ratio'] = self.calculate_sortino_ratio(returns)

        # Drawdown
        dd_info = self.calculate_maximum_drawdown(equity_curve)
        metrics.update(dd_info)

        # Calmar ratio
        if len(returns) > 0:
            annual_return = np.mean(returns) * 252 * 100  # Annualized %
            metrics['calmar_ratio'] = self.calculate_calmar_ratio(
                annual_return,
                dd_info['max_drawdown_pct']
            )
        else:
            metrics['calmar_ratio'] = 0

        # Beta and Alpha (if benchmark provided)
        if benchmark_returns and len(benchmark_returns) == len(returns):
            beta = self.calculate_beta(returns, benchmark_returns)
            metrics['beta'] = beta

            portfolio_return = np.mean(returns) * 252 * 100
            benchmark_return = np.mean(benchmark_returns) * 252 * 100
            metrics['alpha'] = self.calculate_alpha(
                portfolio_return,
                benchmark_return,
                beta
            )
        else:
            metrics['beta'] = None
            metrics['alpha'] = None

        # Additional statistics
        metrics['volatility'] = np.std(returns) * np.sqrt(252) * 100  # Annualized %
        metrics['downside_volatility'] = (
            np.std([r for r in returns if r < 0]) * np.sqrt(252) * 100
        ) if any(r < 0 for r in returns) else 0

        metrics['skewness'] = stats.skew(returns) if len(returns) > 2 else 0
        metrics['kurtosis'] = stats.kurtosis(returns) if len(returns) > 2 else 0

        logger.info("Risk metrics calculation complete")

        return metrics

    def stress_test(
        self,
        current_value: float,
        scenarios: List[Dict[str, float]]
    ) -> List[Dict[str, Any]]:
        """
        Run stress test scenarios

        Args:
            current_value: Current portfolio value
            scenarios: List of scenarios with 'return' key

        Returns:
            Stress test results
        """
        results = []

        for i, scenario in enumerate(scenarios):
            scenario_return = scenario.get('return', 0)
            new_value = current_value * (1 + scenario_return)
            loss = current_value - new_value

            results.append({
                'scenario': scenario.get('name', f'Scenario {i+1}'),
                'return': scenario_return * 100,
                'new_value': new_value,
                'loss': loss,
                'loss_pct': (loss / current_value) * 100
            })

        return results

    def calculate_portfolio_var(
        self,
        positions: List[Dict[str, Any]],
        correlation_matrix: Optional[np.ndarray] = None
    ) -> float:
        """
        Calculate portfolio-level VaR considering correlations

        Args:
            positions: List of positions with returns
            correlation_matrix: Correlation matrix between assets

        Returns:
            Portfolio VaR
        """
        # Implementation would use portfolio theory
        # Placeholder for now
        return 0.0
