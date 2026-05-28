"""
测试获取HK.00700的实时K线数据 - 版本2
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
        
        # 检查运行时间，超过60秒自动停止
        elapsed_time = (datetime.now() - start_time).total_seconds()
        if elapsed_time > 60:
            print(f"\n[提示] 运行时间超过60秒，准备停止...")
            return False
    return True


def main()