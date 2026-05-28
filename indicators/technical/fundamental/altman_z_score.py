"""
Altman Z-score 指标
破产风险预测模型
"""

from typing import Dict, Any, List
import pandas as pd
from indicators.base.base_indicator import TechnicalIndicator


class AltmanZScore(TechnicalIndicator):
    """
    Altman Z-score 指标 - 破产风险预测模型，建议指标名为Z-Score
    
    Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
    A = 营运资本/总资产
    B = 留存收益/总资产  
    C = 息税前利润/总资产
    D = 市值/总负债
    E = 销售收入/总资产
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            name="AltmanZScore",
            data_fields=[
                'current_assets', 'current_liabilities', 'total_assets', 
                'retained_earnings', 'ebit', 'market_cap', 'total_liabilities', 'revenue'
            ],
            output_fields=['z_score'],
            **kwargs
        )
    
    def calculate(self, 
                  data: List[Dict[str, Any]],
                  **kwargs) -> Dict[str, float]:
        """
        计算Altman Z-score
        
        Args:
            data: 基本面数据,一般来说基本面数据是Dict格式的，注意需要加上[]，按列表格式传入
            **kwargs: 计算参数
            
        Returns:
            Z-score值
        """
        # 确保数据有效
        self.validate_data(data)
        data = data[0]
        # 计算各组成部分
        working_capital = data['current_assets'] - data['current_liabilities']
        a = working_capital / data['total_assets']
        b = data['retained_earnings'] / data['total_assets']
        c = data['ebit'] / data['total_assets']
        d = data['market_cap'] / data['total_liabilities']
        e = data['revenue'] / data['total_assets']
        
        # 计算Z-score
        z_score = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e
        
        return {'z_score': z_score}