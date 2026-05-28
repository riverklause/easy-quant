"""
Futu数据处理器与策略模块集成演示
展示如何将简洁的数据处理器与专门的策略模块正确集成
"""
import time
import sys
import os
from typing import Dict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.sources.futu_realtime_clean import FutuCleanRealtimeProcessor
from strategy.realtime_strategy_manager import StrategyEventManager
from strategy.realtime_strategy_example import MovingAverageStrategy, BreakoutStrategy


def demo_strategy_integration():
    """演示数据处理器与策略模块的集成"""
    
    print("🚀 开始Futu数据处理器与策略模块集成演示")
    print("=" * 60)
    
    # 1. 创建数据处理器（专注于数据接收和标准化）
    print("1. 创建Futu数据处理器...")
    data_processor = FutuCleanRealtimeProcessor()
    
    # 2. 创建策略事件管理器（负责策略执行）
    print("2. 创建策略事件管理器...")
    strategy_manager = StrategyEventManager(data_processor)
    
    # 3. 创建策略实例
    print("3. 创建策略实例...")
    symbols = ['HK.00700', 'HK.00939']
    
    # 移动平均线策略
    ma_strategy = MovingAverageStrategy(
        watch_symbols=symbols,
        fast_period=5,
        slow_period=20
    )
    
    # 突破策略
    breakout_strategy = BreakoutStrategy(
        watch_symbols=symbols,
        breakout_period=20
    )
    
    # 4. 注册策略到策略管理器
    print("4. 注册策略到策略管理器...")
    strategy_manager.register_strategy("移动平均线策略", ma_strategy)
    strategy_manager.register_strategy("突破策略", breakout_strategy)
    
    # 5. 创建策略数据处理器（连接数据处理器和策略管理器）
    print("5. 创建策略数据处理器...")
    
    def strategy_data_handler(data: Dict):
        """策略数据处理器 - 连接数据处理器和策略管理器"""
        data_type = data.get('data_type')
        symbol = data.get('symbol')
        
        if data_type == 'kline':
            # 为每个策略创建K线数据处理器
            for strategy_name in strategy_manager.strategies.keys():
                kline_handler = strategy_manager.create_kline_data_processor(symbol, strategy_name)
                kline_handler(data)
        
        elif data_type == 'order_book':
            # 为每个策略创建摆盘数据处理器
            for strategy_name in strategy_manager.strategies.keys():
                order_book_handler = strategy_manager.create_order_book_data_processor(symbol, strategy_name)
                order_book_handler(data)
        
        elif data_type == 'quote':
            # 报价数据可以用于策略的辅助分析
            print(f"💰 [{symbol}] 报价更新: {data.get('last_price', 'N/A')}")
    
    # 6. 将策略数据处理器添加到数据处理器
    data_processor.add_data_callback(strategy_data_handler)
    
    # 7. 连接Futu API并订阅数据
    print("6. 连接Futu API并订阅数据...")
    if data_processor.connect():
        if data_processor.subscribe_realtime_data(symbols):
            print("✅ 数据订阅成功")
            
            # 8. 启动策略执行
            print("7. 启动策略执行...")
            strategy_manager.start_strategy_execution()
            
            print("\n🎯 策略系统已启动，开始接收实时数据并执行策略...")
            print("-" * 60)
            
            # 9. 运行一段时间
            try:
                for i in range(30):  # 运行30秒
                    time.sleep(1)
                    
                    # 每5秒显示一次状态
                    if (i + 1) % 5 == 0:
                        print(f"⏰ 运行状态: {i+1}/30 秒")
                        
                        # 显示策略信号统计
                        ma_signals = strategy_manager.get_trading_signals("移动平均线策略")
                        breakout_signals = strategy_manager.get_trading_signals("突破策略")
                        
                        print(f"   移动平均线策略信号数: {len(ma_signals)}")
                        print(f"   突破策略信号数: {len(breakout_signals)}")
                        
                        # 显示最新信号
                        if ma_signals:
                            latest_signal = ma_signals[-1]
                            print(f"   最新移动平均线信号: {latest_signal.get('signal_type', 'N/A')} - {latest_signal.get('reason', 'N/A')}")
                        
                        if breakout_signals:
                            latest_signal = breakout_signals[-1]
                            print(f"   最新突破策略信号: {latest_signal.get('signal_type', 'N/A')} - {latest_signal.get('reason', 'N/A')}")
                        
                        print("-" * 40)
            
            except KeyboardInterrupt:
                print("\n🛑 用户中断")
            
            finally:
                # 10. 停止策略执行并断开连接
                print("\n8. 停止策略执行...")
                strategy_manager.stop_strategy_execution()
                
                print("9. 断开Futu连接...")
                data_processor.disconnect()
                
                # 11. 显示最终统计
                print("\n📊 最终统计:")
                print("=" * 40)
                
                total_signals = len(strategy_manager.get_trading_signals())
                ma_signals = len(strategy_manager.get_trading_signals("移动平均线策略"))
                breakout_signals = len(strategy_manager.get_trading_signals("突破策略"))
                
                print(f"总交易信号数: {total_signals}")
                print(f"移动平均线策略信号数: {ma_signals}")
                print(f"突破策略信号数: {breakout_signals}")
                
                # 显示所有信号详情
                if total_signals > 0:
                    print("\n📋 所有交易信号详情:")
                    for i, signal in enumerate(strategy_manager.get_trading_signals(), 1):
                        print(f"  {i}. [{signal.get('strategy', 'Unknown')}] {signal.get('symbol', 'Unknown')} - "
                              f"{signal.get('signal_type', 'Unknown')} - {signal.get('reason', 'No reason')}")
                
                print("\n✅ 演示结束")
        else:
            print("❌ 数据订阅失败")
    else:
        print("❌ 连接失败")


def demo_simple_integration():
    """简化版集成演示 - 只使用移动平均线策略"""
    
    print("🚀 开始简化版策略集成演示")
    print("=" * 50)
    
    # 创建数据处理器
    data_processor = FutuCleanRealtimeProcessor()
    
    # 创建策略管理器
    strategy_manager = StrategyEventManager(data_processor)
    
    # 创建并注册移动平均线策略
    symbols = ['HK.00700']
    ma_strategy = MovingAverageStrategy(symbols, fast_period=5, slow_period=10)
    strategy_manager.register_strategy("移动平均线策略", ma_strategy)
    
    # 创建策略数据处理器
    def simple_strategy_handler(data: Dict):
        """简化版策略数据处理器"""
        data_type = data.get('data_type')
        symbol = data.get('symbol')
        
        if data_type == 'kline':
            # 调用策略的K线更新方法
            kline_handler = strategy_manager.create_kline_data_processor(symbol, "移动平均线策略")
            kline_handler(data)
        
        elif data_type == 'order_book':
            # 调用策略的摆盘更新方法
            order_book_handler = strategy_manager.create_order_book_data_processor(symbol, "移动平均线策略")
            order_book_handler(data)
    
    # 添加回调
    data_processor.add_data_callback(simple_strategy_handler)
    
    # 连接并运行
    if data_processor.connect() and data_processor.subscribe_realtime_data(symbols):
        strategy_manager.start_strategy_execution()
        
        print("🎯 简化版策略系统已启动")
        
        try:
            for i in range(15):  # 运行15秒
                time.sleep(1)
                print(f"⏰ 运行中... {i+1}/15 秒")
        
        except KeyboardInterrupt:
            print("\n🛑 用户中断")
        
        finally:
            strategy_manager.stop_strategy_execution()
            data_processor.disconnect()
            
            signals = strategy_manager.get_trading_signals("移动平均线策略")
            print(f"\n📊 移动平均线策略产生 {len(signals)} 个交易信号")
            
            print("✅ 简化版演示结束")
    else:
        print("❌ 连接或订阅失败")


if __name__ == "__main__":
    # 用户可以选择运行完整版或简化版
    print("请选择演示模式:")
    print("1. 完整版策略集成演示 (30秒)")
    print("2. 简化版策略集成演示 (15秒)")
    
    choice = input("请输入选择 (1 或 2): ").strip()
    
    if choice == "1":
        demo_strategy_integration()
    elif choice == "2":
        demo_simple_integration()
    else:
        print("❌ 无效选择，默认运行简化版演示")
        demo_simple_integration()