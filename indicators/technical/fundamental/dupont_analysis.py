"""
杜邦分析指标
分解ROE的驱动因素
"""

from typing import Dict, Any, List
import pandas as pd
from indicators.base.base_indicator import TechnicalIndicator


class DupontAnalysis(TechnicalIndicator):
    """
    杜邦分析指标 - 分解ROE的驱动因素，建议指标名为ROE-Dupont
    
    ROE = 净利润率 × 资产周转率 × 权益乘数
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="DupontAnalysis",
            data_fields=[
                'net_income', 'revenue', 'total_assets', 'shareholders_equity'
            ],
            output_fields=['roe', 'net_profit_margin', 'asset_turnover', 'equity_multiplier'],
            **kwargs
        )
    
    def calculate(self, 
                  data: List[Dict[str, Any]],
                  **kwargs) -> Dict[str, float]:
        """
        计算杜邦分析
        
        Args:
            data: 基本面数据,一般来说基本面数据是Dict格式的，注意需要加上[]，按列表格式传入
            **kwargs: 计算参数
            
        Returns:
            杜邦分析结果
        """
        # 确保数据有效
        self.validate_data(data)
        
        # 计算各组成部分
        data = data[0]
        net_profit_margin = data['net_income'] / data['revenue']
        asset_turnover = data['revenue'] / data['total_assets']
        equity_multiplier = data['total_assets'] / data['shareholders_equity']
        roe = data['net_income'] / data['shareholders_equity']
        
        return {
            'roe': roe,
            'net_profit_margin': net_profit_margin,
            'asset_turnover': asset_turnover,
            'equity_multiplier': equity_multiplier
        }