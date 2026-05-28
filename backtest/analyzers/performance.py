"""
绩效分析器
计算策略的各项绩效指标
"""

from typing import Dict, Optional, Union
import pandas as pd
import numpy as np


class PerformanceAnalyzer:
    """
    绩效分析器
    负责计算策略的各项绩效指标
    """
    
    def __init__(self, risk_free_rate: float = 0.03):
        """
        初始化绩效分析器
        
        Args:
            risk_free_rate: 无风险利率（年化）
        """
        self.risk_free_rate = risk_free_rate
    
    def analyze(self, 
                returns: pd.Series, 
                benchmark_returns: Optional[pd.Series] = None,
                periods_per_year: int = 252) -> Dict:
        """
        综合绩效分析
        
        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列（可选）
            periods_per_year: 每年交易日数
            
        Returns:
            绩效指标字典
        """
        if returns.empty or len(returns) < 2:
            return {}
        
        result = self._calculate_return_metrics(returns, periods_per_year)
        result.update(self._calculate_risk_metrics(returns, periods_per_year))
        result.update(self._calculate_risk_adjusted_metrics(returns, periods_per_year))
        
        if benchmark_returns is not None and not benchmark_returns.empty:
            result.update(self._calculate_benchmark_metrics(
                returns, benchmark_returns, periods_per_year
            ))
        
        return result
    
    def _calculate_return_metrics(self, 
                                  returns: pd.Series, 
                                  periods_per_year: int) -> Dict:
        """
        计算收益指标
        
        Args:
            returns: 收益率序列
            periods_per_year: 每年交易日数
            
        Returns:
            收益指标字典
        """
        cumulative_returns = (1 + returns).cumprod()
        
        total_return = cumulative_returns.iloc[-1] - 1
        annual_return = (1 + total_return) ** (periods_per_year / len(returns)) - 1
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'cumulative_returns': cumulative_returns.to_dict(),
        }
    
    def _calculate_risk_metrics(self, 
                                 returns: pd.Series, 
                                 periods_per_year: int) -> Dict:
        """
        计算风险指标
        
        Args:
            returns: 收益率序列
            periods_per_year: 每年交易日数
            
        Returns:
            风险指标字典
        """
        annual_volatility = returns.std() * np.sqrt(periods_per_year)
        
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 0 else 0
        
        cumulative_returns = (1 + returns).cumprod()
        peak = cumulative_returns.expanding(min_periods=1).max()
        drawdown = (cumulative_returns / peak) - 1
        max_drawdown = drawdown.min()
        
        drawdown_duration = self._calculate_max_drawdown_duration(drawdown)
        
        return {
            'annual_volatility': annual_volatility,
            'downside_volatility': downside_std,
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': drawdown_duration,
            'drawdown_series': drawdown.to_dict(),
        }
    
    def _calculate_risk_adjusted_metrics(self, 
                                         returns: pd.Series, 
                                         periods_per_year: int) -> Dict:
        """
        计算风险调整收益指标
        
        Args:
            returns: 收益率序列
            periods_per_year: 每年交易日数
            
        Returns:
            风险调整收益指标字典
        """
        mean_return = returns.mean()
        std_return = returns.std()
        
        sharpe_ratio = 0
        if std_return > 0:
            sharpe_ratio = (mean_return * periods_per_year - self.risk_free_rate) / (std_return * np.sqrt(periods_per_year))
        
        downside_returns = returns[returns < 0]
        sortino_ratio = 0
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            sortino_ratio = (mean_return * periods_per_year - self.risk_free_rate) / (downside_returns.std() * np.sqrt(periods_per_year))
        
        cumulative_returns = (1 + returns).cumprod()
        peak = cumulative_returns.expanding(min_periods=1).max()
        drawdown = (cumulative_returns / peak) - 1
        max_drawdown = drawdown.min()
        
        calmar_ratio = 0
        if max_drawdown < 0:
            annual_return = ((1 + returns.mean()) ** periods_per_year) - 1
            calmar_ratio = annual_return / abs(max_drawdown)
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
        }
    
    def _calculate_benchmark_metrics(self, 
                                     returns: pd.Series, 
                                     benchmark_returns: pd.Series,
                                     periods_per_year: int) -> Dict:
        """
        计算相对基准的指标
        
        Args:
            returns: 策略收益率序列
            benchmark_returns: 基准收益率序列
            periods_per_year: 每年交易日数
            
        Returns:
            相对基准指标字典
        """
        aligned_returns = returns.align(benchmark_returns, join='inner')
        strategy_returns = aligned_returns[0]
        bench_returns = aligned_returns[1]
        
        if len(strategy_returns) < 2:
            return {}
        
        excess_returns = strategy_returns - bench_returns
        
        alpha = 0
        beta = 0
        if bench_returns.std() > 0:
            covariance = np.cov(strategy_returns, bench_returns)[0, 1]
            bench_variance = bench_returns.var()
            beta = covariance / bench_variance if bench_variance > 0 else 0
            
            alpha = (strategy_returns.mean() - beta * bench_returns.mean()) * periods_per_year
        
        information_ratio = 0
        if excess_returns.std() > 0:
            information_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(periods_per_year)
        
        tracking_error = excess_returns.std() * np.sqrt(periods_per_year)
        
        correlation = strategy_returns.corr(bench_returns)
        
        return {
            'alpha': alpha,
            'beta': beta,
            'information_ratio': information_ratio,
            'tracking_error': tracking_error,
            'correlation': correlation,
            'excess_returns': excess_returns.to_dict(),
        }
    
    def _calculate_max_drawdown_duration(self, drawdown: pd.Series) -> int:
        """
        计算最大回撤持续时间
        
        Args:
            drawdown: 回撤序列
            
        Returns:
            最大回撤持续天数
        """
        if drawdown.empty:
            return 0
        
        max_duration = 0
        current_duration = 0
        
        for value in drawdown:
            if value < 0:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
        
        return max_duration
    
    def get_monthly_returns(self, returns: pd.Series) -> pd.DataFrame:
        """
        获取月度收益率统计
        
        Args:
            returns: 日收益率序列
            
        Returns:
            月度收益率DataFrame
        """
        if returns.empty:
            return pd.DataFrame()
        
        returns_df = returns.to_frame('daily_return')
        returns_df['year_month'] = returns_df.index.to_period('M')
        
        monthly_returns = returns_df.groupby('year_month')['daily_return'].apply(
            lambda x: (1 + x).prod() - 1
        )
        
        monthly_table = pd.DataFrame({
            'monthly_return': monthly_returns
        })
        
        return monthly_table
    
    def get_rolling_metrics(self, 
                          returns: pd.Series, 
                          window: int = 60,
                          periods_per_year: int = 252) -> pd.DataFrame:
        """
        计算滚动绩效指标
        
        Args:
            returns: 收益率序列
            window: 滚动窗口大小
            periods_per_year: 每年交易日数
            
        Returns:
            滚动指标DataFrame
        """
        if len(returns) < window:
            return pd.DataFrame()
        
        rolling_df = pd.DataFrame(index=returns.index)
        
        rolling_df['rolling_return'] = returns.rolling(window).mean() * periods_per_year
        rolling_df['rolling_volatility'] = returns.rolling(window).std() * np.sqrt(periods_per_year)
        
        rolling_cumulative = (1 + returns).cumprod()
        rolling_df['rolling_sharpe'] = (
            (rolling_df['rolling_return'] - self.risk_free_rate) / 
            rolling_df['rolling_volatility']
        )
        
        rolling_peak = rolling_cumulative.rolling(window, min_periods=1).max()
        rolling_drawdown = (rolling_cumulative / rolling_peak) - 1
        rolling_df['rolling_max_drawdown'] = rolling_drawdown.rolling(window).min()
        
        return rolling_df.dropna()
