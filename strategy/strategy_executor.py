"""
策略执行协调器
负责协调指标计算和策略执行，不负责策略管理和指标缓存
指标缓存由IndicatorCalculator统一管理
支持实时模式和非实时模式两种执行方式
"""

import asyncio
from typing import Dict, List, Any, Optional
import pandas as pd
from indicators.base.calculator import IndicatorCalculator
from indicators.base.registry import IndicatorRegistry
from strategy.base_strategy import BaseStrategy
from strategy.technical_strategy import TechnicalStrategy
from strategy.multi_factor.multi_factor_strategy import MultiFactorStrategy


class StrategyExecutor:
    """
    策略执行协调器
    职责：
    1. 协调指标计算和策略执行
    2. 管理执行统计
    3. 支持实时模式和非实时模式
    4. 不负责策略管理（由StrategyManager负责）
    5. 不负责指标缓存（由IndicatorCalculator负责）

    两种执行模式：
    - 非实时模式：手动调用execute_strategy()，数据由调用方传入
    - 实时模式：调用start_realtime_mode()启动，定时自动执行，数据从data_manager读取
    """
    
    def __init__(self, calculator: IndicatorCalculator = None):
        """
        初始化策略执行协调器
        
        Args:
            calculator: 指标计算器实例，如果为None则创建新的
        """
        # 指标计算器（负责指标计算和缓存）
        self.calculator = calculator or IndicatorCalculator()
        
        # 指标注册器（用于获取指标信息）
        self.registry = IndicatorRegistry()
        
        # 加载所有指标
        self.registry.load_indicators_from_package('indicators.technical')
        
        # 执行统计（只统计执行相关）
        self.execution_stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_indicators_calculated': 0
        }
        
        # 实时模式相关
        self._realtime_running = False
        self._realtime_task = None
        self._realtime_interval = 2  # 默认2秒
    
    def get_required_indicators(self, strategy: BaseStrategy) -> List[str]:
        """
        获取策略所需的所有指标
        
        Args:
            strategy: 策略实例
            
        Returns:
            所需指标名称列表
        """
        if isinstance(strategy, TechnicalStrategy):
            return strategy.get_required_indicators()
        elif isinstance(strategy, MultiFactorStrategy):
            return strategy.factor_names
        else:
            # 对于其他类型的策略，返回空列表
            return []
    
    def execute_strategy(self, 
                        strategy: BaseStrategy,
                        raw_data: Any,
                        calculate_indicators: bool = True,
                        **kwargs) -> List[Dict]:
        """
        执行单个策略（非实时模式）
        
        Args:
            strategy: 策略实例
            raw_data: 原始数据（当calculate_indicators=True时）或指标数据（当calculate_indicators=False时）
            calculate_indicators: 是否计算指标（如果为False，则raw_data应为指标数据）
            **kwargs: 执行参数
            
        Returns:
            交易信号列表
        """
        self.execution_stats['total_executions'] += 1
        
        try:
            if calculate_indicators:
                # 获取策略所需指标
                required_indicators = self.get_required_indicators(strategy)
                
                # 使用calculator批量计算指标（calculator负责缓存）
                indicators_data = self.calculator.batch_calculate(
                    raw_data, required_indicators, use_cache=True, **kwargs
                )
                
                # 更新指标计算统计
                self.execution_stats['total_indicators_calculated'] += len(required_indicators)
            else:
                # raw_data已经是指标数据
                indicators_data = raw_data
            
            # 执行策略（应用规则）
            signals = strategy.generate_signals(indicators_data, **kwargs)
            
            self.execution_stats['successful_executions'] += 1
            return signals
            
        except Exception as e:
            self.execution_stats['failed_executions'] += 1
            print(f"执行策略 '{strategy.name}' 失败: {e}")
            return []
    
    def execute_strategies(self,
                          strategies: Dict[str, BaseStrategy],
                          raw_data: Any,
                          calculate_indicators: bool = True,
                          **kwargs) -> Dict[str, List[Dict]]:
        """
        批量执行多个策略（非实时模式）
        
        Args:
            strategies: 策略字典，key为策略ID，value为策略实例
            raw_data: 原始数据（当calculate_indicators=True时）或指标数据字典（当calculate_indicators=False时）
            calculate_indicators: 是否计算指标（为False时，raw_data应为batch_calculate_for_strategies返回的指标字典）
            **kwargs: 执行参数
            
        Returns:
            策略信号字典，key为策略ID，value为信号列表
        """
        all_signals = {}
        
        for strategy_id, strategy in strategies.items():
            if calculate_indicators:
                signals = self.execute_strategy(
                    strategy, raw_data, calculate_indicators, **kwargs
                )
            else:
                indicators_data = raw_data.get(strategy_id, {})
                signals = self.execute_strategy(
                    strategy, indicators_data, calculate_indicators=False, **kwargs
                )
            all_signals[strategy_id] = signals
        
        return all_signals
    
    def batch_calculate_for_strategies(self,
                                      strategies: Dict[str, BaseStrategy],
                                      raw_data: Any,
                                      **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        为多个策略批量计算指标
        
        Args:
            strategies: 策略字典
            raw_data: 原始数据
            **kwargs: 计算参数
            
        Returns:
            策略指标数据字典，key为策略ID，value为指标数据字典
        """
        strategy_indicators = {}
        
        for strategy_id, strategy in strategies.items():
            # 获取策略所需指标
            required_indicators = self.get_required_indicators(strategy)
            
            if not required_indicators:
                print(f"⚠️ 策略 '{strategy_id}' 不需要指标，跳过")
                continue
            
            # 使用calculator批量计算指标
            indicators_data = self.calculator.batch_calculate(
                raw_data, required_indicators, use_cache=True, **kwargs
            )
            
            strategy_indicators[strategy_id] = indicators_data
            
            # 更新指标计算统计
            self.execution_stats['total_indicators_calculated'] += len(required_indicators)
        
        return strategy_indicators
    
    def update_strategy(self,
                       strategy: BaseStrategy,
                       indicators_data: Dict[str, Any],
                       **kwargs):
        """
        更新策略状态
        
        Args:
            strategy: 策略实例
            indicators_data: 指标数据字典
            **kwargs: 更新参数
        """
        strategy.update(indicators_data, **kwargs)
    
    def get_execution_stats(self) -> Dict:
        """
        获取执行统计
        
        Returns:
            执行统计字典
        """
        return self.execution_stats.copy()
    
    def clear_calculator_cache(self):
        """
        清除指标计算器的缓存
        注意：这只是清除calculator的缓存，不是executor的缓存
        """
        self.calculator.clear_cache()
        print("指标计算器缓存已清除")
    
    def register_indicator(self, indicator_name: str, indicator_class):
        """
        注册自定义指标到注册器
        
        Args:
            indicator_name: 指标名称
            indicator_class: 指标类
        """
        self.registry.register_indicator(indicator_name, indicator_class)
        print(f"指标 '{indicator_name}' 注册到注册器")
    
    def get_available_indicators(self) -> List[str]:
        """
        获取所有可用的指标
        
        Returns:
            指标名称列表
        """
        return self.registry.get_all_indicators()
    
    def get_calculator_stats(self) -> Dict:
        """
        获取指标计算器的统计信息
        
        Returns:
            计算器统计字典
        """
        return self.calculator.get_calculation_stats()
    
    async def start_realtime_mode(self,
                                 data_manager,
                                 symbols: List[str],
                                 strategies: Dict[str, BaseStrategy],
                                 interval: int = 2):
        """
        启动实时模式
        
        Args:
            data_manager: 数据管理器实例，用于获取实时数据
            symbols: 要监控的股票代码列表
            strategies: 要执行的策略字典，key为策略ID，value为策略实例
            interval: 执行间隔（秒），默认2秒
        
        Returns:
            None
        """
        if self._realtime_running:
            print("实时模式已在运行中")
            return
        
        self._realtime_running = True
        self._realtime_interval = interval
        self._realtime_task = asyncio.create_task(
            self._realtime_loop(data_manager, symbols, strategies)
        )
        print(f"实时模式已启动，间隔{interval}秒")
    
    async def _realtime_loop(self,
                            data_manager,
                            symbols: List[str],
                            strategies: Dict[str, BaseStrategy]):
        """
        实时模式循环（内部方法）
        
        Args:
            data_manager: 数据管理器实例
            symbols: 股票代码列表
            strategies: 策略字典
        """
        try:
            while self._realtime_running:
                # 遍历所有股票
                for symbol in symbols:
                    # 从data_manager获取该股票的实时K线数据
                    kline_data = data_manager.get_realtime_data('kline', symbol)
                    
                    if kline_data is None or len(kline_data) == 0:
                        continue
                    
                    # 收集该股票所需的所有指标
                    all_indicators = set()
                    for strategy in strategies.values():
                        required_indicators = self.get_required_indicators(strategy)
                        all_indicators.update(required_indicators)
                    
                    # 使用实时模式计算指标（覆盖更新缓存）
                    if all_indicators:
                        self.calculator.batch_calculate(
                            kline_data,
                            list(all_indicators),
                            use_cache=True,
                            cache_mode='realtime'
                        )
                
                # 执行所有策略
                for strategy_id, strategy in strategies.items():
                    try:
                        # 从实时缓存读取指标数据
                        indicators_data = {}
                        required_indicators = self.get_required_indicators(strategy)
                        
                        for indicator_id in required_indicators:
                            for symbol in symbols:
                                indicator_df = self.calculator.get_indicator(
                                    symbol, indicator_id, cache_mode='realtime'
                                )
                                if indicator_df is not None:
                                    if symbol not in indicators_data:
                                        indicators_data[symbol] = {}
                                    indicators_data[symbol][indicator_id] = indicator_df
                        
                        # 执行策略
                        if indicators_data:
                            signals = strategy.generate_signals(indicators_data)
                            if signals:
                                print(f"策略 '{strategy_id}' 产生信号: {signals}")
                        
                        self.execution_stats['successful_executions'] += 1
                    except Exception as e:
                        self.execution_stats['failed_executions'] += 1
                        print(f"执行策略 '{strategy_id}' 失败: {e}")
                
                self.execution_stats['total_executions'] += 1
                
                # 等待下一个周期
                await asyncio.sleep(self._realtime_interval)
                
        except asyncio.CancelledError:
            print("实时模式任务已取消")
        finally:
            self._realtime_running = False
            self._realtime_task = None
            print("实时模式已停止")
    
    def stop_realtime_mode(self):
        """
        停止实时模式
        """
        if not self._realtime_running:
            print("实时模式未运行")
            return
        
        self._realtime_running = False
        
        if self._realtime_task and not self._realtime_task.done():
            self._realtime_task.cancel()
            print("实时模式停止中...")
    
    def is_realtime_running(self) -> bool:
        """
        检查实时模式是否正在运行
        
        Returns:
            是否正在运行
        """
        return self._realtime_running