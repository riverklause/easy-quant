# Easy-Quant 股票量化交易系统

一个基于Python的股票量化交易系统，支持多数据源、实时数据获取、策略回测和自动交易。

## 项目结构

```
easy-quant/
├── data/                    # 数据获取模块
│   ├── __init__.py
│   ├── base_client.py      # 数据源客户端基类
│   ├── data_manager.py     # 数据管理器
│   ├── config.py           # 数据配置
│   └── sources/            # 数据源实现
│       ├── __init__.py
│       ├── futu_client.py  # Futu数据源
│       └── yfinance_client.py # yfinance数据源
├── tests/                   # 测试文件
│   ├── __init__.py
│   └── test_data_manager.py
├── examples/               # 使用示例
│   └── data_example.py
├── utils/                  # 工具模块
│   └── settings.py         # 系统配置
├── requirements.txt        # 依赖管理
└── README.md
```

## 数据获取模块

### 功能特性

- **多数据源支持**: 支持Futu API和yfinance数据源
- **自动数据源选择**: 根据股票代码自动选择最优数据源
- **异步数据获取**: 基于asyncio的异步数据获取
- **统一数据格式**: 标准化不同数据源的数据格式
- **健康检查**: 实时监控数据源连接状态
- **批量操作**: 支持批量获取多个股票数据

### 快速开始

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **基本使用**
```python
import asyncio
from data.data_manager import DataManager
from data.config import get_data_config

async def main():
    # 创建数据管理器
    config = get_data_config()
    data_manager = DataManager(config)
    
    # 连接数据源
    await data_manager.connect_all()
    
    # 获取历史数据
    df = await data_manager.get_historical_data(
        symbol='00700.HK',
        start_date='2023-01-01',
        end_date='2023-01-31',
        period='daily'
    )
    
    # 获取实时数据
    real_time = await data_manager.get_real_time_data('AAPL')
    
    # 断开连接
    await data_manager.disconnect_all()

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
    'yfinance': {
        'yf_proxy': 'http://proxy.example.com:8080',
    }
}
data_manager = DataManager(custom_config)
```

### 支持的股票市场

- **港股**: 以 `.HK` 结尾的代码，如 `00700.HK`
- **A股**: 以 `.SS` 或 `.SZ` 结尾的代码，如 `000001.SZ`
- **美股**: 直接使用股票代码，如 `AAPL`

### 数据周期支持

- **分钟线**: 1min, 5min, 15min, 30min, 60min
- **日线**: daily
- **周线**: weekly
- **月线**: monthly

### 测试

运行测试用例：
```bash
pytest tests/test_data_manager.py -v
```

### 示例

查看完整使用示例：
```bash
python examples/data_example.py
```

## 📊 开发计划

### 第一阶段：数据获取模块（已完成 ✅）
- [x] 多数据源支持架构设计（FutuAPI + yfinance）
- [x] Parquet数据存储管理器实现
- [x] 复权数据处理方案
- [x] 数据缓存与增量更新机制
- [x] 港股美股A股多市场支持
- [x] 股票代码格式转换工具

#### 第一阶段详细完成情况

**✅ YFinanceClient - 已完成并测试验证**
- **代码格式转换**：支持美股/港股/深股/沪股多市场代码格式自动转换（如AAPL→US.AAPL、0700.HK→HK.00700等）
- **数据获取接口**：支持单个股票和批量股票数据获取
- **批量下载优化**：支持批量数据获取，提高下载效率
- **测试验证**：通过单元测试验证代码格式转换功能正常工作

**🔧 YFinanceClient技术实现亮点：**
- 使用symbol_utils.py模块进行统一的股票代码格式管理
- 在_process_dataframe方法中实现自动代码格式转换
- 支持批量下载失败时的逐个回退下载策略
- 完整的异常处理和日志记录

**🔄 FutuAPIClient - 基础功能已实现，需要继续改进**
- **基础数据获取**：支持历史数据和实时数据获取
- **多市场支持**：港股、美股、A股市场
- **异步接口**：提供异步数据获取接口
- **待改进功能**：代码格式转换、错误处理优化、测试覆盖

**📋 FutuAPIClient改进计划：**
- 添加股票代码格式转换功能
- 完善错误处理和回退机制
- 增加批量数据获取的并发优化
- 添加完整的测试用例覆盖

### 第二阶段：指标计算引擎（进行中 🔄）
- [ ] 技术指标计算模块
- [ ] 基本面指标计算模块
- [ ] 复合指标计算引擎
- [ ] 指标缓存与存储优化

### 第三阶段：策略引擎（待开始 ⏳）
- [ ] 条件判断引擎
- [ ] 交易规则引擎
- [ ] 策略模板库
- [ ] 实时策略执行

### 第四阶段：回测与可视化（待开始 ⏳）
- [ ] 回测引擎实现
- [ ] 策略性能分析
- [ ] 数据可视化界面
- [ ] 实时监控面板

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

MIT License