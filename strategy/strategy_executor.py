"""
策略执行协调器
负责协调指标计算和策略执行，不负责策略管理和指标缓存
指标缓存由IndicatorCalculator统一管理
支持实时模式和非实时模式两种执行方式
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import pandas as pd
from indicators.base.calculator import IndicatorCalculator
from indicators.base.errors import IndicatorCalculationError
from indicators.base.registry import IndicatorRegistry
from strategy.base_strategy import BaseStrategy
from strategy.technical_strategy import TechnicalStrategy
from strategy.indicator_spec import indicator_ids
from strategy.indicator_assembly import ensure_indicators
from strategy.multi_factor.multi_factor_strategy import MultiFactorStrategy
from utils.trading_calendar import (
    CalendarError,
    CalendarFutureUnavailable,
    CalendarUnavailable,
    infer_market,
)


logger = logging.getLogger(__name__)


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
    
    def __init__(
        self,
        calculator: IndicatorCalculator = None,
        status_sink: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        初始化策略执行协调器
        
        Args:
            calculator: 指标计算器实例，如果为None则创建新的
            status_sink: 可选实时状态接收方（如 web.calendar_runtime.record_realtime），
                每轮 tick 与停止时写入一次快照
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
        self._status_sink = status_sink
        # 实时健康快照：供 monitor 页与告警消费
        self.realtime_stats = {
            'ticks': 0,
            'indicator_errors': 0,
            'last_error': None,
            'stopped_reason': None,
            'skipped_off_session': 0,
            'last_tick_skipped': 0,
        }
        self.max_consecutive_failures = 3
    
    def get_required_indicators(self, strategy: BaseStrategy) -> List[str]:
        """
        获取策略所需的所有指标
        
        Args:
            strategy: 策略实例
            
        Returns:
            所需指标名称列表
        """
        if isinstance(strategy, TechnicalStrategy):
            return indicator_ids(strategy.get_required_indicators())
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
                ensure_indicators(
                    self.registry, self.calculator, strategy.get_required_indicators()
                )
                
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
            
        except IndicatorCalculationError:
            self.execution_stats['failed_executions'] += 1
            raise
        except Exception:
            self.execution_stats['failed_executions'] += 1
            logger.exception("执行策略 '%s' 失败", strategy.name)
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
            ensure_indicators(
                self.registry, self.calculator, strategy.get_required_indicators()
            )
            
            if not required_indicators:
                logger.warning("策略 '%s' 不需要指标，跳过", strategy_id)
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
    
    def get_realtime_stats(self) -> Dict:
        """实时模式健康快照：ticks / indicator_errors / last_error / stopped_reason。"""
        stats = dict(self.realtime_stats)
        stats['running'] = self._realtime_running
        return stats
    
    def clear_calculator_cache(self):
        """
        清除指标计算器的缓存
        注意：这只是清除calculator的缓存，不是executor的缓存
        """
        self.calculator.clear_cache()
        logger.info("指标计算器缓存已清除")
    
    def register_indicator(self, indicator_name: str, indicator_class):
        """
        注册自定义指标到注册器
        
        Args:
            indicator_name: 指标名称
            indicator_class: 指标类
        """
        self.registry.register_indicator(indicator_name, indicator_class)
        logger.info("指标 '%s' 注册到注册器", indicator_name)
    
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
            logger.info("实时模式已在运行中")
            return
        
        self._reset_realtime_stats()
        self._realtime_running = True
        self._realtime_interval = interval
        self._realtime_task = asyncio.create_task(
            self._realtime_loop(data_manager, symbols, strategies)
        )
        self._realtime_task.add_done_callback(self._on_realtime_task_done)
        logger.info("实时模式已启动，间隔%s秒", interval)
    
    def _reset_realtime_stats(self) -> None:
        self.realtime_stats.update({
            'ticks': 0,
            'indicator_errors': 0,
            'last_error': None,
            'stopped_reason': None,
            'skipped_off_session': 0,
            'last_tick_skipped': 0,
        })

    def _publish_status(self) -> None:
        """把实时健康快照推给可选接收方（监控页）。"""
        if self._status_sink is None:
            return
        try:
            self._status_sink({
                'running': self._realtime_running,
                'skipped_off_session': self.realtime_stats.get('skipped_off_session', 0),
                'last_tick_skipped': self.realtime_stats.get('last_tick_skipped', 0),
                'stopped_reason': self.realtime_stats.get('stopped_reason'),
                'updated_at': datetime.now().astimezone().isoformat(timespec='seconds'),
            })
        except Exception:  # noqa: BLE001 - 状态上报失败不能影响交易循环
            logger.exception("实时状态上报失败")

    def _active_symbols(self, data_manager, symbols: List[str], now: datetime):
        """按标的市场过滤出当前可交易的 symbol。

        日历缺失/不可用/无法推断市场一律抛 CalendarError（fail-closed），
        由实时循环停止并记录原因，不静默跳过。
        """
        getter = getattr(data_manager, 'get_trading_calendar', None)
        if not callable(getter):
            raise CalendarUnavailable(
                "data_manager 未提供 get_trading_calendar，无法判断交易时段"
            )
        try:
            calendar = getter()
        except CalendarError:
            raise
        except Exception as exc:  # noqa: BLE001 - 统一转成显式日历不可用
            raise CalendarUnavailable(f"获取交易日历失败: {exc}") from exc
        if calendar is None:
            raise CalendarUnavailable("交易日历未初始化")

        market_open: Dict[str, bool] = {}
        active: List[str] = []
        skipped: List[str] = []
        for symbol in symbols:
            market = infer_market(symbol)
            if market is None:
                raise CalendarError(f"无法推断 {symbol} 的市场，无法判断交易时段")
            if market not in market_open:
                if calendar.is_trading_day(now, market):
                    market_open[market] = calendar.is_trading_time(now, market)
                else:
                    market_open[market] = False
            (active if market_open[market] else skipped).append(symbol)
        return active, skipped

    def _on_realtime_task_done(self, task: asyncio.Task) -> None:
        """实时任务异常退出时留痕。
        
        asyncio 只在 GC 时才打 "Task exception was never retrieved"，
        对监控来说等于没有，所以这里显式记录原因。
        """
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            self.realtime_stats['stopped_reason'] = f"实时任务异常退出: {exc!r}"
            logger.error("实时任务异常退出: %r", exc, exc_info=exc)
            self._publish_status()
    
    def _realtime_tick(self,
                       data_manager,
                       symbols: List[str],
                       strategies: Dict[str, BaseStrategy],
                       now: Optional[datetime] = None) -> set:
        """执行一轮实时评估，返回本轮指标计算失败的 symbol 集合。

        失败的 symbol 不得进入策略评估：calculator 里留着上一轮的旧值，
        用它出信号比少算一只股票危险得多。休市标的同样不得进入指标与信号。
        """
        failed = set()

        # 按标的市场门控：休市/非交易时段跳过，日历异常 fail-closed 向上抛
        moment = now or datetime.now().astimezone()
        active, skipped = self._active_symbols(data_manager, symbols, moment)
        self.realtime_stats['skipped_off_session'] += len(skipped)
        self.realtime_stats['last_tick_skipped'] = len(skipped)

        # 装配期错误（声明的指标造不出来）不可自愈，直接冒泡让循环停下
        for strategy in strategies.values():
            if isinstance(strategy, TechnicalStrategy):
                ensure_indicators(
                    self.registry, self.calculator, strategy.get_required_indicators()
                )
        
        # 收集所有策略所需的所有指标（策略声明是静态的，不必逐股票重算）
        all_indicators = set()
        for strategy in strategies.values():
            all_indicators.update(self.get_required_indicators(strategy))
        
        # 只遍历当前可交易的股票
        for symbol in active:
            if not all_indicators:
                break
            # 从data_manager获取该股票的实时K线数据
            kline_data = data_manager.get_realtime_data('kline', symbol)
            
            if kline_data is None or len(kline_data) == 0:
                continue
            
            # 使用实时模式计算指标（覆盖更新缓存）
            try:
                self.calculator.batch_calculate(
                    kline_data,
                    list(all_indicators),
                    use_cache=True,
                    cache_mode='realtime'
                )
            except IndicatorCalculationError as exc:
                self.realtime_stats['indicator_errors'] += 1
                self.realtime_stats['last_error'] = repr(exc)
                logger.exception("指标计算失败: %s", symbol)
                failed.add(symbol)
        
        # 执行所有策略
        for strategy_id, strategy in strategies.items():
            try:
                # 从实时缓存读取指标数据
                indicators_data = {}
                required_indicators = self.get_required_indicators(strategy)
                
                for indicator_id in required_indicators:
                    for symbol in active:
                        if symbol in failed:
                            continue
                        indicator_df = self.calculator.get_indicator(
                            symbol, indicator_id, cache_mode='realtime'
                        )
                        if indicator_df is not None:
                            indicators_data.setdefault(symbol, {})[indicator_id] = indicator_df
                
                # 执行策略
                if indicators_data:
                    signals = strategy.generate_signals(indicators_data)
                    if signals:
                        logger.info("策略 '%s' 产生信号: %s", strategy_id, signals)
                
                self.execution_stats['successful_executions'] += 1
            except Exception as e:
                self.execution_stats['failed_executions'] += 1
                logger.exception("执行策略 '%s' 失败: %s", strategy_id, e)
        
        self.execution_stats['total_executions'] += 1
        self.realtime_stats['ticks'] += 1
        return failed
    
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
        consecutive_failures = 0
        try:
            while self._realtime_running:
                try:
                    failed = self._realtime_tick(data_manager, symbols, strategies)
                except CalendarFutureUnavailable as exc:
                    self.realtime_stats['stopped_reason'] = (
                        "跨年日历未发布，请次年 1 月 1 日后重试"
                    )
                    logger.error("%s: %s", self.realtime_stats['stopped_reason'], exc)
                    break
                except CalendarError as exc:
                    self.realtime_stats['stopped_reason'] = (
                        f"交易日历不可用，实时循环已停止: {exc}"
                    )
                    logger.error("%s", self.realtime_stats['stopped_reason'])
                    break

                self._publish_status()
                
                consecutive_failures = consecutive_failures + 1 if failed else 0
                if consecutive_failures >= self.max_consecutive_failures:
                    self.realtime_stats['stopped_reason'] = (
                        f"连续 {consecutive_failures} 轮指标计算失败，已停止"
                    )
                    logger.error("%s", self.realtime_stats['stopped_reason'])
                    break
                
                # 等待下一个周期
                await asyncio.sleep(self._realtime_interval)
                
        except asyncio.CancelledError:
            logger.info("实时模式任务已取消")
            raise
        finally:
            # 兜底：running 变 False 时 stopped_reason 必须非空，监控页不能出现"停了但不知道为什么"
            if self.realtime_stats['stopped_reason'] is None:
                self.realtime_stats['stopped_reason'] = "循环退出"
            self._realtime_running = False
            self._realtime_task = None
            self._publish_status()
            logger.info("实时模式已停止")
    
    def stop_realtime_mode(self):
        """
        停止实时模式
        """
        if not self._realtime_running:
            logger.info("实时模式未运行")
            return
        
        self._realtime_running = False
        self.realtime_stats['stopped_reason'] = "用户取消"
        
        if self._realtime_task and not self._realtime_task.done():
            self._realtime_task.cancel()
            logger.info("实时模式停止中...")
    
    def is_realtime_running(self) -> bool:
        """
        检查实时模式是否正在运行
        
        Returns:
            是否正在运行
        """
        return self._realtime_running