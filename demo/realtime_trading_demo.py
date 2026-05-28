"""
实时交易系统演示 - 展示Futu API实时数据在交易策略中的应用
"""
import asyncio
import time
from datetime import datetime
from typing import List, Dict, Optional
import random

# 策略类定义
from typing import List, Dict, Optional
from datetime import datetime


class BaseRealtimeStrategy:
    """实时交易策略基类"""
    
    def __init__(self, name: str, watch_symbols: List[str]):
        self.name = name
        self.watch_symbols = watch_symbols
        self.position = {}  # 持仓信息
        self.indicators = {}  # 技术指标
        self.signals = []  # 交易信号历史
        
    def on_kline_update(self, kline_data: Dict):
        """K线数据更新回调"""
        raise NotImplementedError("子类必须实现此方法")
        
    def on_order_book_update(self, order_book_data: Dict):
        """摆盘数据更新回调"""
        raise NotImplementedError("子类必须实现此方法")
        
    def on_market_depth_update(self, market_depth: Dict):
        """市场深度更新回调"""
        pass
        
    def generate_signal(self, kline_data: Dict) -> Optional[Dict]:
        """生成交易信号"""
        raise NotImplementedError("子类必须实现此方法")


class MovingAverageStrategy(BaseRealtimeStrategy):
    """移动平均线策略"""
    
    def __init__(self, watch_symbols: List[str], fast_period: int = 5, slow_period: int = 20):
        super().__init__("移动平均线策略", watch_symbols)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.price_history = {symbol: [] for symbol in watch_symbols}
        
    def on_kline_update(self, kline_data: Dict):
        """处理K线数据更新"""
        symbol = kline_data['symbol']
        close_price = kline_data['close']
        
        # 更新价格历史
        self.price_history[symbol].append(close_price)
        
        # 保持历史数据长度
        if len(self.price_history[symbol]) > self.slow_period * 2:
            self.price_history[symbol] = self.price_history[symbol][-self.slow_period * 2:]
        
        # 计算移动平均线
        if len(self.price_history[symbol]) >= self.slow_period:
            fast_ma = self._calculate_ma(self.price_history[symbol], self.fast_period)
            slow_ma = self._calculate_ma(self.price_history[symbol], self.slow_period)
            
            # 更新指标
            if symbol not in self.indicators:
                self.indicators[symbol] = {}
            
            self.indicators[symbol]['fast_ma'] = fast_ma
            self.indicators[symbol]['slow_ma'] = slow_ma
            
            # 打印指标信息
            print(f"{symbol} - 快线MA{self.fast_period}: {fast_ma:.2f}, "
                  f"慢线MA{self.slow_period}: {slow_ma:.2f}")
    
    def on_order_book_update(self, order_book_data: Dict):
        """处理摆盘数据更新"""
        symbol = order_book_data['symbol']
        
        # 分析买卖盘口
        bid_ask_spread = order_book_data['ask_prices'][0] - order_book_data['bid_prices'][0]
        total_bid_volume = sum(order_book_data['bid_volumes'])
        total_ask_volume = sum(order_book_data['ask_volumes'])
        
        print(f"{symbol} - 买卖价差: {bid_ask_spread:.3f}, "
              f"买盘总量: {total_bid_volume}, 卖盘总量: {total_ask_volume}")
    
    def generate_signal(self, kline_data: Dict) -> Optional[Dict]:
        """生成交易信号"""
        symbol = kline_data['symbol']
        
        if symbol not in self.indicators:
            return None
            
        fast_ma = self.indicators[symbol].get('fast_ma')
        slow_ma = self.indicators[symbol].get('slow_ma')
        
        if fast_ma is None or slow_ma is None:
            return None
        
        current_price = kline_data['close']
        
        # 金叉信号：快线上穿慢线
        if fast_ma > slow_ma and len(self.price_history[symbol]) > 1:
            prev_fast_ma = self._calculate_ma(self.price_history[symbol][-2:], self.fast_period)
            prev_slow_ma = self._calculate_ma(self.price_history[symbol][-2:], self.slow_period)
            
            if prev_fast_ma <= prev_slow_ma:  # 之前是死叉或相等
                signal = {
                    'symbol': symbol,
                    'signal_type': 'BUY',
                    'price': current_price,
                    'reason': f"MA金叉: 快线{fast_ma:.2f} > 慢线{slow_ma:.2f}",
                    'timestamp': datetime.now()
                }
                self.signals.append(signal)
                return signal
        
        # 死叉信号：快线下穿慢线
        elif fast_ma < slow_ma and len(self.price_history[symbol]) > 1:
            prev_fast_ma = self._calculate_ma(self.price_history[symbol][-2:], self.fast_period)
            prev_slow_ma = self._calculate_ma(self.price_history[symbol][-2:], self.slow_period)
            
            if prev_fast_ma >= prev_slow_ma:  # 之前是金叉或相等
                signal = {
                    'symbol': symbol,
                    'signal_type': 'SELL',
                    'price': current_price,
                    'reason': f"MA死叉: 快线{fast_ma:.2f} < 慢线{slow_ma:.2f}",
                    'timestamp': datetime.now()
                }
                self.signals.append(signal)
                return signal
        
        return None
    
    def _calculate_ma(self, prices: List[float], period: int) -> float:
        """计算移动平均线"""
        if len(prices) < period:
            return sum(prices) / len(prices)
        return sum(prices[-period:]) / period


class BreakoutStrategy(BaseRealtimeStrategy):
    """突破策略"""
    
    def __init__(self, watch_symbols: List[str], breakout_period: int = 20):
        super().__init__("突破策略", watch_symbols)
        self.breakout_period = breakout_period
        self.high_low_history = {symbol: {'highs': [], 'lows': []} for symbol in watch_symbols}
        
    def on_kline_update(self, kline_data: Dict):
        """处理K线数据更新"""
        symbol = kline_data['symbol']
        high = kline_data['high']
        low = kline_data['low']
        
        # 更新高低点历史
        self.high_low_history[symbol]['highs'].append(high)
        self.high_low_history[symbol]['lows'].append(low)
        
        # 保持历史数据长度
        if len(self.high_low_history[symbol]['highs']) > self.breakout_period * 2:
            self.high_low_history[symbol]['highs'] = self.high_low_history[symbol]['highs'][-self.breakout_period * 2:]
            self.high_low_history[symbol]['lows'] = self.high_low_history[symbol]['lows'][-self.breakout_period * 2:]
        
        # 计算突破位
        if len(self.high_low_history[symbol]['highs']) >= self.breakout_period:
            resistance = max(self.high_low_history[symbol]['highs'][-self.breakout_period:-1])
            support = min(self.high_low_history[symbol]['lows'][-self.breakout_period:-1])
            
            if symbol not in self.indicators:
                self.indicators[symbol] = {}
            
            self.indicators[symbol]['resistance'] = resistance
            self.indicators[symbol]['support'] = support
            
            print(f"{symbol} - 阻力位: {resistance:.2f}, 支撑位: {support:.2f}")
    
    def on_order_book_update(self, order_book_data: Dict):
        """处理摆盘数据更新"""
        symbol = order_book_data['symbol']
        
        # 分析大单情况
        large_bid_volume = sum(vol for price, vol in zip(order_book_data['bid_prices'], 
                                                        order_book_data['bid_volumes']) 
                             if vol > 100000)  # 大单阈值
        large_ask_volume = sum(vol for price, vol in zip(order_book_data['ask_prices'], 
                                                       order_book_data['ask_volumes']) 
                            if vol > 100000)
        
        print(f"{symbol} - 大单买盘: {large_bid_volume}, 大单卖盘: {large_ask_volume}")
    
    def generate_signal(self, kline_data: Dict) -> Optional[Dict]:
        """生成突破信号"""
        symbol = kline_data['symbol']
        current_price = kline_data['close']
        
        if symbol not in self.indicators:
            return None
            
        resistance = self.indicators[symbol].get('resistance')
        support = self.indicators[symbol].get('support')
        
        if resistance is None or support is None:
            return None
        
        # 向上突破阻力位
        if current_price > resistance:
            signal = {
                'symbol': symbol,
                'signal_type': 'BUY',
                'price': current_price,
                'reason': f"向上突破阻力位: {current_price:.2f} > {resistance:.2f}",
                'timestamp': datetime.now()
            }
            self.signals.append(signal)
            return signal
        
        # 向下跌破支撑位
        elif current_price < support:
            signal = {
                'symbol': symbol,
                'signal_type': 'SELL',
                'price': current_price,
                'reason': f"向下跌破支撑位: {current_price:.2f} < {support:.2f}",
                'timestamp': datetime.now()
            }
            self.signals.append(signal)
            return signal
        
        return None


class MarketMakingStrategy(BaseRealtimeStrategy):
    """做市策略 - 利用摆盘数据进行高频交易"""
    
    def __init__(self, watch_symbols: List[str], spread_threshold: float = 0.01):
        super().__init__("做市策略", watch_symbols)
        self.spread_threshold = spread_threshold
        self.order_book_snapshot = {}
        
    def on_kline_update(self, kline_data: Dict):
        """K线数据用于趋势判断"""
        symbol = kline_data['symbol']
        print(f"{symbol} - 最新价格: {kline_data['close']:.2f}")
    
    def on_order_book_update(self, order_book_data: Dict):
        """主要处理摆盘数据"""
        symbol = order_book_data['symbol']
        
        # 保存摆盘快照
        self.order_book_snapshot[symbol] = order_book_data
        
        # 计算买卖价差
        bid_price = order_book_data['bid_prices'][0] if order_book_data['bid_prices'] else 0
        ask_price = order_book_data['ask_prices'][0] if order_book_data['ask_prices'] else 0
        
        if bid_price > 0 and ask_price > 0:
            spread = (ask_price - bid_price) / bid_price  # 相对价差
            
            # 价差交易机会
            if spread > self.spread_threshold:
                print(f"{symbol} - 发现价差机会: {spread:.2%}")
    
    def generate_signal(self, kline_data: Dict) -> Optional[Dict]:
        """生成做市信号"""
        symbol = kline_data['symbol']
        
        if symbol not in self.order_book_snapshot:
            return None
            
        order_book = self.order_book_snapshot[symbol]
        
        # 简单的做市信号：当买卖价差较大时进行套利
        bid_price = order_book['bid_prices'][0] if order_book['bid_prices'] else 0
        ask_price = order_book['ask_prices'][0] if order_book['ask_prices'] else 0
        
        if bid_price > 0 and ask_price > 0:
            spread = (ask_price - bid_price) / bid_price
            
            if spread > self.spread_threshold:
                return {
                    'symbol': symbol,
                    'signal_type': 'ARBITRAGE',
                    'bid_price': bid_price,
                    'ask_price': ask_price,
                    'spread': spread,
                    'reason': f"价差套利机会: {spread:.2%}",
                    'timestamp': datetime.now()
                }
        
        return None


class MockRealtimeDataGenerator:
    """模拟实时数据生成器，用于演示"""
    
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.base_prices = {symbol: random.uniform(10, 100) for symbol in symbols}
        self.volatility = {symbol: random.uniform(0.01, 0.05) for symbol in symbols}
        
    def generate_kline_data(self, symbol: str) -> Dict:
        """生成模拟K线数据"""
        base_price = self.base_prices[symbol]
        vol = self.volatility[symbol]
        
        # 模拟价格波动
        price_change = random.uniform(-vol, vol) * base_price
        new_price = base_price + price_change
        
        # 生成K线数据
        open_price = base_price
        high_price = max(open_price, new_price) + random.uniform(0, vol * base_price)
        low_price = min(open_price, new_price) - random.uniform(0, vol * base_price)
        close_price = new_price
        volume = random.randint(10000, 1000000)
        
        # 更新基础价格
        self.base_prices[symbol] = close_price
        
        return {
            'symbol': symbol,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume,
            'timestamp': datetime.now(),
            'period': '1min'
        }
    
    def generate_order_book_data(self, symbol: str) -> Dict:
        """生成模拟摆盘数据"""
        current_price = self.base_prices[symbol]
        
        # 生成买卖盘口
        bid_prices = [current_price * (1 - i * 0.001) for i in range(5)]
        ask_prices = [current_price * (1 + i * 0.001) for i in range(5)]
        
        bid_volumes = [random.randint(100, 10000) for _ in range(5)]
        ask_volumes = [random.randint(100, 10000) for _ in range(5)]
        
        return {
            'symbol': symbol,
            'bid_prices': bid_prices,
            'ask_prices': ask_prices,
            'bid_volumes': bid_volumes,
            'ask_volumes': ask_volumes,
            'timestamp': datetime.now()
        }


class RealtimeTradingSystem:
    """实时交易系统"""
    
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.strategies = []
        self.is_running = False
        
        # 创建模拟数据生成器
        self.data_generator = MockRealtimeDataGenerator(symbols)
        
        # 初始化策略
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        """初始化交易策略"""
        # 移动平均线策略
        ma_strategy = MovingAverageStrategy(
            watch_symbols=self.symbols,
            fast_period=5,
            slow_period=20
        )
        
        # 突破策略
        breakout_strategy = BreakoutStrategy(
            watch_symbols=self.symbols,
            breakout_period=15
        )
        
        # 做市策略
        market_making_strategy = MarketMakingStrategy(
            watch_symbols=self.symbols,
            spread_threshold=0.02
        )
        
        self.strategies = [ma_strategy, breakout_strategy, market_making_strategy]
    
    async def start_trading(self):
        """启动交易系统"""
        self.is_running = True
        print("🚀 实时交易系统启动...")
        print(f"监控股票: {', '.join(self.symbols)}")
        print("-" * 60)
        
        # 模拟实时数据流
        iteration = 0
        while self.is_running and iteration < 50:  # 限制演示次数
            iteration += 1
            
            print(f"\n📊 第 {iteration} 轮数据更新:")
            
            # 为每个股票生成数据
            for symbol in self.symbols:
                # 生成K线数据
                kline_data = self.data_generator.generate_kline_data(symbol)
                
                # 生成摆盘数据
                order_book_data = self.data_generator.generate_order_book_data(symbol)
                
                # 分发数据给所有策略
                await self._distribute_data_to_strategies(kline_data, order_book_data)
                
                # 生成交易信号
                await self._generate_trading_signals(symbol, kline_data)
            
            # 等待一段时间模拟实时数据间隔
            await asyncio.sleep(2)
        
        print("\n✅ 交易演示完成")
        self._print_trading_summary()
    
    async def _distribute_data_to_strategies(self, kline_data: Dict, order_book_data: Dict):
        """分发数据给所有策略"""
        for strategy in self.strategies:
            # 更新K线数据
            strategy.on_kline_update(kline_data)
            
            # 更新摆盘数据
            strategy.on_order_book_update(order_book_data)
    
    async def _generate_trading_signals(self, symbol: str, kline_data: Dict):
        """生成交易信号"""
        for strategy in self.strategies:
            signal = strategy.generate_signal(kline_data)
            
            if signal:
                await self._execute_signal(strategy, signal)
    
    async def _execute_signal(self, strategy, signal: Dict):
        """执行交易信号"""
        symbol = signal['symbol']
        signal_type = signal['signal_type']
        price = signal.get('price', 0)
        reason = signal.get('reason', '')
        
        # 模拟交易执行
        if signal_type in ['BUY', 'SELL']:
            action = "买入" if signal_type == 'BUY' else "卖出"
            print(f"🎯 [{strategy.name}] {action}信号 - {symbol} @ {price:.2f}")
            print(f"   📝 原因: {reason}")
            
            # 这里可以添加实际的交易执行逻辑
            # 例如：调用交易API下单
            
        elif signal_type == 'ARBITRAGE':
            spread = signal.get('spread', 0)
            print(f"💎 [{strategy.name}] 套利机会 - {symbol}")
            print(f"   📊 价差: {spread:.2%}, 买价: {signal.get('bid_price', 0):.2f}, "
                  f"卖价: {signal.get('ask_price', 0):.2f}")
    
    def _print_trading_summary(self):
        """打印交易总结"""
        print("\n" + "="*60)
        print("📈 交易系统总结")
        print("="*60)
        
        total_signals = 0
        for strategy in self.strategies:
            signal_count = len(strategy.signals)
            total_signals += signal_count
            
            print(f"\n📊 {strategy.name}:")
            print(f"   生成信号数量: {signal_count}")
            
            if strategy.signals:
                # 统计信号类型
                buy_signals = [s for s in strategy.signals if s['signal_type'] == 'BUY']
                sell_signals = [s for s in strategy.signals if s['signal_type'] == 'SELL']
                arbitrage_signals = [s for s in strategy.signals if s['signal_type'] == 'ARBITRAGE']
                
                print(f"   买入信号: {len(buy_signals)}")
                print(f"   卖出信号: {len(sell_signals)}")
                if arbitrage_signals:
                    print(f"   套利信号: {len(arbitrage_signals)}")
        
        print(f"\n📋 总信号数量: {total_signals}")
    
    def stop_trading(self):
        """停止交易系统"""
        self.is_running = False
        print("🛑 交易系统停止")


async def main():
    """主函数 - 演示实时交易系统"""
    
    # 设置监控的股票
    symbols = ['HK.00700', 'HK.00939', 'HK.01299', 'HK.02318']
    
    # 创建交易系统
    trading_system = RealtimeTradingSystem(symbols)
    
    try:
        # 启动交易系统
        await trading_system.start_trading()
        
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断交易系统")
        trading_system.stop_trading()
    
    except Exception as e:
        print(f"\n❌ 交易系统错误: {e}")
        trading_system.stop_trading()


if __name__ == "__main__":
    print("🎯 Futu API实时交易系统演示")
    print("=" * 60)
    print("本演示展示如何将Futu API的实时推送数据用于交易策略")
    print("包含以下功能:")
    print("  • 实时K线数据处理")
    print("  • 实时摆盘数据分析") 
    print("  • 多种交易策略实现")
    print("  • 交易信号生成与执行")
    print("=" * 60)
    
    # 运行演示
    asyncio.run(main())