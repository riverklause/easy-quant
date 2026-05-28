"""
策略管理器
统一管理所有类型的策略（技术指标策略、多因子策略等）
"""

from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from strategy.base_strategy import BaseStrategy
from strategy.strategy_portfolio import StrategyPortfolio
from strategy.strategy_executor import StrategyExecutor


class StrategyManager:
    """
    策略管理器，统一管理所有策略
    支持技术指标策略、多因子策略等不同类型的策略
    """
    
    def __init__(self, data_manager=None, strategy_executor=None):
        """
        初始化策略管理器
        
        Args:
            data_manager: 数据管理器实例，用于数据获取
            strategy_executor: 策略执行器实例，如果为None则创建新的
        """
        self.data_manager = data_manager
        self.strategies: Dict[str, BaseStrategy] = {}
        self.portfolios: Dict[str, StrategyPortfolio] = {}  # 策略组合字典
        self.is_running = False
        
        # 策略执行器（负责指标计算和策略执行协调）
        self.executor = strategy_executor or StrategyExecutor()
        
        # 策略事件处理器
        self.event_handlers: Dict[str, List[Callable]] = {
            'signal_generated': [],
            'strategy_started': [],
            'strategy_stopped': [],
            'strategy_updated': [],
            'portfolio_added': [],
            'portfolio_removed': [],
            'portfolio_updated': []
        }
        
        # 全局信号历史
        self.global_signals = []
    
    def register_strategy(self, strategy: BaseStrategy) -> str:
        """
        注册策略
        
        Args:
            strategy: 策略实例，必须继承自BaseStrategy
            
        Returns:
            策略ID
        """
        if not isinstance(strategy, BaseStrategy):
            raise ValueError("策略必须继承自BaseStrategy")
        
        strategy_id = strategy.name
        if strategy_id in self.strategies:
            raise ValueError(f"策略ID '{strategy_id}' 已存在")
        
        self.strategies[strategy_id] = strategy
        self._emit_event('strategy_registered', {
            'strategy_id': strategy_id,
            'timestamp': datetime.now()
        })
        
        print(f"[+] 策略 '{strategy_id}' 注册成功")
        return strategy_id
    
    def unregister_strategy(self, strategy_id: str):
        """
        注销策略
        
        Args:
            strategy_id: 策略ID
        """
        if strategy_id in self.strategies:
            # 停止策略
            if self.strategies[strategy_id].is_running:
                self.strategies[strategy_id].stop()
            
            del self.strategies[strategy_id]
            self._emit_event('strategy_unregistered', {
                'strategy_id': strategy_id,
                'timestamp': datetime.now()
            })
            
            print(f"[-] 策略 '{strategy_id}' 注销成功")
    
    def start_strategy(self, strategy_id: str, **kwargs):
        """
        启动指定策略
        
        Args:
            strategy_id: 策略ID
            **kwargs: 启动参数
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"策略 '{strategy_id}' 不存在")
        
        strategy = self.strategies[strategy_id]
        if not strategy.is_running:
            strategy.initialize(**kwargs)
            strategy.start()
            self._emit_event('strategy_started', {
                'strategy_id': strategy_id,
                'timestamp': datetime.now()
            })
    
    def start_all_strategies(self, **kwargs):
        """
        启动所有策略
        
        Args:
            **kwargs: 启动参数
        """
        if not self.is_running:
            self.is_running = True
            
            for strategy_id in self.strategies:
                self.start_strategy(strategy_id, **kwargs)
            
            print(f"[+] 所有策略启动成功，共 {len(self.strategies)} 个策略")
    
    def stop_strategy(self, strategy_id: str):
        """
        停止指定策略
        
        Args:
            strategy_id: 策略ID
        """
        if strategy_id in self.strategies:
            strategy = self.strategies[strategy_id]
            if strategy.is_running:
                strategy.stop()
                self._emit_event('strategy_stopped', {
                    'strategy_id': strategy_id,
                    'timestamp': datetime.now()
                })
    
    def stop_all_strategies(self):
        """
        停止所有策略
        """
        if self.is_running:
            for strategy_id in self.strategies:
                self.stop_strategy(strategy_id)
            
            self.is_running = False
            print(f"🛑 所有策略已停止")
    
    def update_strategy(self, strategy_id: str, data: Any, **kwargs):
        """
        更新策略状态
        
        Args:
            strategy_id: 策略ID
            data: 最新数据
            **kwargs: 更新参数
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"策略 '{strategy_id}' 不存在")
        
        strategy = self.strategies[strategy_id]
        if strategy.is_running:
            # 使用executor更新策略状态
            self.executor.update_strategy(strategy, data, **kwargs)
            self._emit_event('strategy_updated', {
                'strategy_id': strategy_id,
                'timestamp': datetime.now()
            })
    
    def update_all_strategies(self, data: Any, **kwargs):
        """
        更新所有策略
        
        Args:
            data: 最新数据
            **kwargs: 更新参数
        """
        for strategy_id in self.strategies:
            self.update_strategy(strategy_id, data, **kwargs)
    
    def generate_signals(self, strategy_id: str, data: Any, **kwargs) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            strategy_id: 策略ID
            data: 输入数据（原始数据或指标数据）
            **kwargs: 计算参数
            
        Returns:
            交易信号列表
        """
        if strategy_id not in self.strategies:
            raise ValueError(f"策略 '{strategy_id}' 不存在")
        
        strategy = self.strategies[strategy_id]
        
        # 使用executor执行策略（executor负责指标计算和策略执行协调）
        signals = self.executor.execute_strategy(strategy, data, **kwargs)
        
        # 记录信号到全局历史
        for signal in signals:
            self.global_signals.append(signal)
            self._emit_event('signal_generated', {
                'signal': signal,
                'timestamp': datetime.now()
            })
        
        return signals
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """
        注册事件处理器
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
    
    def unregister_event_handler(self, event_type: str, handler: Callable):
        """
        注销事件处理器
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type in self.event_handlers:
            self.event_handlers[event_type] = [h for h in self.event_handlers[event_type] if h != handler]
    
    def get_strategy_info(self, strategy_id: str) -> Optional[Dict]:
        """
        获取策略信息
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            策略信息字典，None表示策略不存在
        """
        if strategy_id in self.strategies:
            return self.strategies[strategy_id].get_info()
        return None
    
    def get_all_strategies_info(self) -> List[Dict]:
        """
        获取所有策略信息
        
        Returns:
            策略信息列表
        """
        return [strategy.get_info() for strategy in self.strategies.values()]
    
    def get_strategy_performance(self, strategy_id: str) -> Optional[Dict]:
        """
        获取策略绩效
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            绩效统计字典，None表示策略不存在
        """
        if strategy_id in self.strategies:
            return self.strategies[strategy_id].get_performance()
        return None
    
    def get_global_signals(self, strategy_id: str = None) -> List[Dict]:
        """
        获取全局信号历史
        
        Args:
            strategy_id: 可选，策略ID，用于过滤特定策略的信号
            
        Returns:
            信号历史列表
        """
        if strategy_id:
            return [signal for signal in self.global_signals if signal.get('strategy_name') == strategy_id]
        return self.global_signals.copy()
    
    def clear_signals(self, strategy_id: str = None):
        """
        清除信号历史
        
        Args:
            strategy_id: 可选，策略ID，用于清除特定策略的信号
        """
        if strategy_id:
            # 清除特定策略的全局信号
            self.global_signals = [signal for signal in self.global_signals if signal.get('strategy_name') != strategy_id]
            
            # 清除策略内部信号
            if strategy_id in self.strategies:
                self.strategies[strategy_id].signals.clear()
        else:
            # 清除所有信号
            self.global_signals.clear()
            for strategy in self.strategies.values():
                strategy.signals.clear()
        
        print(f"[+] 信号历史已清除")
    
    def _emit_event(self, event_type: str, event_data: Dict):
        """
        触发事件
        
        Args:
            event_type: 事件类型
            event_data: 事件数据
        """
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(event_data)
                except Exception as e:
                    print(f"[-] 事件处理器 '{handler.__name__}' 执行失败: {e}")
    
    # 策略组合管理方法
    def add_portfolio(self, portfolio: StrategyPortfolio):
        """
        添加策略组合
        
        Args:
            portfolio: 策略组合实例
        """
        if not isinstance(portfolio, StrategyPortfolio):
            raise ValueError("portfolio必须是StrategyPortfolio实例")
        
        portfolio_name = portfolio.name
        if portfolio_name in self.portfolios:
            raise ValueError(f"策略组合 '{portfolio_name}' 已存在")
        
        self.portfolios[portfolio_name] = portfolio
        self._emit_event('portfolio_added', {
            'portfolio_name': portfolio_name,
            'timestamp': datetime.now()
        })
        
        print(f"[+] 策略组合 '{portfolio_name}' 已添加")
    
    def remove_portfolio(self, portfolio_name: str):
        """
        移除策略组合
        
        Args:
            portfolio_name: 策略组合名称
        """
        if portfolio_name in self.portfolios:
            del self.portfolios[portfolio_name]
            self._emit_event('portfolio_removed', {
                'portfolio_name': portfolio_name,
                'timestamp': datetime.now()
            })
            print(f"[-] 策略组合 '{portfolio_name}' 已移除")
    
    def get_portfolio(self, portfolio_name: str) -> Optional[StrategyPortfolio]:
        """
        获取策略组合
        
        Args:
            portfolio_name: 策略组合名称
            
        Returns:
            策略组合实例，None表示不存在
        """
        return self.portfolios.get(portfolio_name)
    
    def get_all_portfolios(self) -> List[str]:
        """
        获取所有策略组合名称
        
        Returns:
            策略组合名称列表
        """
        return list(self.portfolios.keys())
    
    def get_portfolio_info(self, portfolio_name: str) -> Optional[Dict]:
        """
        获取策略组合信息
        
        Args:
            portfolio_name: 策略组合名称
            
        Returns:
            策略组合信息字典，None表示不存在
        """
        if portfolio_name in self.portfolios:
            return self.portfolios[portfolio_name].get_portfolio_info()
        return None
    
    def get_strategies_for_stock(self, stock_symbol: str, portfolio_name: str = None) -> List[str]:
        """
        获取适用于特定股票的策略列表
        
        Args:
            stock_symbol: 股票代码
            portfolio_name: 策略组合名称，None表示使用所有组合
            
        Returns:
            适用的策略ID列表
        """
        applicable_strategies = []
        
        if portfolio_name:
            # 从特定组合获取
            if portfolio_name in self.portfolios:
                applicable_strategies = self.portfolios[portfolio_name].get_strategies_for_stock(stock_symbol)
        else:
            # 从所有组合获取
            for portfolio in self.portfolios.values():
                applicable_strategies.extend(portfolio.get_strategies_for_stock(stock_symbol))
        
        # 去重并返回
        return list(set(applicable_strategies))
    
    def add_strategy_to_portfolio(self, 
                                 portfolio_name: str,
                                 strategy_id: str,
                                 strategy_type: str,
                                 indicators: List[str],
                                 params: Dict,
                                 applicable_stocks: Optional[List[str]] = None):
        """
        向组合添加策略
        
        Args:
            portfolio_name: 策略组合名称
            strategy_id: 策略ID
            strategy_type: 策略类型
            indicators: 指标组合列表
            params: 策略参数
            applicable_stocks: 适用的股票列表，None表示适用于所有股票
        """
        if portfolio_name not in self.portfolios:
            raise ValueError(f"策略组合 '{portfolio_name}' 不存在")
        
        portfolio = self.portfolios[portfolio_name]
        portfolio.add_strategy(strategy_id, strategy_type, indicators, params, applicable_stocks)
        self._emit_event('portfolio_updated', {
            'portfolio_name': portfolio_name,
            'timestamp': datetime.now()
        })
    
    def remove_strategy_from_portfolio(self, portfolio_name: str, strategy_id: str):
        """
        从组合中移除策略
        
        Args:
            portfolio_name: 策略组合名称
            strategy_id: 策略ID
        """
        if portfolio_name not in self.portfolios:
            raise ValueError(f"策略组合 '{portfolio_name}' 不存在")
        
        portfolio = self.portfolios[portfolio_name]
        portfolio.remove_strategy(strategy_id)
        self._emit_event('portfolio_updated', {
            'portfolio_name': portfolio_name,
            'timestamp': datetime.now()
        })
    
    def generate_signals_for_stock(self, stock_symbol: str, data: Any, portfolio_name: str = None, **kwargs) -> List[Dict]:
        """
        为特定股票生成交易信号
        
        Args:
            stock_symbol: 股票代码
            data: 输入数据
            portfolio_name: 策略组合名称，None表示使用所有组合
            **kwargs: 计算参数
            
        Returns:
            交易信号列表
        """
        all_signals = []
        
        # 获取适用于该股票的策略
        applicable_strategies = self.get_strategies_for_stock(stock_symbol, portfolio_name)
        
        # 生成信号
        for strategy_id in applicable_strategies:
            if strategy_id in self.strategies:
                signals = self.generate_signals(strategy_id, data, **kwargs)
                all_signals.extend(signals)
        
        return all_signals
