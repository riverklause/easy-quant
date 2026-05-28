"""
回测结果存储
存储和管理回测结果
"""

from typing import Dict, Optional, Any, List
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
import json
import os


@dataclass
class BacktestResult:
    """
    回测结果
    存储和管理回测的完整结果
    """
    
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    
    created_at: datetime = field(default_factory=datetime.now)
    
    equity_curve: pd.DataFrame = None
    trades: pd.DataFrame = None
    
    performance_metrics: Dict = field(default_factory=dict)
    risk_metrics: Dict = field(default_factory=dict)
    trade_metrics: Dict = field(default_factory=dict)
    
    benchmark_returns: pd.Series = None
    
    config: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.equity_curve is None:
            self.equity_curve = pd.DataFrame()
        if self.trades is None:
            self.trades = pd.DataFrame()
    
    def get_performance_summary(self) -> Dict:
        """
        获取绩效摘要
        
        Returns:
            绩效摘要字典
        """
        summary = {
            'strategy_name': self.strategy_name,
            'period': f"{self.start_date} - {self.end_date}",
            'initial_capital': self.initial_capital,
        }
        
        if not self.equity_curve.empty:
            final_equity = self.equity_curve['equity'].iloc[-1]
            summary['final_equity'] = final_equity
            summary['total_return'] = (final_equity - self.initial_capital) / self.initial_capital
        
        if self.performance_metrics:
            summary.update({
                'annual_return': self.performance_metrics.get('annual_return', 0),
                'annual_volatility': self.performance_metrics.get('annual_volatility', 0),
                'sharpe_ratio': self.performance_metrics.get('sharpe_ratio', 0),
                'max_drawdown': self.performance_metrics.get('max_drawdown', 0),
            })
        
        if self.trade_metrics:
            summary.update({
                'total_trades': self.trade_metrics.get('total_trades', 0),
                'win_rate': self.trade_metrics.get('win_rate', 0),
                'profit_factor': self.trade_metrics.get('profit_factor', 0),
            })
        
        return summary
    
    def get_risk_summary(self) -> Dict:
        """
        获取风险摘要
        
        Returns:
            风险摘要字典
        """
        if not self.risk_metrics:
            return {}
        
        return {
            'var_95': self.risk_metrics.get('var_95', 0),
            'var_99': self.risk_metrics.get('var_99', 0),
            'cvar_95': self.risk_metrics.get('cvar_95', 0),
            'total_volatility': self.risk_metrics.get('total_volatility', 0),
            'downside_volatility': self.risk_metrics.get('downside_volatility', 0),
            'max_loss': self.risk_metrics.get('max_loss', 0),
        }
    
    def get_equity_curve(self) -> pd.DataFrame:
        """
        获取权益曲线
        
        Returns:
            权益曲线DataFrame
        """
        return self.equity_curve
    
    def get_trades(self) -> pd.DataFrame:
        """
        获取交易记录
        
        Returns:
            交易记录DataFrame
        """
        return self.trades
    
    def get_returns(self) -> pd.Series:
        """
        获取收益率序列
        
        Returns:
            收益率Series
        """
        if self.equity_curve.empty or 'daily_return' not in self.equity_curve.columns:
            return pd.Series(dtype=float)
        
        return self.equity_curve['daily_return'].dropna()
    
    def get_benchmark_returns(self) -> pd.Series:
        """
        获取基准收益率
        
        Returns:
            基准收益率Series
        """
        return self.benchmark_returns
    
    def save_to_file(self, filepath: str):
        """
        保存回测结果到文件
        
        Args:
            filepath: 文件路径
        """
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        result_dict = {
            'strategy_name': self.strategy_name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'created_at': self.created_at.isoformat(),
            'performance_metrics': self._convert_to_serializable(self.performance_metrics),
            'risk_metrics': self._convert_to_serializable(self.risk_metrics),
            'trade_metrics': self._convert_to_serializable(self.trade_metrics),
            'config': self._convert_to_serializable(self.config),
        }
        
        if not self.equity_curve.empty:
            self.equity_curve.to_csv(filepath.replace('.json', '_equity.csv'))
            result_dict['equity_curve_file'] = filepath.replace('.json', '_equity.csv')
        
        if not self.trades.empty:
            self.trades.to_csv(filepath.replace('.json', '_trades.csv'))
            result_dict['trades_file'] = filepath.replace('.json', '_trades.csv')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        
        print(f"回测结果已保存到: {filepath}")
    
    def _convert_to_serializable(self, obj: Any) -> Any:
        """
        转换为可序列化的对象
        
        Args:
            obj: 任意对象
            
        Returns:
            可序列化的对象
        """
        if isinstance(obj, pd.Series):
            return obj.to_dict()
        elif isinstance(obj, pd.DataFrame):
            return {'columns': obj.columns.tolist(), 'index': obj.index.tolist()}
        elif isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'BacktestResult':
        """
        从文件加载回测结果
        
        Args:
            filepath: 文件路径
            
        Returns:
            BacktestResult实例
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            result_dict = json.load(f)
        
        equity_curve = pd.DataFrame()
        trades = pd.DataFrame()
        
        if 'equity_curve_file' in result_dict:
            equity_curve_file = result_dict['equity_curve_file']
            if os.path.exists(equity_curve_file):
                equity_curve = pd.read_csv(equity_curve_file, index_col=0, parse_dates=True)
        
        if 'trades_file' in result_dict:
            trades_file = result_dict['trades_file']
            if os.path.exists(trades_file):
                trades = pd.read_csv(trades_file, index_col=0, parse_dates=True)
        
        return cls(
            strategy_name=result_dict['strategy_name'],
            start_date=result_dict['start_date'],
            end_date=result_dict['end_date'],
            initial_capital=result_dict['initial_capital'],
            created_at=datetime.fromisoformat(result_dict['created_at']),
            equity_curve=equity_curve,
            trades=trades,
            performance_metrics=result_dict.get('performance_metrics', {}),
            risk_metrics=result_dict.get('risk_metrics', {}),
            trade_metrics=result_dict.get('trade_metrics', {}),
            config=result_dict.get('config', {}),
        )
    
    def print_summary(self):
        """
        打印回测结果摘要
        """
        print("=" * 60)
        print(f"回测结果摘要 - {self.strategy_name}")
        print("=" * 60)
        print(f"回测期间: {self.start_date} ~ {self.end_date}")
        print(f"初始资金: {self.initial_capital:,.2f}")
        
        if not self.equity_curve.empty:
            final_equity = self.equity_curve['equity'].iloc[-1]
            total_return = (final_equity - self.initial_capital) / self.initial_capital
            print(f"最终权益: {final_equity:,.2f}")
            print(f"总收益率: {total_return:.2%}")
        
        print("")
        
        if self.performance_metrics:
            print("绩效指标:")
            print(f"  年化收益率: {self.performance_metrics.get('annual_return', 0):.2%}")
            print(f"  年化波动率: {self.performance_metrics.get('annual_volatility', 0):.2%}")
            print(f"  夏普比率: {self.performance_metrics.get('sharpe_ratio', 0):.2f}")
            print(f"  最大回撤: {self.performance_metrics.get('max_drawdown', 0):.2%}")
            print(f"  索提诺比率: {self.performance_metrics.get('sortino_ratio', 0):.2f}")
            print(f"  卡玛比率: {self.performance_metrics.get('calmar_ratio', 0):.2f}")
        
        print("")
        
        if self.risk_metrics:
            print("风险指标:")
            print(f"  VaR (95%): {self.risk_metrics.get('var_95', 0):.2%}")
            print(f"  VaR (99%): {self.risk_metrics.get('var_99', 0):.2%}")
            print(f"  CVaR (95%): {self.risk_metrics.get('cvar_95', 0):.2%}")
        
        print("")
        
        if self.trade_metrics:
            print("交易统计:")
            print(f"  总交易次数: {self.trade_metrics.get('total_trades', 0)}")
            print(f"  盈利交易: {self.trade_metrics.get('winning_trades', 0)}")
            print(f"  亏损交易: {self.trade_metrics.get('losing_trades', 0)}")
            print(f"  胜率: {self.trade_metrics.get('win_rate', 0):.2%}")
            print(f"  盈利因子: {self.trade_metrics.get('profit_factor', 0):.2f}")
        
        print("=" * 60)
