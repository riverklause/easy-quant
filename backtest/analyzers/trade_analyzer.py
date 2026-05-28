"""
交易分析器
分析交易记录，生成交易统计信息
"""

from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np


class TradeAnalyzer:
    """
    交易分析器
    负责分析交易记录，计算交易统计指标
    """
    
    def __init__(self):
        """初始化交易分析器"""
        pass
    
    def analyze(self, trades: pd.DataFrame) -> Dict:
        """
        综合交易分析
        
        Args:
            trades: 交易记录DataFrame
            
        Returns:
            交易统计字典
        """
        if trades.empty:
            return self._get_empty_stats()
        
        result = {}
        result.update(self._calculate_trade_count(trades))
        result.update(self._calculate_profit_metrics(trades))
        result.update(self._calculate_trade_duration(trades))
        result.update(self._calculate_trade_frequency(trades))
        
        return result
    
    def _get_empty_stats(self) -> Dict:
        """获取空统计"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'net_profit': 0.0,
            'average_profit': 0.0,
            'average_loss': 0.0,
            'profit_factor': 0.0,
            'average_trade_return': 0.0,
            'average_holding_days': 0.0,
        }
    
    def _calculate_trade_count(self, trades: pd.DataFrame) -> Dict:
        """
        计算交易次数
        
        Args:
            trades: 交易记录
            
        Returns:
            交易次数统计
        """
        if 'action' not in trades.columns:
            return {'total_trades': len(trades)}
        
        buys = trades[trades['action'] == 'BUY']
        sells = trades[trades['action'] == 'SELL']
        
        return {
            'total_trades': len(buys),
            'total_buys': len(buys),
            'total_sells': len(sells),
        }
    
    def _calculate_profit_metrics(self, trades: pd.DataFrame) -> Dict:
        """
        计算盈利指标
        
        Args:
            trades: 交易记录
            
        Returns:
            盈利统计
        """
        if 'profit' not in trades.columns:
            return self._get_empty_stats()
        
        profits = trades['profit'].dropna()
        
        if len(profits) == 0:
            return self._get_empty_stats()
        
        winning_trades = profits[profits > 0]
        losing_trades = profits[profits < 0]
        
        total_profit = winning_trades.sum() if len(winning_trades) > 0 else 0
        total_loss = abs(losing_trades.sum()) if len(losing_trades) > 0 else 0
        
        win_rate = len(winning_trades) / len(profits) if len(profits) > 0 else 0
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0
        
        return {
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'net_profit': total_profit - total_loss,
            'average_profit': winning_trades.mean() if len(winning_trades) > 0 else 0,
            'average_loss': losing_trades.mean() if len(losing_trades) > 0 else 0,
            'profit_factor': profit_factor,
            'average_trade_return': profits.mean(),
            'max_profit': profits.max() if len(profits) > 0 else 0,
            'max_loss': profits.min() if len(profits) > 0 else 0,
            'largest_win': winning_trades.max() if len(winning_trades) > 0 else 0,
            'largest_loss': losing_trades.min() if len(losing_trades) > 0 else 0,
        }
    
    def _calculate_trade_duration(self, trades: pd.DataFrame) -> Dict:
        """
        计算交易持仓时间
        
        Args:
            trades: 交易记录
            
        Returns:
            持仓时间统计
        """
        if 'entry_date' not in trades.columns or 'exit_date' not in trades.columns:
            return {'average_holding_days': 0}
        
        try:
            trades_copy = trades.copy()
            trades_copy['holding_days'] = (
                trades_copy['exit_date'] - trades_copy['entry_date']
            ).dt.days
            
            return {
                'average_holding_days': trades_copy['holding_days'].mean(),
                'median_holding_days': trades_copy['holding_days'].median(),
                'max_holding_days': trades_copy['holding_days'].max(),
                'min_holding_days': trades_copy['holding_days'].min(),
            }
        except:
            return {'average_holding_days': 0}
    
    def _calculate_trade_frequency(self, trades: pd.DataFrame) -> Dict:
        """
        计算交易频率
        
        Args:
            trades: 交易记录
            
        Returns:
            交易频率统计
        """
        if 'date' not in trades.index or len(trades) < 2:
            return {'trades_per_month': 0}
        
        try:
            date_range = (trades.index[-1] - trades.index[0]).days
            months = max(date_range / 30, 1)
            
            trades_per_month = len(trades) / months
            
            return {
                'total_trading_days': date_range,
                'trades_per_month': trades_per_month,
                'trades_per_year': trades_per_month * 12,
            }
        except:
            return {'trades_per_month': 0}
    
    def analyze_by_symbol(self, trades: pd.DataFrame) -> Dict[str, Dict]:
        """
        按股票分析交易
        
        Args:
            trades: 交易记录
            
        Returns:
            按股票分组的交易统计
        """
        if 'symbol' not in trades.columns or trades.empty:
            return {}
        
        result = {}
        
        for symbol in trades['symbol'].unique():
            symbol_trades = trades[trades['symbol'] == symbol]
            result[symbol] = self.analyze(symbol_trades)
        
        return result
    
    def get_trade_summary(self, trades: pd.DataFrame) -> pd.DataFrame:
        """
        获取交易汇总表
        
        Args:
            trades: 交易记录
            
        Returns:
            交易汇总DataFrame
        """
        if 'symbol' not in trades.columns:
            return pd.DataFrame()
        
        summary = []
        
        for symbol in trades['symbol'].unique():
            symbol_trades = trades[trades['symbol'] == symbol]
            
            buys = symbol_trades[symbol_trades['action'] == 'BUY']
            sells = symbol_trades[symbol_trades['action'] == 'SELL']
            
            total_bought = buys['quantity'].sum() if 'quantity' in buys.columns else 0
            total_sold = sells['quantity'].sum() if 'quantity' in sells.columns else 0
            
            avg_buy_price = buys['price'].mean() if 'price' in buys.columns and len(buys) > 0 else 0
            avg_sell_price = sells['price'].mean() if 'price' in sells.columns and len(sells) > 0 else 0
            
            profit = 0
            if 'profit' in symbol_trades.columns:
                profit = symbol_trades['profit'].sum()
            
            summary.append({
                'symbol': symbol,
                'total_trades': len(symbol_trades),
                'total_bought': total_bought,
                'total_sold': total_sold,
                'avg_buy_price': avg_buy_price,
                'avg_sell_price': avg_sell_price,
                'net_profit': profit,
            })
        
        return pd.DataFrame(summary)
    
    def get_monthly_trades(self, trades: pd.DataFrame) -> pd.DataFrame:
        """
        获取月度交易统计
        
        Args:
            trades: 交易记录
            
        Returns:
            月度交易统计
        """
        if 'date' not in trades.index:
            return pd.DataFrame()
        
        try:
            trades_copy = trades.copy()
            trades_copy['year_month'] = trades_copy.index.to_period('M')
            
            monthly = trades_copy.groupby('year_month').agg({
                'symbol': 'count',
                'profit': 'sum' if 'profit' in trades_copy.columns else 'count',
            })
            
            monthly.columns = ['trade_count', 'net_profit']
            
            return monthly
            
        except:
            return pd.DataFrame()
    
    def calculate_consecutive_wins_losses(self, trades: pd.DataFrame) -> Dict:
        """
        计算连续盈亏
        
        Args:
            trades: 交易记录
            
        Returns:
            连续盈亏统计
        """
        if 'profit' not in trades.columns or trades.empty:
            return {
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0,
            }
        
        profits = trades['profit'].values
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for profit in profits:
            if profit > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif profit < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
            else:
                current_wins = 0
                current_losses = 0
        
        return {
            'max_consecutive_wins': max_wins,
            'max_consecutive_losses': max_losses,
        }
    
    def get_trade_report(self, trades: pd.DataFrame) -> str:
        """
        生成交易报告
        
        Args:
            trades: 交易记录
            
        Returns:
            交易报告字符串
        """
        metrics = self.analyze(trades)
        
        report = []
        report.append("=" * 50)
        report.append("交易分析报告")
        report.append("=" * 50)
        report.append("")
        
        report.append("交易次数:")
        report.append(f"  总交易次数: {metrics.get('total_trades', 0)}")
        report.append(f"  盈利交易: {metrics.get('winning_trades', 0)}")
        report.append(f"  亏损交易: {metrics.get('losing_trades', 0)}")
        report.append(f"  胜率: {metrics.get('win_rate', 0):.2%}")
        report.append("")
        
        report.append("盈亏统计:")
        report.append(f"  总盈利: {metrics.get('total_profit', 0):.2f}")
        report.append(f"  总亏损: {metrics.get('total_loss', 0):.2f}")
        report.append(f"  净利润: {metrics.get('net_profit', 0):.2f}")
        report.append(f"  盈利因子: {metrics.get('profit_factor', 0):.2f}")
        report.append("")
        
        report.append("平均统计:")
        report.append(f"  平均盈利: {metrics.get('average_profit', 0):.2f}")
        report.append(f"  平均亏损: {metrics.get('average_loss', 0):.2f}")
        report.append(f"  平均交易收益: {metrics.get('average_trade_return', 0):.2%}")
        report.append(f"  平均持仓天数: {metrics.get('average_holding_days', 0):.1f}")
        report.append("")
        
        report.append("=" * 50)
        
        return "\n".join(report)
