"""
指标计算器
管理多个指标的计算和缓存
支持多股票批量计算
支持历史模式和实时模式两种缓存策略
"""

from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
from .base_indicator import BaseIndicator


class IndicatorCalculator:
    """
    指标计算器，负责指标对象的引入/注销和指标处理逻辑，具体的计算是由指标类实现的,需要注意的是：
    1. 指标计算器是线程安全的，多个线程可以同时使用同一个指标计算器
    2. 指标计算器会缓存指标计算结果，按股票分组存储，避免重复计算
    3. 指标要先用IndicatorRegistry类创建指标实例化对象，然后注册到计算器，才能被calculate方法使用
    4. 支持两种缓存模式：history（历史数据，hash对比）和realtime（实时数据，覆盖更新）

    历史缓存结构 (_cache)：
        {
            'AAPL': {
                'hash_key': {'data': result, 'timestamp': datetime}
            }
        }

    实时缓存结构 (_realtime_cache)：
        {
            'AAPL': {
                'sma_20': pd.DataFrame,
                'rsi_14': pd.DataFrame
            }
        }

    使用方法：
    1. 初始化指标计算器：calculator = IndicatorCalculator()
    2. 注册指标：calculator.register_indicator(indicator_instance, indicator_id)
    3. 批量计算指标：results = calculator.batch_calculate(data, indicator_ids)
       - 输入数据支持三种形式：pd.DataFrame、pd.Series、List[Dict]
       - 自动按股票代码分组处理
       - 返回格式：{股票代码: {指标ID: 计算结果}}
    4. 实时模式计算：results = calculator.batch_calculate(data, indicator_ids, cache_mode='realtime')
    5. 读取指标：result = calculator.get_indicator('AAPL', 'sma_20', cache_mode='realtime')
    6. 注销指标：calculator.unregister_indicator(indicator_id)
    7. 辅助方法：
       - get_calculation_stats()：查看计算统计
       - clear_cache()：清除缓存（可指定股票或指标）
    """

    def __init__(self,
                 cache_size: int = 300,
                 cache_ttl: int = 3600):
        """
        初始化指标计算器

        Args:
            cache_size: 历史缓存大小
            cache_ttl: 历史缓存生存时间（秒）
        """
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self.indicators: Dict[str, BaseIndicator] = {}
        
        # 历史数据缓存（hash对比模式）
        self._cache: Dict[str, Dict[str, Dict]] = {}
        
        # 实时数据缓存（覆盖更新模式）
        self._realtime_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        
        self._cache_lock = threading.RLock()
        self._calculation_stats = {
            'total_calculations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }

    def register_indicator(self,
                          indicator: BaseIndicator,
                          indicator_id: Optional[str] = None) -> str:
        """
        注册指标，将指标实例和指标ID添加到计算器中，返回指标ID

        Args:
            indicator: 指标实例
            indicator_id: 指标ID，如果为None则自动使用指标名称作为ID

        Returns:
            指标ID
        """
        if indicator_id is None:
            indicator_id = indicator.name

        if indicator_id in self.indicators:
            raise ValueError(f"指标ID '{indicator_id}' 已存在")

        self.indicators[indicator_id] = indicator
        return indicator_id

    def unregister_indicator(self, indicator_id: str):
        """注销指标，从计算器中移除指标实例和相关缓存

        Args:
            indicator_id: 指标ID
        """
        if indicator_id in self.indicators:
            del self.indicators[indicator_id]
            self._clear_cache_for_indicator(indicator_id)
            self._clear_realtime_cache_for_indicator(indicator_id)

    def calculate(self,
                  indicator_id: str,
                  data: Union[pd.DataFrame, pd.Series, List[Dict]],
                  use_cache: bool = True,
                  cache_mode: str = 'history',
                  **kwargs) -> Any:
        """
        计算指定指标（兼容旧接口）

        Args:
            indicator_id: 指标ID
            data: 输入数据
            use_cache: 是否使用缓存
            cache_mode: 缓存模式，'history' 或 'realtime'
            **kwargs: 计算参数

        Returns:
            指标计算结果
        """
        results = self.batch_calculate(data, [indicator_id], use_cache, cache_mode=cache_mode, **kwargs)

        for symbol, symbol_results in results.items():
            if indicator_id in symbol_results:
                result = symbol_results[indicator_id]
                if isinstance(result, dict) and 'error' in result:
                    raise ValueError(f"指标计算错误: {result['error']}")
                return result

        raise ValueError(f"未找到指标计算结果: {indicator_id}")

    def batch_calculate(self,
                       data: Union[pd.DataFrame, pd.Series, List[Dict]],
                       indicator_ids: Optional[List[str]] = None,
                       use_cache: bool = True,
                       cache_mode: str = 'history',
                       **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        批量计算多个股票的多个指标

        Args:
            data: 输入数据
                  - pd.DataFrame：来自数据模块，索引为 [time_key, code]
                  - pd.Series：单列数据
                  - List[Dict]：实时数据
            indicator_ids: 要计算的指标ID列表，None表示计算所有已注册指标
            use_cache: 是否使用缓存
            cache_mode: 缓存模式
                        - 'history': 历史模式，使用hash对比，TTL淘汰
                        - 'realtime': 实时模式，直接覆盖更新，无hash对比
            **kwargs: 计算参数

        Returns:
            {股票代码: {指标ID: 计算结果}}
            例如：{'AAPL': {'sma_20': Series}, 'MSFT': {'sma_20': Series}}
        """
        if indicator_ids is None:
            indicator_ids = list(self.indicators.keys())

        processed_data = self._preprocess_data(data)
        data_by_symbol = self._split_by_symbol(processed_data)

        results = {}
        
        if cache_mode == 'realtime':
            # 实时模式：直接覆盖更新，无hash对比
            for symbol, symbol_data in data_by_symbol.items():
                results[symbol] = {}
                
                for indicator_id in indicator_ids:
                    if indicator_id not in self.indicators:
                        results[symbol][indicator_id] = {'error': f"未找到指标: {indicator_id}"}
                        continue
                    
                    try:
                        indicator = self.indicators[indicator_id]
                        result = indicator.calculate(symbol_data, **kwargs)
                        results[symbol][indicator_id] = result
                        
                        if use_cache:
                            self._update_realtime_cache(symbol, indicator_id, result)
                        
                        self._calculation_stats['total_calculations'] += 1
                    except Exception as e:
                        results[symbol][indicator_id] = {'error': str(e)}
        
        else:
            # 历史模式：hash对比，TTL淘汰
            for symbol, symbol_data in data_by_symbol.items():
                results[symbol] = {}

                for indicator_id in indicator_ids:
                    if indicator_id not in self.indicators:
                        results[symbol][indicator_id] = {'error': f"未找到指标: {indicator_id}"}
                        continue

                    cache_key = self._generate_cache_key(indicator_id, symbol, symbol_data, kwargs)
                    cached_result = None

                    if use_cache:
                        cached_result = self._get_from_cache(symbol, cache_key)

                    if cached_result is not None:
                        results[symbol][indicator_id] = cached_result
                        self._calculation_stats['cache_hits'] += 1
                    else:
                        try:
                            indicator = self.indicators[indicator_id]
                            result = indicator.calculate(symbol_data, **kwargs)
                            results[symbol][indicator_id] = result

                            if use_cache:
                                self._add_to_cache(symbol, cache_key, result)

                            self._calculation_stats['total_calculations'] += 1
                            self._calculation_stats['cache_misses'] += 1
                        except Exception as e:
                            results[symbol][indicator_id] = {'error': str(e)}

        return results

    def get_indicator(self,
                      symbol: str,
                      indicator_id: str,
                      cache_mode: str = 'realtime') -> Optional[pd.DataFrame]:
        """
        从缓存中读取指标值

        Args:
            symbol: 股票代码
            indicator_id: 指标ID
            cache_mode: 缓存模式，'history' 或 'realtime'

        Returns:
            指标数据（DataFrame），如果不存在返回None
        """
        if cache_mode == 'realtime':
            return self._realtime_cache.get(symbol, {}).get(indicator_id)
        else:
            # 历史模式需要遍历hash key查找
            if symbol in self._cache:
                for key, entry in self._cache[symbol].items():
                    if indicator_id in key:
                        return entry.get('data')
            return None

    def _update_realtime_cache(self, symbol: str, indicator_id: str, data: pd.DataFrame):
        """更新实时缓存（覆盖式更新）"""
        with self._cache_lock:
            if symbol not in self._realtime_cache:
                self._realtime_cache[symbol] = {}
            
            self._realtime_cache[symbol][indicator_id] = data

    def _clear_realtime_cache_for_indicator(self, indicator_id: str):
        """清理所有股票中指定指标的实时缓存"""
        with self._cache_lock:
            for symbol in list(self._realtime_cache.keys()):
                if indicator_id in self._realtime_cache[symbol]:
                    del self._realtime_cache[symbol][indicator_id]
                
                if not self._realtime_cache[symbol]:
                    del self._realtime_cache[symbol]

    def clear_realtime_cache(self, symbol: Optional[str] = None, indicator_id: Optional[str] = None):
        """
        清空实时缓存

        Args:
            symbol: 清理指定股票的缓存，None表示所有股票
            indicator_id: 清理指定指标的缓存，None表示所有指标
        """
        with self._cache_lock:
            if symbol is None and indicator_id is None:
                self._realtime_cache.clear()
            
            elif symbol is not None and indicator_id is None:
                if symbol in self._realtime_cache:
                    del self._realtime_cache[symbol]
            
            elif symbol is None and indicator_id is not None:
                self._clear_realtime_cache_for_indicator(indicator_id)
            
            else:
                if symbol in self._realtime_cache and indicator_id in self._realtime_cache[symbol]:
                    del self._realtime_cache[symbol][indicator_id]

    def _preprocess_data(self,
                        data: Union[pd.DataFrame, pd.Series, List[Dict]]
                        ) -> Union[pd.DataFrame, pd.Series]:
        """
        预处理输入数据

        Args:
            data: 原始输入数据

        Returns:
            预处理后的数据
        """
        if isinstance(data, pd.Series):
            return data.copy()

        elif isinstance(data, pd.DataFrame):
            return data.copy()

        else:
            df = pd.DataFrame(data)
            df.set_index(['time_key', 'code'], inplace=True)
            return df

    def _split_by_symbol(self, data: Union[pd.DataFrame, pd.Series]
                        ) -> Dict[str, Union[pd.DataFrame, pd.Series]]:
        """
        按股票代码分组拆分数据

        Args:
            data: 预处理后的数据

        Returns:
            {股票代码: 单股票数据}
        """
        if isinstance(data, pd.Series):
            return {'unknown': data}

        if isinstance(data.index, pd.MultiIndex) and 'code' in data.index.names:
            codes = data.index.get_level_values('code').unique()
            return {code: data.xs(code, level='code') for code in codes}

        return {'unknown': data}

    def _generate_cache_key(self,
                           indicator_id: str,
                           symbol: str,
                           data: Any,
                           kwargs: Dict) -> str:
        """
        生成缓存键（包含股票代码）

        Args:
            indicator_id: 指标ID
            symbol: 股票代码
            data: 输入数据
            kwargs: 计算参数

        Returns:
            缓存键字符串
        """
        if isinstance(data, (pd.DataFrame, pd.Series)):
            if len(data) > 0:
                data_hash = hash(data.values.tobytes())
            else:
                data_hash = hash(type(data).__name__)
        else:
            data_hash = hash(str(data)) if hasattr(data, '__hash__') else hash(str(id(data)))
        
        kwargs_hash = hash(str(sorted(kwargs.items()))) if kwargs else 0

        return f"{symbol}_{indicator_id}_{data_hash}_{kwargs_hash}"

    def _get_from_cache(self, symbol: str, cache_key: str) -> Optional[Any]:
        """从历史缓存获取数据"""
        with self._cache_lock:
            if symbol not in self._cache:
                return None

            if cache_key not in self._cache[symbol]:
                return None

            cache_entry = self._cache[symbol][cache_key]
            if datetime.now() - cache_entry['timestamp'] < timedelta(seconds=self.cache_ttl):
                return cache_entry['data']
            else:
                del self._cache[symbol][cache_key]

        return None

    def _add_to_cache(self, symbol: str, cache_key: str, data: Any):
        """添加数据到历史缓存"""
        with self._cache_lock:
            if symbol not in self._cache:
                self._cache[symbol] = {}

            self._cache[symbol][cache_key] = {
                'data': data,
                'timestamp': datetime.now()
            }

            total_cache_size = sum(len(v) for v in self._cache.values())
            if total_cache_size > self.cache_size:
                self._evict_oldest()

    def _evict_oldest(self):
        """淘汰历史缓存中最旧的缓存项"""
        oldest_symbol = None
        oldest_key = None
        oldest_time = datetime.max

        for symbol, symbol_cache in self._cache.items():
            for key, entry in symbol_cache.items():
                if entry['timestamp'] < oldest_time:
                    oldest_time = entry['timestamp']
                    oldest_symbol = symbol
                    oldest_key = key

        if oldest_symbol and oldest_key:
            del self._cache[oldest_symbol][oldest_key]
            if not self._cache[oldest_symbol]:
                del self._cache[oldest_symbol]

    def _clear_cache_for_indicator(self, indicator_id: str):
        """清理所有股票中指定指标的历史缓存"""
        with self._cache_lock:
            for symbol in list(self._cache.keys()):
                keys_to_remove = [k for k in self._cache[symbol].keys()
                                if k.endswith(f"_{indicator_id}_") or
                                   k.endswith(f"_{indicator_id}")]
                for key in keys_to_remove:
                    del self._cache[symbol][key]

                if not self._cache[symbol]:
                    del self._cache[symbol]

    def clear_cache(self, symbol: Optional[str] = None, indicator_id: Optional[str] = None):
        """
        清空历史缓存

        Args:
            symbol: 清理指定股票的缓存，None表示所有股票
            indicator_id: 清理指定指标的缓存，None表示所有指标
        """
        with self._cache_lock:
            if symbol is None and indicator_id is None:
                self._cache.clear()

            elif symbol is not None and indicator_id is None:
                if symbol in self._cache:
                    del self._cache[symbol]

            elif symbol is None and indicator_id is not None:
                self._clear_cache_for_indicator(indicator_id)

            else:
                if symbol in self._cache:
                    keys_to_remove = [k for k in self._cache[symbol].keys()
                                    if k.endswith(f"_{indicator_id}_") or
                                       k.endswith(f"_{indicator_id}")]
                    for key in keys_to_remove:
                        del self._cache[symbol][key]

    def get_indicator_info(self, indicator_id: str) -> Dict[str, Any]:
        """获取指定指标的内置信息"""
        if indicator_id not in self.indicators:
            raise ValueError(f"未找到指标: {indicator_id}")

        return self.indicators[indicator_id].get_info()

    def get_calculation_stats(self) -> Dict[str, int]:
        """获取计算统计信息"""
        return self._calculation_stats.copy()

    def update_indicator(self,
                        indicator_id: str,
                        new_data: Union[pd.DataFrame, pd.Series, Dict],
                        use_cache: bool = True,
                        symbol: Optional[str] = None,
                        cache_mode: str = 'history',
                        **kwargs) -> Any:
        """
        增量更新单个指标

        Args:
            indicator_id: 指标ID
            new_data: 新增数据
            use_cache: 是否使用缓存
            symbol: 股票代码，如果为None则尝试从数据中提取
            cache_mode: 缓存模式
            **kwargs: 更新参数

        Returns:
            更新后的指标值
        """
        if symbol is None:
            if isinstance(new_data, pd.DataFrame):
                if isinstance(new_data.index, pd.MultiIndex) and 'code' in new_data.index.names:
                    codes = new_data.index.get_level_values('code').unique()
                    symbol = codes[0] if len(codes) > 0 else 'unknown'
                elif 'code' in new_data.columns:
                    symbol = new_data['code'].iloc[0]
            elif isinstance(new_data, list) and len(new_data) > 0:
                symbol = new_data[0].get('code', 'unknown')
            else:
                symbol = 'unknown'

        results = self.batch_update_indicators(new_data, [indicator_id], use_cache, symbol=symbol, cache_mode=cache_mode, **kwargs)

        if symbol in results and indicator_id in results[symbol]:
            result = results[symbol][indicator_id]
            if isinstance(result, dict) and 'error' in result:
                raise ValueError(f"指标更新错误: {result['error']}")
            return result

        raise ValueError(f"未找到指标更新结果: {indicator_id}")

    def batch_update_indicators(self,
                               new_data: Union[pd.DataFrame, pd.Series, Dict],
                               indicator_ids: Optional[List[str]] = None,
                               use_cache: bool = True,
                               symbol: Optional[str] = None,
                               cache_mode: str = 'history',
                               **kwargs) -> Dict[str, Dict[str, Any]]:
        """
        批量增量更新多个指标

        Args:
            new_data: 新增数据
            indicator_ids: 要更新的指标ID列表
            use_cache: 是否使用缓存
            symbol: 股票代码
            cache_mode: 缓存模式
            **kwargs: 更新参数

        Returns:
            {股票代码: {指标ID: 结果}}
        """
        if indicator_ids is None:
            indicator_ids = list(self.indicators.keys())

        processed_data = self._preprocess_data(new_data)
        data_by_symbol = self._split_by_symbol(processed_data)

        results = {}
        
        if cache_mode == 'realtime':
            # 实时模式：直接覆盖更新
            for sym, sym_data in data_by_symbol.items():
                actual_symbol = symbol if symbol else sym
                results[actual_symbol] = {}

                for indicator_id in indicator_ids:
                    if indicator_id not in self.indicators:
                        results[actual_symbol][indicator_id] = {'error': f"未找到指标: {indicator_id}"}
                        continue

                    try:
                        indicator = self.indicators[indicator_id]
                        result = indicator.update(sym_data, **kwargs)
                        results[actual_symbol][indicator_id] = result

                        if use_cache:
                            self._update_realtime_cache(actual_symbol, indicator_id, result)

                        self._calculation_stats['total_calculations'] += 1
                    except Exception as e:
                        results[actual_symbol][indicator_id] = {'error': str(e)}
        
        else:
            # 历史模式：hash对比
            for sym, sym_data in data_by_symbol.items():
                actual_symbol = symbol if symbol else sym
                results[actual_symbol] = {}

                for indicator_id in indicator_ids:
                    if indicator_id not in self.indicators:
                        results[actual_symbol][indicator_id] = {'error': f"未找到指标: {indicator_id}"}
                        continue

                    cache_key = self._generate_cache_key(indicator_id, actual_symbol, sym_data, kwargs)
                    cached_result = None

                    if use_cache:
                        cached_result = self._get_from_cache(actual_symbol, cache_key)

                    if cached_result is not None:
                        results[actual_symbol][indicator_id] = cached_result
                        self._calculation_stats['cache_hits'] += 1
                    else:
                        try:
                            indicator = self.indicators[indicator_id]
                            result = indicator.update(sym_data, **kwargs)
                            results[actual_symbol][indicator_id] = result

                            if use_cache:
                                self._add_to_cache(actual_symbol, cache_key, result)

                            self._calculation_stats['total_calculations'] += 1
                        except Exception as e:
                            results[actual_symbol][indicator_id] = {'error': str(e)}

                        self._calculation_stats['cache_misses'] += 1

        return results