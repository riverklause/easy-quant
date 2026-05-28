"""
策略执行器
负责协调指标计算和策略规则应用
将指标计算职责从策略类中分离出来
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from indicators.base.calculator import IndicatorCalculator
from indicators.base.registry import IndicatorRegistry
from strategy.base_strategy import BaseStrategy
from strategy.technical_strategy import TechnicalStrategy
from strategy.multi_factor.multi_factor_strategy import MultiFactorStrategy


class StrategyExecutor:
    """
    策略执行器
    负责：
    1. 管理指标计算器
    2. 为策略提供所需的指标数据
    3. 协调策略规则应用
    4. 执行策略并生成信号
    """
    
    def __init__(self):
        """
        初始化策略执行器
        """
        # 指标计算器
        self.calculator = IndicatorCalculator()
        
        # 指标注册器
        self.registry = IndicatorRegistry()
        
        # 加载所有指标
        self.registry.load_indicators_from_package('indicators.technical')
        
        # 策略缓存
        self.strategies: Dict[str, BaseStrategy] = {}
        
        # 指标缓存
        self.indicators_cache: Dict[str, Any] = {}
        
        # 执行统计
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_strategies': 0,
            'total_indicators_calculated': 0
        }
    
    def register_strategy(self, strategy: BaseStrategy) -> str:
        """
        注册策略
        
        Args:
            strategy: 策略实例
            
        Returns:
            策略ID
        """
        strategy_id = strategy.name
        
        if strategy_id in self.strategies:
            raise ValueError(f"策略ID '{strategy_id}' 已存在")
        
        self.strategies[strategy_id] = strategy
        self.execution_stats['total_strategies'] += 1
        
        print(f"✅ 策略 '{strategy_id}' 注册到执行器")
        return strategy_id
    
    def unregister_strategy(self, strategy_id: str):
        """
        注销策略
        
        Args:
            strategy_id: 策略ID
        """
        if strategy_id in self.strategies:
            del self.strategies[strategy_id]
            self.execution_stats['total_strategies'] -= 1
            print(f"✅ 策略 '{strategy_id}' 从执行器注销")
    
    def get_required_indicators(self, strategy_id: str) -> List[str]:
        """
        获取策略所需的所有指标
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            所需指标名称列表
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"策略 '{strategy_id}' 不存在")
        
        strategy = self.strategies[strategy_id]
        
        if isinstance(strategy, TechnicalStrategy):
            return strategy.get_required_indicators()
        elif isinstance(strategy, MultiFactorStrategy):
            return strategy.factor_names
        else:
            # 对于其他类型的策略，返回空列表
            return []
    
    def calculate_indicators(self, 
                           raw_data: Any,
                           indicator_names: List[str],
                           use_cache: bool = True,
                           **kwargs) -> Dict[str, Any]:
        """
        批量计算指标
        
        Args:
            raw_data: 原始数据
            indicator_names: 指标名称列表
            use_cache: 是否使用缓存
            **kwargs: 计算参数
            
        Returns:
            指标数据字典，key为指标名称，value为指标值
        """
        indicators_data = {}
        
        for indicator_name in indicator_names:
            try:
                # 检查缓存
                cache_key = f"{indicator_name}_{hash(str(raw_data))}"
                
                if use_cache and cache_key in self.indicators_cache:
                    indicators_data[indicator_name] = self.indicators_cache[cache_key]
                    self.execution_stats['total_indicators_calculated'] += 1
                    continue
                
                # 计算指标
                indicator_result = self.calculator.calculate(
                    indicator_name, raw_data, use_cache=use_cache, **kwargs
                )
                
                indicators_data[indicator_name] = indicator_result
                
                # 更新缓存
                if use_cache:
                    self.indicators_cache[cache_key] = indicator_result
                
                self.execution_stats['total_indicators_calculated'] += 1
                
            except Exception as e:
                print(f"❌ 计算指标 '{indicator_name}' 失败: {e}")
                # 可以选择跳过失败的指标或抛出异常
                continue
        
        return indicators_data
    
    def execute_strategy(self, 
                        strategy_id: str,
                        raw_data: Any,
                        calculate_indicators: bool = True,
                        **kwargs) -> List[Dict]:
        """
        执行策略
        
        Args:
            strategy_id: 策略ID
            raw_data: 原始数据
            calculate_indicators: 是否计算指标（如果为False，则raw_data应为指标数据）
            **kwargs: 执行参数
            
        Returns:
            交易信号列表
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"策略 '{strategy_id}' 不存在")
        
        strategy = self.strategies[strategy_id]
        self.execution_stats['total_executions'] += 1
        
        try:
            # 获取策略所需指标
            required_indicators = self.get_required_indicators(strategy_id)
            
            if calculate_indicators:
                # 计算所需指标
                indicators_data = self.calculate_indicators(
                    raw_data, required_indicators, **kwargs
                )
            else:
                # raw_data已经是指标数据
                indicators_data = raw_data
            
            # 执行策略（应用规则）
            signals = strategy.generate_signals(indicators_data, **kwargs)
            
            self.execution_stats['successful_executions'] += 1
            return signals
            
        except Exception as e:
            self.execution_stats['failed_executions'] += 1
            print(f"❌ 执行策略 '{strategy_id}' 失败: {e}")
            return []
    
    def execute_all_strategies(self,
                              raw_data: Any,
                              calculate_indicators: bool = True,
                              **kwargs) -> Dict[str, List[Dict]]:
        """
        执行所有注册的策略
        
        Args:
            raw_data: 原始数据
            calculate_indicators: 是否计算指标
            **kwargs: 执行参数
            
        Returns:
            策略信号字典，key为策略ID，value为信号列表
        """
        all_signals = {}
        
        for strategy_id in self.strategies:
            signals = self.execute_strategy(
                strategy_id, raw_data, calculate_indicators, **kwargs
            )
            all_signals[strategy_id] = signals
        
        return all_signals
    
    def batch_calculate_for_strategies(self,
                                      raw_data: Any,
                                      strategy_ids: List[str] = None,
                                      **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        为多个策略批量计算指标
        
        Args:
            raw_data: 原始数据
            strategy_ids: 策略ID列表，None表示所有策略
            **kwargs: 计算参数
            
        Returns:
            策略指标数据字典，key为策略ID，value为指标数据字典
        """
        if strategy_ids is None:
            strategy_ids = list(self.strategies.keys())
        
        strategy_indicators = {}
        
        for strategy_id in strategy_ids:
            if strategy_id not in self.strategies:
                print(f"⚠️ 策略 '{strategy_id}' 不存在，跳过")
                continue
            
            # 获取策略所需指标
            required_indicators = self.get_required_indicators(strategy_id)
            
            if not required_indicators:
                print(f"⚠️ 策略 '{strategy_id}' 不需要指标，跳过")
                continue
            
            # 计算指标
            indicators_data = self.calculate_indicators(
                raw_data, required_indicators, **kwargs
            )
            
            strategy_indicators[strategy_id] = indicators_data
        
        return strategy_indicators
    
    def update_strategy(self,
                       strategy_id: str,
                       indicators_data: Dict[str, Any],
                       **kwargs):
        """
        更新策略状态
        
        Args:
            strategy_id: 策略ID
            indicators_data: 指标数据字典
            **kwargs: 更新参数
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"策略 '{strategy_id}' 不存在")
        
        strategy = self.strategies[strategy_id]
        strategy.update(indicators_data, **kwargs)
    
    def get_strategy_info(self, strategy_id: str) -> Optional[Dict]:
        """
        获取策略信息
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            策略信息字典
        """
        if strategy_id in self.strategies:
            return self.strategies[strategy_id].get_info()
        return None
    
    def get_execution_stats(self) -> Dict:
        """
        获取执行统计
        
        Returns:
            执行统计字典
        """
        return self.execution_stats.copy()
    
    def clear_cache(self):
        """
        清除指标缓存
        """
        self.indicators_cache.clear()
        self.calculator.clear_cache()
        print("🧹 指标缓存已清除")
    
    def register_indicator(self, indicator_name: str, indicator_class):
        """
        注册自定义指标
        
        Args:
            indicator_name: 指标名称
            indicator_class: 指标类
        """
        self.registry.register_indicator(indicator_name, indicator_class)
        print(f"✅ 指标 '{indicator_name}' 注册成功")
    
    def get_available_indicators(self) -> List[str]:
        """
        获取所有可用的指标
        
        Returns:
            指标名称列表
        """
        return self.registry.get_all_indicators()