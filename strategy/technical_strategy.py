"""
技术指标策略基类
基于技术指标的交易策略，继承自BaseStrategy
专注于策略规则定义，不负责指标计算
"""

from typing import List, Dict, Optional, Any
from strategy.base_strategy import BaseStrategy


class TechnicalStrategy(BaseStrategy):
    """
    技术指标策略基类
    用于基于技术指标的交易策略
    只关注规则定义，不负责指标计算
    """
    
    def __init__(self, name: str):
        """
        初始化技术指标策略
        
        Args:
            name: 策略名称
        """
        super().__init__(name)
        
        # 策略所需的技术指标列表
        self.required_indicators: List[str] = []
        
        # 策略规则定义
        self.rules: List[Dict] = []
        
        # 策略参数
        self.strategy_params: Dict = {}
    
    def initialize(self, **kwargs):
        """
        初始化策略
        
        Args:
            **kwargs: 初始化参数
        """
        # 定义策略规则
        self.define_rules(**kwargs)
        print(f"🔄 技术指标策略 '{self.name}' 初始化完成")
    
    def define_rules(self, **kwargs):
        """
        定义策略规则
        
        Args:
            **kwargs: 规则参数
        """
        # 子类应实现此方法，定义具体的策略规则
        pass
    
    def add_required_indicator(self, indicator_name: str):
        """
        添加策略所需的指标
        
        Args:
            indicator_name: 指标名称
        """
        if indicator_name not in self.required_indicators:
            self.required_indicators.append(indicator_name)
    
    def get_required_indicators(self) -> List[str]:
        """
        获取策略所需的所有指标
        
        Returns:
            所需指标名称列表
        """
        return self.required_indicators.copy()
    
    def add_rule(self, rule: Dict):
        """
        添加策略规则
        
        Args:
            rule: 规则字典，包含条件、动作、权重等信息
        """
        self.rules.append(rule)
    
    def generate_signals(self, indicators_data: Dict[str, Any], **kwargs) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            indicators_data: 指标数据字典，key为指标名称，value为指标值
            **kwargs: 计算参数
            
        Returns:
            交易信号列表
        """
        signals = []
        
        try:
            # 验证所需指标是否齐全
            missing_indicators = [
                indicator for indicator in self.required_indicators 
                if indicator not in indicators_data
            ]
            
            if missing_indicators:
                raise ValueError(f"缺少所需指标: {missing_indicators}")
            
            # 应用规则生成信号
            signals = self.apply_rules(indicators_data, **kwargs)
            
            # 记录信号
            for signal in signals:
                self.record_signal(signal)
                
        except Exception as e:
            print(f"❌ 技术指标策略 '{self.name}' 生成信号失败: {e}")
        
        return signals
    
    def apply_rules(self, indicators_data: Dict[str, Any], **kwargs) -> List[Dict]:
        """
        应用策略规则生成信号
        
        Args:
            indicators_data: 指标数据字典
            **kwargs: 计算参数
            
        Returns:
            交易信号列表
        """
        # 子类应实现此方法，应用具体的规则逻辑
        return []
    
    def update(self, indicators_data: Dict[str, Any], **kwargs):
        """
        更新策略状态
        
        Args:
            indicators_data: 指标数据字典
            **kwargs: 更新参数
        """
        # 更新策略参数
        if kwargs:
            self.update_params(**kwargs)
        
        # 记录更新时间
        self.last_updated = self.last_updated
