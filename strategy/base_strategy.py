"""
策略基类
统一管理所有类型的策略（技术指标策略、多因子策略等）
专注于策略规则定义和生命周期管理，不负责指标计算
"""

from typing import List, Dict, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime


class BaseStrategy(ABC):
    """
    策略基类，所有策略都应继承此类
    专注于策略规则定义和生命周期管理
    """
    
    def __init__(self, name: str):
        """
        初始化策略
        
        Args:
            name: 策略名称
        """
        self.name = name
        self.is_running = False
        self.created_at = datetime.now()
        self.last_updated = datetime.now()
        
        # 策略参数
        self.params = {}
        
        # 策略规则定义
        self.rules = []
        
        # 交易信号历史
        self.signals = []
        
        # 持仓信息
        self.positions = {}
        
        # 绩效统计
        self.performance = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0
        }
    
    @abstractmethod
    def initialize(self, **kwargs):
        """
        初始化策略
        
        Args:
            **kwargs: 初始化参数
        """
        pass
    
    @abstractmethod
    def define_rules(self, **kwargs):
        """
        定义策略规则
        
        Args:
            **kwargs: 规则参数
        """
        pass
    
    @abstractmethod
    def generate_signals(self, data: Any, **kwargs) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            data: 输入数据（通常是已计算的指标数据）
            **kwargs: 计算参数
            
        Returns:
            交易信号列表
        """
        pass
    
    @abstractmethod
    def update(self, data: Any, **kwargs):
        """
        更新策略状态
        
        Args:
            data: 最新数据（通常是已计算的指标数据）
            **kwargs: 更新参数
        """
        pass
    
    def start(self):
        """
        启动策略
        """
        self.is_running = True
        self.initialize()
        print(f"✅ 策略 {self.name} 启动")
    
    def stop(self):
        """
        停止策略
        """
        self.is_running = False
        print(f"🛑 策略 {self.name} 停止")
    
    def record_signal(self, signal: Dict):
        """
        记录交易信号
        
        Args:
            signal: 交易信号字典
        """
        # 补充信号元数据
        signal['strategy_name'] = self.name
        signal['timestamp'] = datetime.now()
        signal['signal_id'] = f"{self.name}_{datetime.now().timestamp()}"
        
        self.signals.append(signal)
        self.performance['total_trades'] += 1
        
        # 更新绩效统计
        if 'profit' in signal: #profit可正可负可0
            if signal['profit'] > 0:
                self.performance['winning_trades'] += 1
                self.performance['total_profit'] += signal['profit']
            else:
                self.performance['losing_trades'] += 1
                self.performance['total_loss'] += abs(signal['profit'])
    
    def get_performance(self) -> Dict:
        """
        获取策略绩效
        
        Returns:
            绩效统计字典
        """
        return self.performance.copy()
    
    def get_info(self) -> Dict:
        """
        获取策略信息
        
        Returns:
            策略信息字典
        """
        return {
            'name': self.name,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'is_running': self.is_running,
            'params': self.params,
            'signal_count': len(self.signals)
        }
    
    def update_params(self, **kwargs):
        """
        更新策略参数
        
        Args:
            **kwargs: 新的策略参数
        """
        self.params.update(kwargs)
        self.last_updated = datetime.now()
        print(f"🔄 策略 {self.name} 参数更新: {kwargs}")
