"""
测试获取HK.00700的实时K线数据
"""
import time
from datetime import datetime
from typing import Dict, List
from data.sources.futu_realtime import FutuRTProcessor
from utils.settings import settings

# 全局变量用于存储接收到的K线数据
received_kline_data = []
start_time = datetime.now()


def kline_data_handler(data: Dict):
    """
    处理接收到的K线数据
    
    Args:
        data: 标准化后的K线数据字典
    """
    if data['data_type'] == 'kline':
        print(f"\n[K线数据]")
        print(f"   股票代码: {data['code']}")
        print(f"   时间: {data['time_key']}")
        print(f"   开盘价: {data['open']}")
        print(f"   收盘价: {data['close']}")
        print(f"   最高价: {data['high']}")
        print(f"   最低价: {data['low']}")
        print(f"   成交量: {data['volume']}")
        print(f"   成交额: {data['turnover']}")
        print(f"   换手率: {data['turnover_rate']}")
        
        # 保存数据到全局列表
        received_kline_data.append(data)
        
        # 检查运行时间，超过30秒自动停止
        elapsed_time = (datetime.now() - start_time).total_seconds()
        if elapsed_time > 30:
            print(f"\n[提示] 运行时间超过30秒，准备停止...")
            return False
    return True


def main():
    """
    主函数 - 测试获取HK.00700的实时K线数据
    """
    print("=" * 60)
    print("测试获取HK.00700的实时K线数据")
    print("=" * 60)
    
    # 1. 准备配置
    futu_config = settings.data.futu
    print(f"[配置信息]:")
    print(f"   Futu Host: {futu_config['Futu_Host']}")
    print(f"   Futu Port: {futu_config['Futu_Port']}")
    print(f"   交易环境: {futu_config['Futu_TrdEnv']}")
    
    # 2. 初始化Futu实时数据处理器
    print("\n初始化Futu实时数据处理器...")
    try:
        rt_processor = FutuRTProcessor(futu_config)
        print("[成功] Futu实时数据处理器初始化成功")
    except Exception as e:
        print(f"[错误] 初始化失败: {e}")
        return
    
    # 3. 连接Futu API
    print("\n连接Futu API...")
    if not rt_processor.connect():
        print("[错误] 连接失败，退出测试")
        return
    
    # 4. 注册回调函数
    print("\n注册数据回调函数...")
    rt_processor.register_callback(kline_data_handler)
    print("[成功] 回调函数注册成功")
    
    # 5. 订阅HK.00700的K线数据
    print("\n订阅HK.00700的K线数据...")
    symbols = ['HK.00700']  # 腾讯控股
    data_types = ['kline']  # 只订阅K线数据
    
    if not rt_processor.subscribe_realtime_data(symbols, data_types):
        print("[错误] 订阅失败，退出测试")
        rt_processor.disconnect()
        return
    
    print("[成功] 订阅成功，等待接收实时数据...")
    print("[提示] 按Ctrl+C停止测试")
    
    # 6. 运行主循环，等待接收数据
    try:
        while (datetime.now() - start_time).total_seconds() < 30:
            time.sleep(1)
            # 每5秒打印一次状态
            if int((datetime.now() - start_time).total_seconds()) % 5 == 0:
                elapsed = int((datetime.now() - start_time).total_seconds())
                print(f"\n[运行中] ({elapsed}秒)")
                print(f"   已接收K线数据: {len(received_kline_data)}条")
    
    except KeyboardInterrupt:
        print("\n\n[提示] 用户中断测试")
    
    # 7. 断开连接
    print("\n断开Futu API连接...")
    rt_processor.disconnect()
    
    # 8. 打印测试总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"测试时间: {datetime.now() - start_time}")
    print(f"接收K线数据条数: {len(received_kline_data)}")
    
    if received_kline_data:
        print("\n数据概览:")
        for i, data in enumerate(received_kline_data[:5]):  # 只显示前5条
            print(f"\n第{i+1}条数据:")
            print(f"   时间: {data['time_key']}")
            print(f"   收盘价: {data['close']}")
            print(f"   成交量: {data['volume']}")
        
        if len(received_kline_data) > 5:
            print(f"\n... 省略 {len(received_kline_data) - 5} 条数据")
    else:
        print("\n[提示] 未接收到任何K线数据")
        print("可能的原因:")
        print("1. Futu OpenD未运行")
        print("2. 网络连接问题")
        print("3. 股票市场未开盘")
        print("4. API权限问题")
    
    print("\n[成功] 测试完成")


if __name__ == "__main__":
    main()
