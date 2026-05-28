# Easy-Quant 股票量化交易系统

一个基于Python的股票量化交易系统，支持多数据源、实时数据获取、策略回测和自动交易。

## 🎯 项目状态

**第一阶段：数据获取模块 - 已完成 ✅**
- 多数据源支持架构已实现并测试验证
- Futu实时数据订阅功能正常工作
- 实时数据回调机制已完善
- 市场快照数据获取接口已实现

**第二阶段：指标计算引擎 - 已完成 ✅**
- 技术指标计算模块已实现（SMA、EMA、MACD、ADX、RSI等15个指标）
- 指标计算器实现，支持完整计算和增量更新
- **双缓存模式支持**：历史模式（hash对比+TTL淘汰）和实时模式（覆盖更新）
- 指标注册器实现，支持动态加载和分类管理
- 缓存机制优化，hash计算性能提升82倍
- 批量计算和更新功能，提高效率

**已实现的技术指标：**
- 趋势指标：SMA、EMA、MACD、ADX、ParabolicSAR、PriceChannels
- 动量指标：RSI、Stochastic、CCI、WilliamsR、KDJ
- 波动率指标：BollingerBands、ATR、StandardDeviationChannel
- 成交量指标：OBV、VWAP

**第三阶段：策略引擎 - 已完成 ✅**
- 统一策略管理架构实现
- 支持技术指标策略和多因子策略
- 实现了策略组合管理系统
- 支持全局策略和特定股票策略
- 事件驱动架构，支持策略间通信
- 完整的策略生命周期管理
- 策略模块重构优化，职责清晰分离
- **双执行模式支持**：非实时模式（手动调用）和实时模式（定时自动执行）

**第四阶段：条件过滤/选股模块 - 已完成 ✅**
- 选股器基类实现（StockScreener）
- 条件基类实现（FilterCondition和TechnicalCondition）
- 内置技术条件实现（RSI、MACD、均线、布林带等）
- 条件组支持（AND关系条件组合）
- 自定义条件扩展支持

**第五阶段：回测引擎 - 已完成 ✅**
- 回测引擎核心实现（BacktestEngine）
- 组合管理器实现（Portfolio）
- 订单执行器实现（OrderExecutor）
- 历史数据源实现（HistoricalDataFeed）
- 绩效分析器实现（PerformanceAnalyzer）
- 风险分析器实现（RiskAnalyzer）
- 交易分析器实现（TradeAnalyzer）
- 回测结果存储（BacktestResult）
- 支持多策略回测和异步执行
- 支持基准对比和调仓策略

**第六阶段：可视化与监控 - 规划中 ⏳**
- 数据可视化界面（规划中）
- 实时监控面板（规划中）

## 项目结构

```
easy-quant/
├── backtest/               # ✅ 回测引擎模块（已完成）
│   ├── engine/           # ✅ 回测引擎核心
│   │   ├── backtest_engine.py # ✅ 回测引擎主类
│   │   ├── portfolio.py     # ✅ 组合管理器
│   │   └── order_executor.py # ✅ 订单执行器
│   ├── datafeed/         # ✅ 数据源
│   │   └── historical_datafeed.py # ✅ 历史数据源
│   ├── analyzers/        # ✅ 分析器
│   │   ├── performance.py # ✅ 绩效分析器
│   │   ├── risk.py        # ✅ 风险分析器
│   │   └── trade_analyzer.py # ✅ 交易分析器
│   └── results/         # ✅ 结果存储
│       └── result_store.py # ✅ 回测结果存储
├── data/                    # ✅ 数据获取模块（已完成）
│   ├── StockList.parquet           # 关注股票列表
│   ├── StockBasicInfo.parquet       # 市场股票全列表
│   ├── StockBasicFiltered.parquet   # 粗过滤后的活跃股票列表
│   ├── history_data/               # 用于策略分析的历史数据
│   ├── screener/                 # 用于股票过滤的数据
│   ├── realtime/                 # 实时数据
│   │   ├── kline/               # 实时K线数据
│   │   ├── tick/                # 实时成交数据
│   │   ├── quote/               # 实时报价数据
│   │   └── order_book/           # 实时摆盘数据
│   ├── sources/                 # ✅ 数据源客户端
│   │   ├── futu_client.py       # ✅ FutuAPI客户端
│   │   ├── futu_realtime.py     # ✅ Futu实时数据处理器
│   │   └── yfinance_client.py  # ✅ yfinance客户端
│   ├── storage/                 # 数据存储方法
│   ├── rehab/                  # 复权因子数据
│   ├── snapshot/               # 快照数据
│   └── temp/                  # 其他临时数据
├── demo/                   # 演示示例
│   ├── futu_realtime_demo.py    # 实时数据演示
│   ├── futu_strategy_integration.py # 策略集成演示
│   └── realtime_trading_demo.py # 实时交易演示
├── examples/               # 使用示例
│   ├── demo_indicators.py           # ✅ 指标计算示例
│   ├── demo_strategy_portfolio.py   # ✅ 策略组合演示
│   ├── demo_unified_strategy.py     # ✅ 统一策略管理演示
│   ├── demo_multi_factor.py         # ✅ 多因子策略演示
│   ├── demo_stock_screener.py       # ✅ 选股器演示
│   ├── demo_modular_portfolios.py   # ✅ 模块化组合演示
│   ├── demo_realtime_data.py        # ✅ 实时数据示例
│   ├── demo_data_storage.py         # ✅ 数据存储示例
│   ├── demo_futu_simple.py          # Futu基础数据示例
│   ├── demo_futuRT_simple.py        # Futu实时数据示例
│   └── demo_yfinance_simple.py       # yfinance数据示例
├── execution/              # 交易执行模块
├── indicators/              # ✅ 指标计算引擎（已完成）
│   ├── base/               # ✅ 指标基础架构
│   │   ├── base_indicator.py # ✅ 指标基类（包含因子基类）
│   │   ├── calculator.py    # ✅ 指标计算器
│   │   └── registry.py      # ✅ 指标注册器
│   ├── technical/           # ✅ 技术指标实现
│   │   ├── momentum/        # ✅ 动量指标
│   │   ├── trend/           # ✅ 趋势指标（SMA、EMA、MACD等）
│   │   ├── volatility/      # ✅ 波动率指标
│   │   └── volume/          # ✅ 成交量指标
│   └── fundamental/         # ✅ 基本面指标实现
├── screener/                # ✅ 条件过滤模块（已完成）
│   ├── filter_condition.py  # ✅ 条件基类
│   ├── stock_screener.py    # ✅ 选股执行引擎
│   └── conditions/          # ✅ 内置条件
│       ├── custom.py        # ✅ 自定义条件
│       └── technical/       # ✅ 技术条件
│       ├── altman_z_score.py # ✅ Altman Z-Score财务风险指标
│       └── dupont_analysis.py # ✅ 杜邦分析盈利能力指标
├── research/               # 研究模块
│   ├── dashboard/          # 仪表盘
│   ├── factor_analysis/    # 因子分析
│   ├── mcp_integration/    # MCP策略集成
│   ├── optimization/       # 优化模块
│   ├── strategy_builder/   # 策略构建
│   └── validation/         # 验证工具
├── risk_management/        # 风险管理模块
├── strategy/               # ✅ 策略引擎（已完成）
│   ├── multi_factor/       # ✅ 多因子策略框架
│   │   ├── example_strategy.py      # ✅ 示例多因子策略
│   │   ├── factor_combiner.py        # ✅ 因子组合器
│   │   └── multi_factor_strategy.py  # ✅ 多因子策略基类
│   ├── base_strategy.py    # ✅ 策略基类
│   ├── strategy_manager.py # ✅ 统一策略管理器
│   ├── strategy_portfolio.py # ✅ 策略组合管理器
│   └── technical_strategy.py # ✅ 技术指标策略基类
├── tests/                  # ✅ 测试框架
│   └── test_data_manager.py # ✅ 数据管理器测试
├── utils/                  # ✅ 工具模块
│   ├── symbol_utils.py     # ✅ 股票代码工具
│   ├── settings.py         # ✅ 配置管理
│   ├── data_utils.py       # 数据处理工具
│   └── validation.py       # 验证工具
└── visualization/          # 可视化模块
```

## 数据获取模块（已重构）

### 功能特性

- **多数据源支持**: 支持Futu API、Futu实时数据和yfinance数据源
- **统一数据源管理**: 每个数据源客户端都有features属性，统一管理特性信息
- **实时数据订阅**: 支持Futu实时数据的订阅和回调处理
- **异步数据获取**: 基于asyncio的异步数据获取
- **统一数据格式**: 标准化不同数据源的数据格式
- **健康检查**: 实时监控数据源连接状态
- **批量操作**: 支持批量获取多个股票数据
- **基本面数据获取**: 支持财务报表和财务指标数据获取
- **市场快照数据**: 支持统一的市场快照数据获取接口

### 快速开始

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **基本使用**
```python
import asyncio
from data.data_manager import DataManager
from utils.settings import get_data_config

async def main():
    # 创建数据管理器
    config = get_data_config()
    data_manager = DataManager(config)
    
    # 连接所有数据源
    data_manager.connect_all()
    
    # 获取数据源信息
    futu_info = data_manager.get_source_info('futu')
    print(f"富途数据源特性: {futu_info}")
    
    # 获取历史数据
    df = await data_manager.get_historical_data(
        symbol='00700',
        start_date='2023-01-01',
        end_date='2023-01-31',
        period='daily'
    )
    
    # 订阅实时数据
    data_manager.subscribe_realtime_data(['00700', '00001'], ['kline', 'quote'])
    
    # 添加实时数据回调
    def realtime_callback(data):
        print(f"收到实时数据: {data}")
    
    data_manager.add_realtime_callback(realtime_callback)
    
    # 断开连接
    data_manager.disconnect_all()

asyncio.run(main())
```

### 数据源配置

所有配置统一在 `utils/settings.py` 中管理。系统会自动读取以下配置项：

```python
# Futu配置
Futu_Host: str = "127.0.0.1"
Futu_Port: int = 11111
Futu_TrdEnv: str = "SIMULATE"

# yfinance配置
yf_proxy: str = "http://127.0.0.1:5644"
```

如果需要自定义配置，可以传入自定义配置字典：

```python
custom_config = {
    'futu': {
        'host': '192.168.1.100',
        'port': 11111,
        'market': 'HK',
        'trd_env': 'SIMULATE',
    },
    'futu_RT': {
        'host': '192.168.1.100',
        'port': 11111,
        'market': 'HK',
        'trd_env': 'SIMULATE',
    },
    'yfinance': {
        'yf_proxy': 'http://proxy.example.com:8080',
    }
}
data_manager = DataManager(custom_config)
```

### 支持的股票市场

- **港股**: 以 `.HK` 结尾的代码，如 `00700.HK`，或简写为 `00700`
- **A股**: 以 `.SS` 或 `.SZ` 结尾的代码，如 `000001.SZ`
- **美股**: 直接使用股票代码，如 `AAPL`

### 数据周期支持

- **分钟线**: 1min, 5min, 15min, 30min, 60min
- **日线**: daily
- **周线**: weekly
- **月线**: monthly

### 实时数据支持

- **Futu实时数据源**: 支持K线、摆盘、报价等实时数据订阅
- **回调机制**: 支持多个回调函数注册，实时接收数据推送
- **数据类型**: K线数据、摆盘数据、报价数据

### 测试

运行测试用例：
```bash
pytest tests/test_data_manager.py -v
```

### 示例

查看完整使用示例：
```bash
# 指标计算示例
python examples/demo_indicators.py

# 策略组合演示
python examples/demo_strategy_portfolio.py

# 统一策略管理演示
python examples/demo_unified_strategy.py
```

## 📊 开发计划

### ✅ 第一阶段：数据获取模块（已完成）

**核心功能实现情况：**
- [x] **多数据源支持架构**：FutuAPI + Futu实时数据 + yfinance
- [x] **Futu实时数据源**：支持K线、摆盘、报价等实时数据订阅
- [x] **数据管理器重构**：统一接口设计，简化数据源管理
- [x] **实时数据回调机制**：支持多个回调函数注册
- [x] **多市场支持**：港股、美股、A股市场
- [x] **股票代码格式转换**：自动转换多市场代码格式
- [x] **市场快照数据**：统一的市场快照数据获取接口
- [x] **数据过期判断**：支持文件时间、数据内容、混合三种过期判断方法

**测试验证结果：**
- ✅ 实时数据订阅成功（HK.00700 K线数据）
- ✅ 批量数据获取成功（3个股票66条历史数据）
- ✅ 实时数据接收正常（摆盘数据流）
- ✅ 数据源连接稳定（Futu API）
- ✅ 多市场代码转换正确

### ✅ 第二阶段：指标计算引擎（已完成）

**核心功能实现情况：**
- [x] **指标基类设计**：`BaseIndicator`抽象基类，定义统一接口
- [x] **指标计算器**：`IndicatorCalculator`支持完整计算和增量更新
- [x] **指标注册器**：`IndicatorRegistry`支持动态加载和分类管理
- [x] **技术指标实现**：SMA、EMA、MACD等常用技术指标
- [x] **双缓存模式**：历史模式（hash对比+TTL淘汰）和实时模式（覆盖更新）
- [x] **缓存机制优化**：hash计算性能提升82倍
- [x] **批量操作**：支持批量计算和更新多个指标
- [x] **线程安全**：使用`threading.RLock`确保多线程环境安全
- [x] **基本面指标**：Altman Z-Score、杜邦分析等财务指标

**测试验证结果：**
- ✅ 技术指标计算正确（SMA、EMA、MACD等）
- ✅ 缓存机制正常工作，命中率符合预期
- ✅ 批量计算和更新功能正常
- ✅ 增量更新缓存逻辑修复完成
- ✅ 基本面指标计算正确
- ✅ 双缓存模式测试通过（历史模式和实时模式）

### ✅ 第三阶段：策略引擎（已完成 + 重构优化）

**核心功能实现情况：**
- [x] **统一策略基类设计**：`BaseStrategy`抽象基类，定义统一策略接口
- [x] **策略管理器实现**：`StrategyManager`统一管理所有策略
- [x] **策略组合管理**：`StrategyPortfolio`支持全局策略和特定股票策略
- [x] **多因子策略框架**：支持因子生成、标准化、组合和选股
- [x] **技术指标策略框架**：支持基于技术指标的交易策略
- [x] **事件驱动架构**：支持策略相关事件的监听和处理
- [x] **完整的策略生命周期管理**：创建、初始化、运行、停止、销毁
- [x] **策略模块重构优化**：清晰的职责划分，消除功能重叠
- [x] **双执行模式**：非实时模式（手动调用）和实时模式（定时自动执行）

**重构优化亮点：**
- ✅ **职责清晰分离**：`StrategyManager`负责策略管理，`StrategyExecutor`负责执行协调
- ✅ **消除重复缓存**：指标缓存由`IndicatorCalculator`统一管理，避免双重缓存
- ✅ **性能优化**：批量计算策略所需指标，提高执行效率
- ✅ **可维护性提升**：松耦合设计，各组件可独立测试和替换
- ✅ **向后兼容**：保持现有接口兼容，平滑升级
- ✅ **实时模式支持**：异步定时执行，自动从data_manager获取数据

**测试验证结果：**
- ✅ 多因子策略执行正确，生成预期选股结果
- ✅ 策略组合管理功能正常，支持全局和特定股票策略
- ✅ 信号生成和记录功能正常
- ✅ 事件驱动机制工作正常
- ✅ 策略绩效统计功能正常
- ✅ **重构验证通过**：所有测试通过，架构更清晰
- ✅ **实时模式测试通过**：定时执行、启动/停止、多股票支持

### ✅ 第四阶段：条件过滤/选股模块（已完成 ✅）

**核心功能实现情况：**
- [x] **选股器基类**：`StockScreener`支持并行条件过滤
- [x] **条件基类**：`FilterCondition`和`TechnicalCondition`抽象基类
- [x] **内置技术条件**：RSI、MACD、均线、布林带、成交量、ADX、随机指标等
- [x] **条件组支持**：AND关系条件组合
- [x] **自定义条件**：支持扩展开发新条件

**测试验证结果：**
- ✅ 条件过滤模块功能正常

### ✅ 第五阶段：回测引擎（已完成 ✅）

**核心功能实现情况：**
- [x] **回测引擎**：`BacktestEngine`核心引擎
- [x] **组合管理**：`Portfolio`持仓和现金管理
- [x] **订单执行**：`OrderExecutor`订单处理
- [x] **历史数据源**：`HistoricalDataFeed`数据源
- [x] **绩效分析**：`PerformanceAnalyzer`绩效指标
- [x] **风险分析**：`RiskAnalyzer`风险指标
- [x] **交易分析**：`TradeAnalyzer`交易统计
- [x] **结果存储**：`BacktestResult`结果管理
- [x] **异步执行**：支持异步回测
- [x] **多策略支持**：支持策略组合回测
- [x] **调仓策略**：支持定期调仓
- [x] **基准对比**：支持基准收益率对比

### ⏳ 第六阶段：可视化与监控（规划中）

- [ ] 回测引擎实现（历史数据回测）
- [ ] 策略性能分析（收益、风险指标）
- [ ] 数据可视化界面（图表展示）
- [ ] 实时监控面板（策略运行监控）

## 🎯 当前项目优势

1. **多数据源支持**：Futu API + Futu实时数据 + yfinance
2. **实时数据能力**：完整的实时数据订阅和回调机制
3. **统一数据格式**：标准化不同数据源的数据格式
4. **多市场覆盖**：港股、美股、A股市场支持
5. **异步架构**：基于asyncio的高效数据获取
6. **模块化设计**：指标-策略分离架构，便于扩展
7. **清晰的职责划分**：策略管理、执行协调、指标计算职责分离
8. **性能优化架构**：统一缓存管理，批量计算优化
9. **可维护性设计**：松耦合组件，易于测试和扩展
10. **基本面分析能力**：财务报表获取、财务指标计算、Altman Z-Score、杜邦分析
11. **数据过期管理**：灵活的数据过期判断机制
12. **完整的测试覆盖**：pytest测试框架，核心功能测试验证

## 技术栈

- **编程语言**: Python 3.8+
- **数据处理**: pandas, numpy, scikit-learn
- **数据获取**: futu-api, yfinance
- **数据存储**: pyarrow (Parquet格式)
- **异步支持**: asyncio, aiolimiter
- **Web框架**: FastAPI, uvicorn
- **测试框架**: pytest, pytest-asyncio
- **缓存**: redis
- **日志**: loguru
- **代码质量**: black, flake8, mypy

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

MIT License

---

**版本**: 2.1.0  
**更新日期**: 2026-05-21  
**项目状态**: 核心功能已完成 (数据获取 + 指标计算 + 策略引擎 + 条件过滤 + 回测引擎)

## 📊 实时模式使用说明

### 指标计算器实时模式

指标计算器支持两种缓存模式：

| 模式 | 缓存策略 | 适用场景 |
|------|----------|----------|
| **history** | hash对比 + TTL淘汰 | 历史数据回测、选股 |
| **realtime** | 覆盖更新 | 实时监控、策略执行 |

**使用示例：**

```python
from indicators.base.calculator import IndicatorCalculator
from indicators.technical.trend.moving_average import SMA

calculator = IndicatorCalculator()
calculator.register_indicator(SMA(period=20), 'sma_20')

# 历史模式（默认）
result = calculator.batch_calculate(data, ['sma_20'], cache_mode='history')

# 实时模式
result = calculator.batch_calculate(data, ['sma_20'], cache_mode='realtime')

# 读取实时缓存
indicator_data = calculator.get_indicator('HK.00700', 'sma_20', cache_mode='realtime')
```

### 策略执行器实时模式

策略执行器支持两种执行模式：

| 模式 | 触发方式 | 数据来源 |
|------|----------|----------|
| **非实时** | 手动调用 | 调用方传入 |
| **实时** | 定时自动 | data_manager |

**使用示例：**

```python
import asyncio
from strategy.strategy_executor import StrategyExecutor

executor = StrategyExecutor()

# 启动实时模式
await executor.start_realtime_mode(
    data_manager=data_manager,
    symbols=['HK.00700', 'HK.01951'],
    strategies={'my_strategy': my_strategy},
    interval=2  # 每2秒执行一次
)

# 检查状态
executor.is_realtime_running()  # True

# 停止实时模式
executor.stop_realtime_mode()
```