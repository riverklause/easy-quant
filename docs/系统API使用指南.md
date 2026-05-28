# Easy-Quant API 使用指南

## 概述

本文档详细介绍了Easy-Quant量化交易系统的API使用方法，包括数据获取、指标计算、策略开发等核心功能。

## 快速开始

### 1. 环境配置

```python
# 导入必要的模块
from data.data_manager import DataManager
from indicators.base.registry import IndicatorRegistry
from strategy.strategy_manager import StrategyManager
from utils.settings import settings

# 初始化核心组件
data_manager = DataManager()
indicator_registry = IndicatorRegistry()
strategy_manager = StrategyManager()
```

### 2. 数据源连接

```python
# 连接所有数据源
data_manager.connect_all()

# 检查连接状态
health_status = data_manager.health_check()
print(f"数据源健康状态: {health_status}")
```

## 数据获取API

### 历史数据获取

```python
import asyncio

async def get_historical_data():
    # 获取单个股票历史数据
    df = await data_manager.get_historical_data(
        symbol="US.AAPL",
        start_date="2024-01-01",
        end_date="2024-12-31",
        data_source="yfinance",
        period="daily"
    )
    print(f"历史数据形状: {df.shape}")
    return df

# 运行异步函数
asyncio.run(get_historical_data())
```

### 批量数据获取

```python
async def get_batch_data():
    symbols = ["US.AAPL", "US.GOOG", "US.MSFT"]
    
    # 批量获取多个股票数据
    batch_data = await data_manager.get_batch_data(
        symbols=symbols,
        start_date="2024-01-01",
        end_date="2024-12-31",
        data_source="yfinance"
    )
    
    for symbol, data in batch_data.items():
        print(f"{symbol}: {data.shape}")
    
    return batch_data

asyncio.run(get_batch_data())
```

### 基本面数据获取

```python
async def get_fundamental_data():
    # 获取财务报表数据
    balance_sheet = await data_manager.get_financial_statements(
        symbol="US.AAPL",
        statement_type="balance",
        data_source="yfinance",
        period="annual"
    )
    
    # 获取财务指标数据
    financial_indicators = await data_manager.get_financial_indicators(
        symbol="US.AAPL",
        data_source="yfinance",
        period="annual"
    )
    
    print(f"资产负债表形状: {balance_sheet.shape}")
    print(f"财务指标: {list(financial_indicators.index)}")
    
    return balance_sheet, financial_indicators

asyncio.run(get_fundamental_data())
```

### 市场快照数据

```python
async def get_market_snapshot():
    symbols = ["US.AAPL", "HK.00700"]
    
    # 获取市场快照数据
    snapshot = await data_manager.get_market_snapshot(
        symbols=symbols,
        data_source="yfinance"
    )
    
    print(f"市场快照数据形状: {snapshot.shape}")
    print(f"包含字段: {list(snapshot.columns)}")
    
    return snapshot

asyncio.run(get_market_snapshot())
```

## Futu API 专用功能

### 复权因子和复权价格

```python
from data.sources.futu_client import FutuAPIClient
from futu import Market, SecurityType

# 创建Futu客户端
futu_client = FutuAPIClient({
    'Futu_Host': '127.0.0.1',
    'Futu_Port': 11111
})
futu_client.connect()

# 获取复权因子数据
async def get_rehab_factors():
    success, rehab_factors = await futu_client.get_rehab_factors('HK.00700')
    if success:
        print(f"复权因子: {rehab_factors.head()}")
    return rehab_factors

# 计算复权价格
async def calculate_adjusted_price():
    raw_price = 300.0
    # 前复权价格
    forward_price = await futu_client.get_adjusted_price(
        symbol='HK.00700',
        raw_price=raw_price,
        target_date='2024-06-01',
        adjust_type='forward'
    )
    # 后复权价格
    backward_price = await futu_client.get_adjusted_price(
        symbol='HK.00700',
        raw_price=raw_price,
        target_date='2024-06-01',
        adjust_type='backward'
    )
    print(f"原始: {raw_price}, 前复权: {forward_price}, 后复权: {backward_price}")

futu_client.disconnect()
```

### 股票基本信息获取

```python
from data.sources.futu_client import FutuAPIClient
from futu import Market, SecurityType

futu_client = FutuAPIClient({
    'Futu_Host': '127.0.0.1',
    'Futu_Port': 11111
})
futu_client.connect()

# 获取港股所有股票基本信息
success, hk_stocks = futu_client.get_stock_basicinfo(
    market=Market.HK,
    stock_type=SecurityType.STOCK
)
if success:
    hk_stocks.to_parquet('data/StockBasicInfo.parquet', index=False)
    print(f"港股数量: {len(hk_stocks)}")

# 获取美股基本信息
success, us_stocks = futu_client.get_stock_basicinfo(
    market=Market.US,
    stock_type=SecurityType.STOCK
)
if success:
    us_stocks.to_parquet('data/USStockBasicInfo.parquet', index=False)
    print(f"美股数量: {len(us_stocks)}")

futu_client.disconnect()
```

### 股票筛选

```python
from data.sources.futu_client import FutuAPIClient
from futu import Market

futu_client = FutuAPIClient({
    'Futu_Host': '127.0.0.1',
    'Futu_Port': 11111
})
futu_client.connect()

# 筛选条件：市值>10亿，换手率>0.05%
success, filtered_list, name_dict = futu_client.get_basicfiltered_stocks(
    marketcode=Market.HK
)

if success:
    print(f"筛选出 {len(filtered_list)} 只股票")
    # 保存筛选结果
    filtered_df = pd.DataFrame({
        'code': filtered_list,
        'name': [name_dict.get(c, '') for c in filtered_list]
    })
    filtered_df.to_parquet('data/StockBasicFiltered.parquet', index=False)

futu_client.disconnect()
```

## 指标计算API

### 技术指标计算

```python
from indicators.technical.trend.moving_average import MovingAverage
from indicators.technical.momentum.rsi import RSI

# 创建技术指标实例
sma = MovingAverage(name="SMA_20", period=20)
rsi = RSI(name="RSI_14", period=14)

# 计算指标
async def calculate_indicators():
    # 获取历史数据
    df = await data_manager.get_historical_data(
        symbol="US.AAPL",
        start_date="2024-01-01",
        end_date="2024-12-31",
        data_source="yfinance"
    )
    
    # 计算SMA
    sma_result = sma.calculate(df['close'])
    
    # 计算RSI
    rsi_result = rsi.calculate(df['close'])
    
    # 合并结果
    df['sma_20'] = sma_result
    df['rsi_14'] = rsi_result
    
    return df

asyncio.run(calculate_indicators())
```

### 基本面指标计算

```python
from indicators.fundamental.altman_z_score import AltmanZScore
from indicators.fundamental.dupont_analysis import DupontAnalysis

# 创建基本面指标实例
altman_z = AltmanZScore()
dupont = DupontAnalysis()

async def calculate_fundamental_indicators():
    # 获取财务数据
    balance_sheet, financial_indicators = await get_fundamental_data()
    
    # 计算Altman Z-Score
    z_score = altman_z.calculate(balance_sheet)
    
    # 计算杜邦分析
    dupont_result = dupont.calculate(balance_sheet)
    
    print(f"Altman Z-Score: {z_score}")
    print(f"杜邦分析结果: {dupont_result}")
    
    return z_score, dupont_result

asyncio.run(calculate_fundamental_indicators())
```

### 指标注册器使用

```python
# 注册指标
indicator_registry.register('sma_20', sma)
indicator_registry.register('rsi_14', rsi)
indicator_registry.register('altman_z', altman_z)

# 获取已注册指标
registered_indicators = indicator_registry.get_all()
print(f"已注册指标: {list(registered_indicators.keys())}")

# 批量计算指标
async def batch_calculate_indicators():
    df = await data_manager.get_historical_data(
        symbol="US.AAPL",
        start_date="2024-01-01",
        end_date="2024-12-31",
        data_source="yfinance"
    )
    
    results = {}
    for name, indicator in registered_indicators.items():
        if hasattr(indicator, 'calculate'):
            results[name] = indicator.calculate(df['close'])
    
    return results

asyncio.run(batch_calculate_indicators())
```

## 策略开发API

### 基础策略开发

```python
from strategy.base_strategy import BaseStrategy
from strategy.technical_strategy import TechnicalStrategy
from strategy.strategy_manager import StrategyManager

class MySimpleStrategy(TechnicalStrategy):
    """自定义简单策略（重构后版本）"""
    
    def __init__(self, name="MySimpleStrategy"):
        super().__init__(name=name)
        
        # 定义所需指标（重构后：策略只定义规则，不负责计算）
        self.add_required_indicator('sma_20')
        self.add_required_indicator('rsi_14')
        
        # 策略参数
        self.strategy_params = {
            'sma_period': 20,
            'rsi_period': 14,
            'oversold': 30,
            'overbought': 70
        }
    
    def define_rules(self, **kwargs):
        """定义策略规则（重构后：规则定义与执行分离）"""
        print(f"🔄 策略 '{self.name}' 规则定义完成")
        print(f"   - SMA周期: {self.strategy_params['sma_period']}日")
        print(f"   - RSI周期: {self.strategy_params['rsi_period']}日")
        print(f"   - RSI超卖阈值: {self.strategy_params['oversold']}")
        print(f"   - RSI超买阈值: {self.strategy_params['overbought']}")
    
    def generate_signals(self, indicators_data, **kwargs):
        """生成交易信号（重构后：接收指标数据，生成信号）"""
        signals = []
        
        # 获取指标数据（由StrategyExecutor提供）
        sma_data = indicators_data.get('sma_20')
        rsi_data = indicators_data.get('rsi_14')
        
        if sma_data is None or rsi_data is None:
            print(f"⚠️ 策略 '{self.name}' 缺少所需指标数据")
            return signals
        
        # 获取最新数据
        current_price = kwargs.get('current_price', 100)
        current_sma = sma_data.iloc[-1] if hasattr(sma_data, 'iloc') else sma_data
        current_rsi = rsi_data.iloc[-1] if hasattr(rsi_data, 'iloc') else rsi_data
        
        # 生成交易信号
        if current_price > current_sma and current_rsi < self.strategy_params['oversold']:
            # 买入信号
            signals.append({
                'action': 'BUY',
                'symbol': kwargs.get('symbol', 'default'),
                'price': current_price,
                'quantity': 100,
                'reason': f"价格突破SMA且RSI超卖: {current_rsi:.2f} < {self.strategy_params['oversold']}"
            })
        
        elif current_price < current_sma and current_rsi > self.strategy_params['overbought']:
            # 卖出信号
            signals.append({
                'action': 'SELL',
                'symbol': kwargs.get('symbol', 'default'),
                'price': current_price,
                'quantity': 100,
                'reason': f"价格跌破SMA且RSI超买: {current_rsi:.2f} > {self.strategy_params['overbought']}"
            })
        
        return signals

# 创建策略实例
my_strategy = MySimpleStrategy()
```

### 多因子策略开发

```python
from strategy.multi_factor.multi_factor_strategy import MultiFactorStrategy
from strategy.multi_factor.factor_combiner import FactorCombiner

class MyMultiFactorStrategy(MultiFactorStrategy):
    """自定义多因子策略"""
    
    def __init__(self, name="MyMultiFactorStrategy"):
        super().__init__(name=name)
        
        # 定义因子权重
        self.factor_weights = {
            'value': 0.4,      # 价值因子
            'growth': 0.3,     # 成长因子
            'momentum': 0.2,   # 动量因子
            'quality': 0.1     # 质量因子
        }
    
    async def calculate_factors(self, data):
        """计算各因子得分"""
        factors = {}
        
        # 价值因子（市盈率倒数）
        if 'pe_ratio' in data.columns:
            factors['value'] = 1 / data['pe_ratio']
        
        # 成长因子（营收增长率）
        if 'revenue_growth' in data.columns:
            factors['growth'] = data['revenue_growth']
        
        # 动量因子（价格动量）
        if 'close' in data.columns:
            factors['momentum'] = data['close'].pct_change(periods=20)
        
        # 质量因子（ROE）
        if 'roe' in data.columns:
            factors['quality'] = data['roe']
        
        return factors
    
    async def generate_signals(self, universe_data):
        """生成交易信号"""
        # 计算因子得分
        factor_scores = await self.calculate_factors(universe_data)
        
        # 组合因子得分
        combined_scores = FactorCombiner.combine_factors(
            factor_scores, 
            self.factor_weights
        )
        
        # 生成选股信号
        top_stocks = combined_scores.nlargest(10)  # 选择得分最高的10只股票
        
        for symbol, score in top_stocks.items():
            self.generate_signal(
                symbol=symbol,
                signal_type='BUY',
                weight=score / top_stocks.sum(),  # 按得分分配权重
                reason=f"多因子综合得分: {score:.4f}"
            )

# 创建多因子策略实例
multi_factor_strategy = MyMultiFactorStrategy()
```

### 策略管理（重构后版本）

```python
# 创建策略管理器（重构后：集成StrategyExecutor）
manager = StrategyManager()

# 注册策略（重构后：策略管理器负责策略存储和管理）
strategy_id = manager.register_strategy(my_strategy)
print(f"✅ 策略 '{my_strategy.name}' 注册成功，ID: {strategy_id}")

# 启动策略（重构后：策略管理器负责生命周期控制）
manager.start_strategy(strategy_id)
print(f"🔄 策略 '{strategy_id}' 启动成功")

# 生成交易信号（重构后：协调StrategyExecutor执行策略）
# 准备原始数据
import pandas as pd
import numpy as np

# 生成示例数据
dates = pd.date_range(start='2024-01-01', periods=100)
prices = 100 + np.cumsum(np.random.randn(100) * 2)
raw_data = pd.DataFrame({'close': prices}, index=dates)

# 生成信号（重构后：StrategyManager协调执行）
signals = manager.generate_signals(strategy_id, raw_data)
print(f"📈 策略 '{strategy_id}' 生成 {len(signals)} 个信号")

if signals:
    for i, signal in enumerate(signals[:3]):  # 显示前3个信号
        print(f"  信号{i+1}: {signal['action']} - {signal['reason']}")

# 获取策略信息（重构后：策略管理器提供统一接口）
strategy_info = manager.get_strategy_info(strategy_id)
print(f"ℹ️  策略信息:")
print(f"   名称: {strategy_info['name']}")
print(f"   运行状态: {strategy_info['is_running']}")
print(f"   创建时间: {strategy_info['created_at']}")

# 获取执行统计（重构后：通过executor获取统计信息）
execution_stats = manager.executor.get_execution_stats()
print(f"📊 执行统计:")
print(f"   总执行次数: {execution_stats['total_executions']}")
print(f"   成功执行: {execution_stats['successful_executions']}")
print(f"   失败执行: {execution_stats['failed_executions']}")

# 停止策略
manager.stop_strategy(strategy_id)
print(f"🛑 策略 '{strategy_id}' 已停止")

# 注销策略
manager.unregister_strategy(strategy_id)
print(f"🗑️  策略 '{strategy_id}' 已注销")
```

## 实时数据API

### 实时数据订阅

```python
# 注册回调函数（使用 DataManager 内置回调处理）
data_manager.register_callback('futu_RT', data_manager.on_realtime_data)

# 订阅股票实时数据
data_manager.subscribe_realtime_data(
    data_source='futu_RT',
    symbols=['HK.00700', 'US.AAPL'],
    data_types=['kline', 'quote', 'order_book', 'ticker', 'time_share']
)
```

### 从内存缓存获取实时数据

```python
# 获取特定股票的K线数据（返回 pd.DataFrame）
kline_data = data_manager.get_realtime_data('kline', symbol='HK.00700')

# 获取所有股票的报价数据
all_quotes = data_manager.get_realtime_data('quote')

# 返回值说明：get_realtime_data() 返回 pd.DataFrame
# 缓存结构优化：每只股票存储一个大DataFrame，通过 maxlen 自动限制行数
# 可直接用于指标计算：
kline_data['close'].rolling(5).mean()

# 获取最新实时数据
latest_data = data_manager.get_lastest_data(
    data_types=['quote', 'kline'],
    symbols=['HK.00700', 'HK.00941']
)

# 添加额外回调函数
def custom_callback(data):
    # 注意：data 现在是 pd.DataFrame 类型
    data_type = data['data_type'].iloc[0] if 'data_type' in data.columns else None
    symbol = data['code'].iloc[0] if 'code' in data.columns else None
    print(f"自定义处理: {data_type} - {symbol}")

data_manager.add_realtime_callback('futu_RT', custom_callback)
```

### 缓存配置

| 数据类型 | 最大缓存条数 |
|---------|-------------|
| kline | 1000条/股 |
| quote | 1000条/股 |
| order_book | 1000条/股 |
| time_share | 1000条/股 |
| broker | 100条/股 |
| ticker | 10000条/股 |

### 实时数据本地存储

```python
# 将实时数据保存到本地文件
success = data_manager.save_realtime_data_to_local(
    data_type='kline',
    symbol='HK.00700',
    trading_day='2026-04-14'
)

# 清理过期的实时数据（默认保留15天）
deleted_count = data_manager.cleanup_old_realtime_data(days=15)
```

### 实时策略执行

```python
class RealtimeStrategy(BaseStrategy):
    """实时交易策略"""
    
    def __init__(self, name="RealtimeStrategy"):
        super().__init__(name=name)
        self.last_price = {}
    
    async def on_realtime_data(self, data):
        """
        实时数据处理
        
        注意：data 参数现在是 pd.DataFrame 类型（单行），而非 dict
        """
        import pandas as pd
        
        if data is None or data.empty:
            return
        
        symbol = data['code'].iloc[0] if 'code' in data.columns else None
        data_type = data['data_type'].iloc[0] if 'data_type' in data.columns else None
        
        if data_type == 'quote':
            current_price = float(data['last_price'].iloc[0]) if 'last_price' in data.columns else None
            
            if symbol in self.last_price:
                price_change = current_price - self.last_price[symbol]
                price_change_pct = price_change / self.last_price[symbol] * 100
                
                # 价格变动超过2%时生成信号
                if abs(price_change_pct) > 2:
                    signal_type = 'BUY' if price_change_pct > 0 else 'SELL'
                    self.generate_signal(
                        symbol=symbol,
                        signal_type=signal_type,
                        price=current_price,
                        reason=f"价格变动: {price_change_pct:.2f}%"
                    )
            
            self.last_price[symbol] = current_price

# 创建实时策略
realtime_strategy = RealtimeStrategy()
strategy_manager.register_strategy('realtime', realtime_strategy)
```

## 数据存储API

### 本地数据存储

```python
from data.storage.local_storage import LocalStorageManager

# 创建存储管理器
storage_manager = LocalStorageManager()

async def save_and_load_data():
    # 获取数据
    df = await data_manager.get_historical_data(
        symbol="US.AAPL",
        start_date="2024-01-01",
        end_date="2024-12-31",
        data_source="yfinance"
    )
    
    # 保存数据
    save_success = storage_manager.save_data(
        data=df,
        symbol="US.AAPL",
        data_type="historical",
        start_date="2024-01-01",
        end_date="2024-12-31",
        source="yfinance"
    )
    
    if save_success:
        print("数据保存成功")
    
    # 加载数据
    loaded_data = storage_manager.load_data(
        symbol="US.AAPL",
        data_type="historical",
        start_date="2024-01-01",
        end_date="2024-12-31",
        source="yfinance"
    )
    
    print(f"加载的数据形状: {loaded_data.shape}")
    return loaded_data

asyncio.run(save_and_load_data())
```

## 配置管理API

### 系统配置

```python
from utils.settings import settings, update_settings

# 查看当前配置
print(f"数据目录: {settings.data.data_dir}")
print(f"缓存目录: {settings.data.cache_dir}")

# 更新配置
update_settings(
    data_path="/path/to/your/data",
    yfinance_proxy="http://your-proxy:port"
)

# 自定义配置
custom_config = {
    'futu': {
        'Futu_Host': '127.0.0.1',
        'Futu_Port': 11111,
        'Futu_TrdEnv': 'SIMULATE'
    },
    'yfinance': {
        'yfinance_proxy': 'http://127.0.0.1:5644'
    }
}

# 使用自定义配置初始化
data_manager_custom = DataManager(custom_config)
```

## 错误处理

### 异常处理示例

```python
import asyncio
from data.data_manager import DataManager

data_manager = DataManager()

async def safe_data_fetch():
    try:
        # 连接数据源
        data_manager.connect_all()
        
        # 获取数据
        df = await data_manager.get_historical_data(
            symbol="US.AAPL",
            start_date="2024-01-01",
            end_date="2024-12-31",
            data_source="yfinance"
        )
        
        return df
        
    except ConnectionError as e:
        print(f"连接错误: {e}")
        return None
    except Exception as e:
        print(f"数据获取错误: {e}")
        return None
    finally:
        # 确保断开连接
        data_manager.disconnect_all()

# 运行安全的数据获取
result = asyncio.run(safe_data_fetch())
if result is not None:
    print(f"成功获取数据: {result.shape}")
```

## 性能优化

### 批量操作优化

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def batch_optimized_operations():
    symbols = [f"US.AAPL", "US.GOOG", "US.MSFT", "US.AMZN", "US.NVDA"]
    
    # 使用线程池并行处理
    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = []
        for symbol in symbols:
            task = asyncio.get_event_loop().run_in_executor(
                executor,
                lambda s=symbol: asyncio.run(
                    data_manager.get_historical_data(
                        s, "2024-01-01", "2024-12-31", "yfinance"
                    )
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results

asyncio.run(batch_optimized_operations())
```

## 总结

本文档提供了Easy-Quant系统的完整API使用指南，涵盖了从数据获取到策略开发的各个环节。通过合理使用这些API，您可以快速构建和部署量化交易策略。

建议在实际使用前先运行测试用例，确保系统功能正常。如有问题，请参考项目文档或提交Issue。

## 模块状态总结

### ✅ 核心模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| 数据获取 | ✅ | 多数据源、历史/实时、基本面 |
| **Futu API** | ✅ | 复权因子、股票信息、股票筛选 |
| 指标计算 | ✅ | 15+技术指标、基本面指标 |
| 策略开发 | ✅ | 基础策略、多因子策略 |
| 策略管理 | ✅ | 统一管理、组合管理 |
| 实时数据 | ✅ | 内存缓存、最新数据、回调管理 |
| 数据存储 | ✅ | Parquet存储、过期管理 |
| 配置管理 | ✅ | 统一配置、动态更新 |

---

**版本**: 1.2.0
**更新日期**: 2026-04-15
**项目状态**: 核心功能已完成 ✅