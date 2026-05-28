"""
风险分析器
计算策略的各项风险指标
"""

from typing import Dict, Optional, List
import pandas as pd
import numpy as np


class RiskAnalyzer:
    """
    风险分析器
    负责计算策略的各项风险指标
    """
    
    def __init__(self, confidence_levels: List[float] = None):
        """
        初始化风险分析器
        
        Args:
            confidence_levels: VaR置信水平列表
        """
        self.confidence_levels = confidence_levels or [0.95, 0.99]
    
    def analyze(self, returns: pd.Series, periods_per_year: int = 252) -> Dict:
        """
        综合风险分析
        
        Args:
            returns: 收益率序列
            periods_per_year: 每年交易日数
            
        Returns:
            风险指标字典
        """
        if returns.empty or len(returns) < 2:
            return {}
        
        result = self._calculate_volatility(returns, periods_per_year)
        result.update(self._calculate_var(returns))
        result.update(self._calculate_cvar(returns))
        result.update(self._calculate_tail_risk(returns))
        result.update(self._calculate_distribution_metrics(returns))
        
        return result
    
    def _calculate_volatility(self, returns: pd.Series, periods_per_year: int) -> Dict:
        """
        计算波动率指标
        
        Args:
            returns: 收益率序列
            periods_per_year: 每年交易日数
            
        Returns:
            波动率指标字典
        """
        total_volatility = returns.std() * np.sqrt(periods_per_year)
        
        downside_returns = returns[returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 0 else 0
        
        return {
            'total_volatility': total_volatility,
            'downside_volatility': downside_volatility,
            'upside_volatility': returns[returns > 0].std() * np.sqrt(periods_per_year) if len(returns[returns > 0]) > 0 else 0,
            'volatility_ratio': downside_volatility / total_volatility if total_volatility > 0 else 0,
        }
    
    def _calculate_var(self, returns: pd.Series) -> Dict:
        """
        计算VaR（Value at Risk）
        
        Args:
            returns: 收益率序列
            
        Returns:
            VaR指标字典
        """
        var_results = {}
        
        for confidence in self.confidence_levels:
            var_value = returns.quantile(1 - confidence)
            var_results[f'var_{int(confidence * 100)}'] = var_value
        
        return var_results
    
    def _calculate_cvar(self, returns: pd.Series) -> Dict:
        """
        计算CVaR（Conditional VaR）/ Expected Shortfall
        
        Args:
            returns: 收益率序列
            
        Returns:
            CVaR指标字典
        """
        cvar_results = {}
        
        for confidence in self.confidence_levels:
            threshold = returns.quantile(1 - confidence)
            cvar_value = returns[returns <= threshold].mean()
            cvar_results[f'cvar_{int(confidence * 100)}'] = cvar_value
        
        return cvar_results
    
    def _calculate_tail_risk(self, returns: pd.Series) -> Dict:
        """
        计算尾部风险指标
        
        Args:
            returns: 收益率序列
            
        Returns:
            尾部风险指标字典
        """
        threshold = returns.quantile(0.05)
        tail_returns = returns[returns <= threshold]
        
        tail_risk = {
            'tail_loss': tail_returns.mean() if len(tail_returns) > 0 else 0,
            'tail_probability': len(tail_returns) / len(returns),
            'max_loss': returns.min(),
            'skewness': returns.skew(),
            'kurtosis': returns.kurtosis(),
        }
        
        return tail_risk
    
    def _calculate_distribution_metrics(self, returns: pd.Series) -> Dict:
        """
        计算分布指标
        
        Args:
            returns: 收益率序列
            
        Returns:
            分布指标字典
        """
        return {
            'mean': returns.mean(),
            'std': returns.std(),
            'skewness': returns.skew(),
            'kurtosis': returns.kurtosis(),
            'jarque_bera_pvalue': self._jarque_bera_test(returns),
            'normality_test': 'NORMAL' if abs(returns.skew()) < 0.5 and returns.kurtosis() < 3 else 'NON_NORMAL',
        }
    
    def _jarque_bera_test(self, returns: pd.Series) -> float:
        """
        Jarque-Bera正态性检验
        
        Args:
            returns: 收益率序列
            
        Returns:
            p值
        """
        n = len(returns)
        if n < 8:
            return 0.0
        
        skew = returns.skew()
        kurt = returns.kurtosis()
        
        jb_statistic = (n / 6) * (skew**2 + (kurt**2) / 4)
        
        from scipy import stats
        p_value = 1 - stats.chi2.cdf(jb_statistic, df=2)
        
        return p_value
    
    def calculate_rolling_var(self, 
                            returns: pd.Series, 
                            window: int = 60,
                            confidence: float = 0.95) -> pd.Series:
        """
        计算滚动VaR
        
        Args:
            returns: 收益率序列
            window: 滚动窗口大小
            confidence: 置信水平
            
        Returns:
            滚动VaR序列
        """
        rolling_var = returns.rolling(window).quantile(1 - confidence)
        return rolling_var
    
    def calculate_rolling_volatility(self, 
                                    returns: pd.Series, 
                                    window: int = 60,
                                    periods_per_year: int = 252) -> pd.Series:
        """
        计算滚动波动率
        
        Args:
            returns: 收益率序列
            window: 滚动窗口大小
            periods_per_year: 每年交易日数
            
        Returns:
            滚动波动率序列
        """
        return returns.rolling(window).std() * np.sqrt(periods_per_year)
    
    def calculate_garch_volatility(self, 
                                  returns: pd.Series,
                                  p: int = 1, 
                                  q: int = 1) -> pd.Series:
        """
        计算GARCH波动率
        
        Args:
            returns: 收益率序列
            p: GARCH阶数
            q: ARCH阶数
            
        Returns:
            条件波动率序列
        """
        try:
            from arch import arch_model
            
            returns_clean = returns.dropna()
            if len(returns_clean) < 50:
                return pd.Series(dtype=float)
            
            model = arch_model(returns_clean * 100, vol='Garch', p=p, q=q)
            result = model.fit(disp='off')
            
            conditional_vol = result.conditional_volatility / 100
            
            vol_series = pd.Series(
                conditional_vol.values,
                index=returns_clean.index
            )
            
            return vol_series
            
        except ImportError:
            print("Warning: arch package not installed, using rolling volatility instead")
            return self.calculate_rolling_volatility(returns)
        except Exception as e:
            print(f"GARCH model failed: {e}")
            return pd.Series(dtype=float)
    
    def calculate_stress_tests(self, 
                              returns: pd.Series,
                              market_stress: Dict[str, float] = None) -> Dict:
        """
        压力测试
        
        Args:
            returns: 收益率序列
            market_stress: 市场压力情景
            
        Returns:
            压力测试结果
        """
        if market_stress is None:
            market_stress = {
                '2008金融危机': -0.50,
                '2020新冠疫情': -0.34,
                '2022加息': -0.25,
            }
        
        stress_results = {}
        
        for scenario, market_loss in market_stress.items():
            beta_estimate = self._estimate_beta(returns)
            strategy_loss = beta_estimate * market_loss
            stress_results[scenario] = strategy_loss
        
        worst_case = returns.quantile(0.01)
        stress_results['worst_case_daily'] = worst_case
        
        return stress_results
    
    def _estimate_beta(self, returns: pd.Series, market_returns: pd.Series = None) -> float:
        """
        估算Beta
        
        Args:
            returns: 策略收益率
            market_returns: 市场收益率，如果为None则假设为1
            
        Returns:
            Beta值
        """
        if market_returns is None:
            market_returns = pd.Series(np.ones(len(returns)), index=returns.index)
        
        aligned = returns.align(market_returns, join='inner')
        
        if len(aligned[0]) < 2:
            return 1.0
        
        covariance = np.cov(aligned[0], aligned[1])[0, 1]
        market_variance = np.var(aligned[1])
        
        if market_variance == 0:
            return 1.0
        
        return covariance / market_variance
    
    def get_risk_report(self, returns: pd.Series, periods_per_year: int = 252) -> str:
        """
        生成风险报告
        
        Args:
            returns: 收益率序列
            periods_per_year: 每年交易日数
            
        Returns:
            风险报告字符串
        """
        metrics = self.analyze(returns, periods_per_year)
        
        report = []
        report.append("=" * 50)
        report.append("风险分析报告")
        report.append("=" * 50)
        report.append("")
        
        report.append("波动率指标:")
        report.append(f"  年化波动率: {metrics.get('total_volatility', 0):.2%}")
        report.append(f"  下行波动率: {metrics.get('downside_volatility', 0):.2%}")
        report.append("")
        
        report.append("VaR指标:")
        report.append(f"  VaR (95%): {metrics.get('var_95', 0):.2%}")
        report.append(f"  VaR (99%): {metrics.get('var_99', 0):.2%}")
        report.append("")
        
        report.append("CVaR指标:")
        report.append(f"  CVaR (95%): {metrics.get('cvar_95', 0):.2%}")
        report.append(f"  CVaR (99%): {metrics.get('cvar_99', 0):.2%}")
        report.append("")
        
        report.append("尾部风险:")
        report.append(f"  最大单日亏损: {metrics.get('max_loss', 0):.2%}")
        report.append(f"  偏度: {metrics.get('skewness', 0):.4f}")
        report.append(f"  峰度: {metrics.get('kurtosis', 0):.4f}")
        report.append("")
        
        report.append("=" * 50)
        
        return "\n".join(report)
