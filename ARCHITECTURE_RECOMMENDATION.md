# 股票量化交易系统完整架构建议

## 📊 架构实现状态

### 当前进展（第一阶段：数据获取模块 - 已完成 ✅）

**✅ 已实现的核心功能：**

**YFinanceClient - 已完成并测试验证 ✅**
- **股票代码格式转换系统**：支持多市场代码格式自动转换
- **数据获取接口**：支持单个和批量股票数据获取
- **批量下载优化**：支持批量数据获取，提高下载效率
- **测试验证体系**：完整的单元测试覆盖

**YFinanceClient技术实现详情：**
- **代码格式转换**：在`_process_dataframe`方法中实现自动转换逻辑
- **多市场支持**：美股(AAPL→US.AAPL)、港股(0700.HK→HK.00700)、A股(000001.SZ→SZ.000001)
- **批量处理**：支持批量下载失败时的逐个回退下载
- **异常处理**：完整的错误处理和日志记录机制

**FutuAPIClient - 基础功能已实现，需要继续改进 🔄**
- **基础数据获取**：支持历史数据和实时数据获取
- **多市场支持**：港股、美股、A股市场
- **异步接口**：提供异步数据获取接口
- **待改进功能**：代码格式转换、错误处理优化、测试覆盖

**FutuAPIClient改进计划：**
- 添加股票代码格式转换功能
- 完善错误处理和回退机制
- 增加批量数据获取的并发优化
- 添加完整的测试用例覆盖

**📁 文件结构实现：**
```
easy-quant/
├── data/                    # 数据获取模块（已实现）
│   ├── clients/            # 数据源客户端
│   │   ├── futu_client.py  # FutuAPI客户端 ✅
│   │   └── yfinance_client.py # yfinance客户端 ✅
│   ├── managers/           # 数据管理器
│   │   └── data_manager.py # 数据管理器 ✅
│   └── utils/              # 工具函数
│       └── symbol_utils.py # 股票代码工具 ✅
└── tests/                  # 测试文件
    ├── test_code_conversion.py # 代码转换测试 ✅
    └── test_yfinance_conversion.py # 实际数据测试 ✅
```

## 1. 系统整体架构

### 1.1 核心模块划分（指标-策略分离架构）
```
easy-quant/
├── indicators/        # 指标计算模块（独立）
│   ├── technical/     # 技术指标计算
│   ├── fundamental/   # 高级基本面指标计算
│   ├── sentiment/     # 情绪指标计算
│   └── composite/     # 复合指标计算
├── strategy/          # 策略模块（纯判断逻辑）
│   ├── conditions/    # 条件判断引擎
│   ├── combinations/  # 指标组合管理
│   ├── rules/         # 交易规则引擎
│   └── templates/     # 策略模板库
├── data/              # 数据获取与Parquet存储模块
├── research/          # MCP策略研究模块
├── execution/         # 实时交易执行模块
├── risk_management/   # 风险管理模块
├── backtest/          # 回测引擎模块
├── visualization/     # 数据可视化模块
└── utils/             # 工具函数模块
```

### 1.2 技术栈选择（指标-策略分离架构）
- **编程语言**: Python 3.8+
- **数据获取**: futu-api-sdk, yfinance（多数据源支持，用户指定选择）
- **数据处理**: pandas, numpy, pyarrow（核心）
- **指标计算**: ta-lib, pandas-ta, IndicatorEngine（自定义指标引擎）
- **策略框架**: StrategyEngine（自定义策略引擎，基于条件判断）
- **存储格式**: Parquet（完全替代数据库）
- **可视化**: Dash, Plotly
- **缓存**: Redis（指标计算结果缓存）
- **任务调度**: Celery
- **Web框架**: FastAPI

## 2. 数据获取模块详细设计

### 2.1 简化多数据源架构
```python
class DataManager:
    """数据管理器 - 简化多数据源支持"""
    def __init__(self):
        # 数据源字典，支持动态添加新数据源
        self.data_sources = {
            'futu': FutuAPIClient(),
            'yfinance': YFinanceClient(),
            'tushare': TushareClient(),  # 可选数据源
            'akshare': AkshareClient()   # 可选数据源
        }
        
        self.storage_manager = ParquetStorageManager()
        
    async def get_historical_data(self, symbol, start_date, end_date, adjusted=False, data_source='futu'):
        """获取历史数据 - 必须指定数据源"""
        if data_source not in self.data_sources:
            raise ValueError(f"数据源 '{data_source}' 不存在")
             
        source = self.data_sources[data_source]
        
        if adjusted:
            # 实时获取复权数据
            return await source.get_adjusted_data(symbol, start_date, end_date)
        else:
            # 获取不复权数据
            return await source.get_data(symbol, start_date, end_date)
             
    async def get_real_time_data(self, symbol, adjusted=True, data_source='futu'):
        """获取实时数据 - 必须指定数据源"""
        if data_source not in self.data_sources:
            raise ValueError(f"数据源 '{data_source}' 不存在")
             
        source = self.data_sources[data_source]
        return await source.get_real_time_data(symbol, adjusted=adjusted)
         
    def add_data_source(self, source_name, source_client):
        """动态添加新数据源"""
        self.data_sources[source_name] = source_client
        print(f"已添加数据源: {source_name}")
         
    def remove_data_source(self, source_name):
        """移除数据源"""
        if source_name in self.data_sources:
            del self.data_sources[source_name]
            print(f"已移除数据源: {source_name}")
```

### 2.2 数据存储策略（完全基于Parquet）
- **历史数据**: 存储原始不复权数据（Parquet格式）
- **实时数据**: 直接获取复权数据（Parquet格式）
- **复权因子**: Parquet格式存储
- **技术指标**: 预计算并存储为Parquet
- **存储优势**: 列式存储、高效压缩、快速查询

### 2.5 指标存储策略（技术指标存储优化）

#### 存储介质选择
- **Redis**: 用于实时指标计算结果缓存，支持快速访问（内存缓存）
- **Parquet**: 用于历史指标数据持久化存储，支持离线分析（磁盘存储）

#### 技术指标存储必要性分析
**需要存储的技术指标类型：**
1. **计算成本高的指标**：如布林带、ATR、MACD等复杂计算
2. **历史回溯分析指标**：用于策略回测和性能分析
3. **实时监控指标**：用于实时策略执行和监控
4. **复合指标**：由多个基础指标组合而成

**不需要存储的指标：**
1. **简单移动平均**：计算简单，实时计算成本低
2. **基本价格指标**：如最高价、最低价等直接从价格数据获取

#### 分层存储策略设计
```python
class IndicatorStorageManager:
    """指标存储管理器 - 支持分层存储策略"""
    def __init__(self, redis_client, parquet_storage_path):
        self.redis = redis_client
        self.parquet_path = parquet_storage_path
        
        # 需要持久化存储的指标列表
        self.persistent_indicators = {
            'technical': ['bollinger_bands', 'atr', 'macd', 'rsi', 'stochastic'],
            'fundamental': ['altman_z', 'dupont_analysis', 'eva'],
            'composite': ['value_momentum_score', 'quality_score']
        }
        
        # 缓存过期时间配置
        self.cache_ttl = {
            'real_time': 300,      # 5分钟（实时数据）
            'historical': 3600,    # 1小时（历史数据）
            'fundamental': 86400   # 24小时（基本面数据）
        }
        
    async def store_indicator(self, symbol, indicator_type, indicator_name, data, period='daily'):
        """存储指标计算结果（分层存储）"""
        # 1. Redis缓存（所有指标）
        cache_key = f"indicator:{symbol}:{indicator_type}:{indicator_name}:{period}"
        ttl = self.cache_ttl.get(period, 3600)
        await self.redis.setex(cache_key, ttl, pickle.dumps(data))
        
        # 2. Parquet持久化存储（仅重要指标）
        if indicator_name in self.persistent_indicators.get(indicator_type, []):
            await self._store_to_parquet(symbol, indicator_type, indicator_name, data, period)
            
    async def get_indicator(self, symbol, indicator_type, indicator_name, period='daily'):
        """获取指标计算结果（缓存优先）"""
        # 1. 尝试从Redis缓存获取
        cache_key = f"indicator:{symbol}:{indicator_type}:{indicator_name}:{period}"
        cached_data = await self.redis.get(cache_key)
        if cached_data:
            return pickle.loads(cached_data)
            
        # 2. 从Parquet文件获取（如果支持持久化）
        if indicator_name in self.persistent_indicators.get(indicator_type, []):
            return await self._load_from_parquet(symbol, indicator_type, indicator_name, period)
            
        return None  # 指标需要实时计算
        
    async def _store_to_parquet(self, symbol, indicator_type, indicator_name, data, period):
        """存储到Parquet文件"""
        file_path = f"{self.parquet_path}/{indicator_type}/{symbol}/{indicator_name}_{period}.parquet"
        # 实现Parquet存储逻辑
        pass
        
    async def _load_from_parquet(self, symbol, indicator_type, indicator_name, period):
        """从Parquet文件加载"""
        file_path = f"{self.parquet_path}/{indicator_type}/{symbol}/{indicator_name}_{period}.parquet"
        # 实现Parquet加载逻辑
        pass
        
    def add_persistent_indicator(self, indicator_type, indicator_name):
        """动态添加需要持久化存储的指标"""
        if indicator_type not in self.persistent_indicators:
            self.persistent_indicators[indicator_type] = []
        if indicator_name not in self.persistent_indicators[indicator_type]:
            self.persistent_indicators[indicator_type].append(indicator_name)
```

### 2.3 Parquet数据管理器设计
```python
class ParquetDataManager:
    def __init__(self, base_path="data"):
        self.base_path = Path(base_path)
        self.partition_scheme = {
            'market': ['symbol', 'year', 'month'],
            'indicators': ['indicator_type', 'symbol', 'timeframe'],
            'factors': ['factor_type', 'symbol']
        }
        
    async def store_market_data(self, data, data_type, symbol, timestamp):
        """存储市场数据到Parquet"""
        # 确定分区路径
        partition_path = self._get_partition_path(data_type, symbol, timestamp)
        
        # 转换为DataFrame并优化
        df = pd.DataFrame(data)
        df = self._optimize_dataframe(df)
        
        # 写入Parquet（追加模式）
        file_path = partition_path / f"{timestamp.strftime('%Y%m%d')}.parquet"
        df.to_parquet(file_path, engine='pyarrow', compression='snappy', index=False)
        
    async def query_data(self, data_type, filters, columns=None):
        """查询Parquet数据"""
        # 构建查询路径
        query_paths = self._build_query_paths(data_type, filters)
        
        # 使用pandas直接读取Parquet文件进行查询
        import pandas as pd
        import pyarrow.parquet as pq
        
        # 读取所有匹配的Parquet文件
        data_frames = []
        for file_path in query_paths:
            if file_path.exists():
                # 使用pyarrow读取Parquet文件
                table = pq.read_table(file_path, columns=columns)
                df = table.to_pandas()
                
                # 应用过滤器
                if filters:
                    df = self._apply_filters(df, filters)
                
                data_frames.append(df)
        
        if not data_frames:
            return pd.DataFrame()
            
        # 合并所有数据
        result = pd.concat(data_frames, ignore_index=True)
        return result
        
    def _apply_filters(self, df, filters):
        """应用过滤器到DataFrame"""
        for column, condition in filters.items():
            if column in df.columns:
                if isinstance(condition, dict):
                    # 范围查询
                    if 'min' in condition:
                        df = df[df[column] >= condition['min']]
                    if 'max' in condition:
                        df = df[df[column] <= condition['max']]
                else:
                    # 精确匹配
                    df = df[df[column] == condition]
        return df
        
    def _get_partition_path(self, data_type, symbol, timestamp):
        """获取分区路径"""
        year = timestamp.year
        month = timestamp.month
        return self.base_path / data_type / symbol / str(year) / f"{month:02d}"
        
    def _optimize_dataframe(self, df):
        """优化DataFrame存储效率"""
        # 优化数据类型
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype('category')
        return df
```

### 2.4 数据目录结构（港股美股优化）
```
data/
├── raw/                    # 原始数据
│   ├── futu/              # FutuAPI原始数据
│   │   ├── hk/            # 港股原始数据
│   │   ├── us/            # 美股原始数据
│   │   └── cn/            # A股原始数据
│   └── yfinance/          # yfinance原始数据
│       ├── us/            # 美股原始数据
│       └── hk/            # 港股原始数据
├── adjusted/              # 复权后数据
│   ├── hk/                # 港股复权数据
│   │   ├── stocks/        # 个股数据
│   │   └── indices/       # 港股指数数据（恒生指数、国企指数等）
│   ├── us/                # 美股复权数据
│   │   ├── stocks/        # 个股数据
│   │   └── indices/       # 美股指数数据（标普500、纳斯达克等）
│   └── cn/                # A股复权数据
├── factors/               # 因子数据
    ├── technical/         # 技术因子
    ├── fundamental/       # 基本面因子
    └── composite/         # 复合因子
└── indicators/            # 指标计算结果存储
    ├── technical/         # 技术指标缓存
    ├── fundamental/       # 基本面指标缓存
    └── composite/         # 复合指标缓存
```

## 3. 复权数据处理方案

### 3.1 基于FutuAPI复权因子的架构
```python
class AdjustedPriceCalculator:
    def __init__(self):
        self.factor_cache = FactorCache()
        
    async def calculate_adjusted_price(self, raw_data, symbol, date):
        """计算复权价格"""
        factor = await self._get_adjustment_factor(symbol, date)
        return raw_data * factor
        
    async def _get_adjustment_factor(self, symbol, date):
        """获取复权因子"""
        if factor in self.factor_cache:
            return self.factor_cache.get(symbol, date)
        else:
            factor = await self.futu_client.get_adjustment_factor(symbol, date)
            self.factor_cache.set(symbol, date, factor)
            return factor
```

### 3.2 增量更新策略
```python
async def incremental_data_update(symbol, last_update_date):
    """增量数据更新"""
    # 获取新的复权因子
    new_factors = await futu_client.get_latest_factors(symbol, last_update_date)
    
    # 更新因子缓存
    factor_cache.update(new_factors)
    
    # 重新计算受影响的历史数据
    affected_dates = get_affected_dates(new_factors)
    await recalculate_adjusted_prices(symbol, affected_dates)
```

## 4. 指标计算与策略模块分离设计

### 4.1 新的模块架构（指标与策略分离）
```
easy-quant/
├── indicators/           # 指标计算模块（独立）
│   ├── technical/       # 技术指标
│   ├── fundamental/     # 基本面指标
│   ├── sentiment/       # 情绪指标
│   └── composite/       # 复合指标
├── strategy/            # 策略模块（纯判断逻辑）
│   ├── conditions/      # 条件判断
│   ├── combinations/   # 指标组合
│   ├── rules/          # 交易规则
│   └── templates/      # 策略模板
└── research/           # MCP策略研究模块
    ├── mcp_integration/
    ├── strategy_builder/
    └── validation/
```

### 4.2 指标计算模块设计
```python
class IndicatorEngine:
    """指标计算引擎 - 负责所有指标的计算和缓存"""
    def __init__(self):
        self.calculators = {
            'technical': TechnicalIndicatorCalculator(),
            'fundamental': FundamentalIndicatorCalculator(),
            'sentiment': SentimentIndicatorCalculator(),
            'composite': CompositeIndicatorCalculator()  # 新增复合指标计算器
        }
        self.cache = IndicatorCache()
        
    async def calculate_indicators(self, market_data, indicator_configs):
        """批量计算指标"""
        results = {}
        
        for config in indicator_configs:
            indicator_type = config['type']
            indicator_name = config['name']
            params = config.get('params', {})
            
            # 检查缓存
            cache_key = self._generate_cache_key(indicator_type, indicator_name, params, market_data)
            if cached_result := self.cache.get(cache_key):
                results[indicator_name] = cached_result
                continue
                
            # 计算指标
            calculator = self.calculators[indicator_type]
            result = await calculator.calculate(indicator_name, market_data, params)
            
            # 缓存结果
            self.cache.set(cache_key, result)
            results[indicator_name] = result
            
        return results
        
    def _generate_cache_key(self, indicator_type, name, params, data):
        """生成缓存键"""
        return f"{indicator_type}:{name}:{hash(str(params))}:{data.index[-1]}"

class FundamentalIndicatorCalculator:
    """基本面指标计算器 - 计算需要复杂处理的基本面指标"""
    async def calculate(self, indicator_name, fundamental_data, params):
        if indicator_name == 'altman_z_score':
            return self._calculate_altman_z_score(fundamental_data)
        elif indicator_name == 'dupont_analysis':
            return self._calculate_dupont_analysis(fundamental_data)
        elif indicator_name == 'economic_value_added':
            return self._calculate_eva(fundamental_data, params)
        elif indicator_name == 'quality_score':
            return self._calculate_quality_score(fundamental_data)
        elif indicator_name == 'financial_strength_index':
            return self._calculate_financial_strength_index(fundamental_data)
        # ... 其他需要计算的基本面指标
        
    def _calculate_altman_z_score(self, data):
        """计算Altman Z-score（破产风险预测模型）"""
        # Z = 1.2A + 1.4B + 3.3C + 0.6D + 1.0E
        # A = 营运资本/总资产
        # B = 留存收益/总资产  
        # C = 息税前利润/总资产
        # D = 市值/总负债
        # E = 销售收入/总资产
        working_capital = data['current_assets'] - data['current_liabilities']
        a = working_capital / data['total_assets']
        b = data['retained_earnings'] / data['total_assets']
        c = data['ebit'] / data['total_assets']
        d = data['market_cap'] / data['total_liabilities']
        e = data['revenue'] / data['total_assets']
        
        return 1.2*a + 1.4*b + 3.3*c + 0.6*d + 1.0*e
        
    def _calculate_dupont_analysis(self, data):
        """杜邦分析 - 分解ROE的驱动因素"""
        # ROE = 净利润率 × 资产周转率 × 权益乘数
        net_profit_margin = data['net_income'] / data['revenue']
        asset_turnover = data['revenue'] / data['total_assets']
        equity_multiplier = data['total_assets'] / data['shareholders_equity']
        
        return {
            'roe': data['net_income'] / data['shareholders_equity'],
            'net_profit_margin': net_profit_margin,
            'asset_turnover': asset_turnover,
            'equity_multiplier': equity_multiplier
        }
        
    def _calculate_eva(self, data, params):
        """计算经济增加值（EVA）"""
        # EVA = 税后净营业利润 - 资本成本
        # 资本成本 = 投入资本 × 加权平均资本成本(WACC)
        wacc = params.get('wacc', 0.08)  # 默认WACC为8%
        nopat = data['ebit'] * (1 - data['tax_rate'])
        invested_capital = data['total_assets'] - data['current_liabilities']
        capital_charge = invested_capital * wacc
        
        return nopat - capital_charge
        
    def _calculate_quality_score(self, data):
        """计算财务质量综合评分"""
        # 基于多个财务指标的综合评分
        scores = {
            'profitability': self._score_profitability(data),
            'liquidity': self._score_liquidity(data),
            'solvency': self._score_solvency(data),
            'efficiency': self._score_efficiency(data)
        }
        return sum(scores.values()) / len(scores)
        
    def _calculate_financial_strength_index(self, data):
        """计算财务强度指数"""
        # 综合多个财务比率
        current_ratio = data['current_assets'] / data['current_liabilities']
        debt_to_equity = data['total_liabilities'] / data['shareholders_equity']
        roe = data['net_income'] / data['shareholders_equity']
        
        # 标准化并加权
        return (current_ratio * 0.3 + (1/debt_to_equity) * 0.4 + roe * 0.3)

class CompositeIndicatorCalculator:

## 🚀 下一阶段开发计划

### 第二阶段：指标计算引擎（即将开始 🔄）

**📋 核心任务：**
- [ ] **技术指标计算模块**：实现常见技术指标（MACD、RSI、布林带等）
- [ ] **基本面指标计算模块**：实现财务指标计算（ROE、PE、PB等）
- [ ] **复合指标计算引擎**：支持多指标组合计算
- [ ] **指标缓存与存储优化**：Redis缓存 + Parquet持久化存储

**🔧 技术重点：**
- 指标计算引擎的模块化设计
- 实时计算与历史计算的分离
- 指标结果的缓存策略优化
- 与数据获取模块的无缝集成

**📊 预期成果：**
- 完整的指标计算API接口
- 高性能的指标计算引擎
- 可扩展的指标插件机制
- 完整的测试覆盖和性能基准

### 第三阶段：策略引擎（规划中 ⏳）

**📋 核心任务：**
- [ ] **条件判断引擎**：基于指标的条件判断系统
- [ ] **交易规则引擎**：交易信号生成和执行规则
- [ ] **策略模板库**：预置常用策略模板
- [ ] **实时策略执行**：支持实盘交易执行

**🔧 技术重点：**
- 策略与指标的完全分离架构
- 策略配置的灵活性和可扩展性
- 实时性能监控和风险控制
- 策略回测和优化的集成

### 第四阶段：回测与可视化（规划中 ⏳）

**📋 核心任务：**
- [ ] **回测引擎实现**：历史数据回测系统
- [ ] **策略性能分析**：收益、风险、夏普比率等指标
- [ ] **数据可视化界面**：基于Dash/Plotly的Web界面
- [ ] **实时监控面板**：实盘交易监控和报警

**🔧 技术重点：**
- 高性能回测引擎设计
- 可视化界面的用户体验优化
- 实时数据流处理
- 多策略并行执行支持

## 📈 项目里程碑

| 阶段 | 状态 | 预计完成时间 | 关键交付物 |
|------|------|--------------|------------|
| 第一阶段：数据获取 | ✅ 已完成 | 2024年12月 | 多数据源客户端、代码格式转换系统 |
| 第二阶段：指标计算 | 🔄 进行中 | 2025年1月 | 指标计算引擎、缓存系统 |
| 第三阶段：策略引擎 | ⏳ 规划中 | 2025年2月 | 策略框架、交易规则引擎 |
| 第四阶段：回测可视化 | ⏳ 规划中 | 2025年3月 | 回测系统、Web界面 |

## 🤝 贡献指南

欢迎对项目进行贡献！当前项目处于活跃开发阶段，主要贡献方向包括：
- 数据源客户端的优化和扩展
- 指标计算算法的实现和优化
- 策略模板的开发和测试
- 文档的完善和示例代码

请参考项目根目录的CONTRIBUTING.md文件了解详细的贡献流程。
    """复合指标计算器 - 结合技术面和基本面的复合指标"""
    async def calculate(self, indicator_name, technical_data, fundamental_data, params):
        if indicator_name == 'value_momentum_score':
            return self._calculate_value_momentum_score(technical_data, fundamental_data)
        elif indicator_name == 'quality_growth_score':
            return self._calculate_quality_growth_score(fundamental_data, params)
        elif indicator_name == 'risk_adjusted_return':
            return self._calculate_risk_adjusted_return(technical_data, fundamental_data)
        # ... 其他复合指标
        
    def _calculate_value_momentum_score(self, technical_data, fundamental_data):
        """价值-动量复合评分"""
        # 价值因子
        pe_ratio = fundamental_data['pe_ratio']
        pb_ratio = fundamental_data['pb_ratio']
        value_score = (1/pe_ratio + 1/pb_ratio) / 2
        
        # 动量因子
        momentum = technical_data['close'].pct_change(periods=20).iloc[-1]
        
        return value_score * 0.6 + momentum * 0.4
        
    def _calculate_quality_growth_score(self, fundamental_data, params):
        """质量-增长复合评分"""
        # 质量因子（ROE、毛利率等）
        quality_score = fundamental_data.get('quality_score', 0)
        
        # 增长因子（收入增长率、利润增长率）
        revenue_growth = fundamental_data['revenue_growth']
        profit_growth = fundamental_data['net_income_growth']
        growth_score = (revenue_growth + profit_growth) / 2
        
        return quality_score * 0.5 + growth_score * 0.5
```

### 4.3 策略模块设计（纯判断逻辑）
```python
class StrategyEngine:
    """策略引擎 - 负责指标组合和交易决策"""
    def __init__(self, indicator_engine):
        self.indicator_engine = indicator_engine
        self.condition_evaluator = ConditionEvaluator()
        self.rule_engine = RuleEngine()
        
    async def execute_strategy(self, strategy_config, market_data):
        """执行策略：计算指标 → 评估条件 → 生成信号"""
        # 1. 计算所需指标
        indicators = await self.indicator_engine.calculate_indicators(
            market_data, 
            strategy_config['indicators']
        )
        
        # 2. 评估交易条件
        conditions_met = await self.condition_evaluator.evaluate_conditions(
            strategy_config['conditions'], 
            indicators
        )
        
        # 3. 应用交易规则
        trading_signal = await self.rule_engine.generate_signal(
            conditions_met, 
            strategy_config['rules']
        )
        
        return {
            'signal': trading_signal,
            'indicators': indicators,
            'conditions_evaluation': conditions_met
        }

class ConditionEvaluator:
    """条件评估器 - 负责判断逻辑"""
    async def evaluate_conditions(self, conditions, indicators):
        """评估一组条件"""
        results = {}
        
        for condition_name, condition_config in conditions.items():
            condition_type = condition_config['type']
            
            if condition_type == 'comparison':
                results[condition_name] = self._evaluate_comparison(
                    condition_config, indicators
                )
            elif condition_type == 'crossover':
                results[condition_name] = self._evaluate_crossover(
                    condition_config, indicators
                )
            elif condition_type == 'threshold':
                results[condition_name] = self._evaluate_threshold(
                    condition_config, indicators
                )
                
        return results
        
    def _evaluate_comparison(self, condition, indicators):
        """比较条件：指标A > 指标B"""
        indicator_a = indicators[condition['indicator_a']]
        indicator_b = indicators[condition['indicator_b']]
        operator = condition['operator']  # '>', '<', '>=', '<=', '=='
        
        if operator == '>':
            return indicator_a > indicator_b
        elif operator == '<':
            return indicator_a < indicator_b
        # ... 其他比较操作符
        
    def _evaluate_crossover(self, condition, indicators):
        """交叉条件：指标A上穿/下穿指标B"""
        indicator_a = indicators[condition['indicator_a']]
        indicator_b = indicators[condition['indicator_b']]
        crossover_type = condition['type']  # 'up' 或 'down'
        
        if crossover_type == 'up':
            # 上穿：当前A>B且前一个A<=B
            return (indicator_a.iloc[-1] > indicator_b.iloc[-1]) and \
                   (indicator_a.iloc[-2] <= indicator_b.iloc[-2])
        else:  # down
            # 下穿：当前A<B且前一个A>=B
            return (indicator_a.iloc[-1] < indicator_b.iloc[-1]) and \
                   (indicator_a.iloc[-2] >= indicator_b.iloc[-2])
                   
    def _evaluate_threshold(self, condition, indicators):
        """阈值条件：指标值与阈值的比较"""
        indicator_value = indicators[condition['indicator']]
        threshold = condition['threshold']
        operator = condition['operator']  # '>', '<', '>=', '<=', '=='
        
        # 获取当前值（最新数据点）
        current_value = indicator_value.iloc[-1] if hasattr(indicator_value, 'iloc') else indicator_value
        
        if operator == '>':
            return current_value > threshold
        elif operator == '<':
            return current_value < threshold
        elif operator == '>=':
            return current_value >= threshold
        elif operator == '<=':
            return current_value <= threshold
        elif operator == '==':
            return current_value == threshold
        elif operator == '!=':
            return current_value != threshold
        else:
            raise ValueError(f"不支持的比较操作符: {operator}")

class RuleEngine:
    """规则引擎 - 负责信号生成和风险管理"""
    async def generate_signal(self, conditions_met, rules):
        """根据条件和规则生成交易信号"""
        # 1. 检查入场条件
        if not self._check_entry_conditions(conditions_met, rules['entry']):
            return 'HOLD'
            
        # 2. 检查出场条件
        if self._check_exit_conditions(conditions_met, rules['exit']):
            return 'SELL'
            
        # 3. 生成买入信号
        return 'BUY'
        
    def _check_entry_conditions(self, conditions, entry_rules):
        """检查入场条件"""
        # 示例：所有必需条件都必须满足
        required_conditions = entry_rules.get('required', [])
        for condition in required_conditions:
            if not conditions.get(condition, False):
                return False
        return True
```

### 4.4 MCP策略研究模块（基于指标-策略分离架构）

#### 4.4.1 新的研究架构
```python
class MCPStrategyResearchLab:
    """MCP策略研究实验室 - 基于指标-策略分离架构"""
    def __init__(self):
        self.indicator_engine = IndicatorEngine()
        self.strategy_engine = StrategyEngine(self.indicator_engine)
        self.mcp_client = MCPClient()
        
    async def research_pipeline(self, research_request):
        """完整的研究流程"""
        # 1. MCP生成指标组合建议
        indicator_suggestions = await self.mcp_client.generate_indicator_suggestions(
            research_request
        )
        
        # 2. 构建策略条件
        strategy_conditions = await self.build_strategy_conditions(indicator_suggestions)
        
        # 3. 策略验证与优化
        optimized_strategies = await self.optimize_strategies(strategy_conditions)
        
        return optimized_strategies
        
    async def build_strategy_conditions(self, indicator_suggestions):
        """基于MCP建议构建策略条件"""
        strategies = []
        
        for suggestion in indicator_suggestions:
            # 构建指标配置
            indicator_configs = self._parse_indicator_configs(suggestion)
            
            # 构建条件配置
            condition_configs = self._parse_condition_configs(suggestion)
            
            # 构建规则配置
            rule_configs = self._parse_rule_configs(suggestion)
            
            strategy = {
                'name': suggestion['strategy_name'],
                'indicators': indicator_configs,
                'conditions': condition_configs,
                'rules': rule_configs
            }
            strategies.append(strategy)
            
        return strategies
```

#### 4.4.2 策略配置示例（指标-策略分离）
```yaml
# 双均线策略配置（新架构）
strategy_name: "dual_moving_average_v2"

# 指标计算部分（独立）
indicators:
  sma_short:
    type: "technical"
    calculator: "sma"
    params: {period: 10}
    
  sma_long:
    type: "technical" 
    calculator: "sma"
    params: {period: 30}

# 策略判断部分（纯逻辑）
conditions:
  golden_cross:
    type: "crossover"
    indicator_a: "sma_short"
    indicator_b: "sma_long"
    direction: "up"
    
  death_cross:
    type: "crossover"
    indicator_a: "sma_short" 
    indicator_b: "sma_long"
    direction: "down"

# 交易规则部分
rules:
  entry:
    required: ["golden_cross"]
    optional: []
  exit:
    required: ["death_cross"]
    stop_loss: 0.05  # 5%止损
    take_profit: 0.10 # 10%止盈
```

## 5. 盘前筛选系统设计

### 5.1 多维度筛选规则
```python
class PreMarketScreener:
    def __init__(self):
        self.filters = {
            'technical': TechnicalFilter(),
            'fundamental': FundamentalFilter(),
            'liquidity': LiquidityFilter(),
            'volatility': VolatilityFilter()
        }
        
    async def screen_stocks(self, market_condition):
        """盘前股票筛选"""
        candidates = []
        for filter_name, filter_obj in self.filters.items():
            filtered = await filter_obj.apply(market_condition)
            candidates.extend(filtered)
            
        return self.rank_candidates(candidates)
```

## 6. 实时交易建议系统

### 6.1 信号生成引擎
```python
class TradingSignalGenerator:
    def __init__(self):
        self.strategy_pool = StrategyPool()
        self.risk_manager = RiskManager()
        
    async def generate_signals(self, market_data):
        """生成交易信号"""
        signals = []
        for strategy in self.strategy_pool.get_active_strategies():
            signal = await strategy.generate_signal(market_data)
            if signal and self.risk_manager.validate_signal(signal):
                signals.append(signal)
                
        return self.prioritize_signals(signals)
```

## 7. 回测引擎设计

### 7.1 事件驱动回测
```python
class EventDrivenBacktest:
    def __init__(self):
        self.event_engine = EventEngine()
        self.portfolio = Portfolio()
        self.performance_tracker = PerformanceTracker()
        
    async def run_backtest(self, strategy, historical_data):
        """运行回测"""
        for event in self.event_engine.generate_events(historical_data):
            # 处理市场事件
            await self.process_market_event(event, strategy)
            
            # 更新组合
            self.portfolio.update(event)
            
            # 记录性能
            self.performance_tracker.record(event)
            
        return self.performance_tracker.get_results()
```

## 8. 数据可视化模块（Dash + Plotly）

### 8.1 可视化架构
```python
class QuantVisualization:
    def __init__(self):
        self.dash_app = Dash(__name__)
        self.setup_layout()
        
    def setup_layout(self):
        """设置Dash应用布局"""
        self.dash_app.layout = html.Div([
            # 盘前筛选看板
            self.create_pre_market_dashboard(),
            
            # 实时监控看板
            self.create_real_time_dashboard(),
            
            # 策略研究看板
            self.create_research_dashboard(),
            
            # 回测结果看板
            self.create_backtest_dashboard()
        ])
```

### 8.2 核心可视化组件
- **盘前筛选看板**: 股票筛选结果、因子暴露分析
- **实时监控看板**: 持仓监控、市场行情、信号提醒
- **策略研究看板**: MCP研究进度、因子分析、策略对比
- **回测结果看板**: 收益曲线、风险指标、交易明细

### 8.3 交互式研究工具
```python
class InteractiveResearchTools:
    def create_parameter_sensitivity_plot(self, strategy, parameters):
        """创建参数敏感性分析图"""
        return plotly.express.line(
            data=self._calculate_sensitivity(strategy, parameters),
            x="parameter_value",
            y="performance",
            color="parameter_name",
            title="参数敏感性分析"
        )
```

## 9. 技术实施计划

### 9.1 开发阶段划分（Parquet为核心）
1. **第一阶段**: Parquet数据框架搭建（2-3周）
   - Parquet存储系统设计
   - 数据获取与Parquet写入
   - 分区策略和索引优化

2. **第二阶段**: 核心策略功能（3-4周）
   - Parquet数据读取优化
   - 盘前筛选系统（基于Parquet查询）
   - 实时信号生成

3. **第三阶段**: MCP研究模块（4-5周）
   - MCP客户端集成
   - 策略研究流水线（Parquet数据源）
   - 高级可视化

4. **第四阶段**: 系统优化与部署（2-3周）
   - Parquet性能优化
   - 缓存策略优化
   - 生产部署

### 9.2 依赖包清单（Parquet为核心）
```txt
# 核心Parquet依赖
pandas>=1.5.0
pyarrow>=10.0.0
fastparquet>=0.8.0

# 数据处理
numpy>=1.21.0
polars>=0.15.0  # 高性能DataFrame

# 数据获取
futu-api-sdk>=3.0.0
yfinance>=0.2.0

# 可视化
plotly>=5.0.0
dash>=2.0.0
dash-bootstrap-components>=1.0.0

# Web框架
fastapi>=0.95.0
uvicorn>=0.21.0

# 任务调度和缓存
celery>=5.3.0
redis>=4.5.0

# 可选：Parquet工具
duckdb>=0.6.0  # 用于Parquet查询优化
```

## 10. 关键技术挑战与解决方案（Parquet为核心）

### 10.1 Parquet存储优化挑战
- **问题**: 大数据量下的Parquet读写性能
- **解决方案**: 
  - 分区策略优化（按时间、股票代码分区）
  - 列式存储压缩优化
  - 预聚合数据减少文件大小

### 10.2 数据一致性挑战
- **问题**: 复权数据与实时数据同步
- **解决方案**: 基于复权因子的实时计算 + Parquet增量更新

### 10.3 查询性能挑战  
- **问题**: 大规模Parquet文件查询延迟
- **解决方案**: 
  - 建立Parquet文件索引
  - 使用DuckDB进行高效查询
  - 预计算常用查询结果

### 10.4 实时数据处理挑战
- **问题**: 实时数据写入Parquet的性能
- **解决方案**: 
  - 批量写入优化
  - 内存缓存 + 定期刷盘
  - 异步写入机制

### 10.5 可视化性能挑战
- **问题**: Parquet大数据量下的渲染性能
- **解决方案**: 
  - 数据采样和聚合
  - 懒加载和分页查询
  - 预计算可视化数据

## 11. 高级研究功能

### 11.1 多时间框架研究
```python
class MultiTimeframeResearch:
    def __init__(self):
        self.timeframes = ['1m', '5m', '15m', '1h', '1d', '1w']
        
    async def analyze_strategy_robustness(self, strategy):
        """分析策略在不同时间框架下的稳健性"""
        results = {}
        for timeframe in self.timeframes:
            data = await self._get_data_for_timeframe(timeframe)
            result = await self.backtest_engine.run_backtest(strategy, data)
            results[timeframe] = result
        return results
```

### 11.2 市场状态自适应
```python
class MarketStateAdaptiveResearch:
    def __init__(self):
        self.market_state_classifier = MarketStateClassifier()
        
    async def research_by_market_state(self, strategy, market_data):
        """按市场状态进行策略研究"""
        market_states = self.market_state_classifier.classify(market_data)
        
        state_specific_results = {}
        for state in market_states:
            state_data = market_data[market_data['market_state'] == state]
            result = await self.backtest_engine.run_backtest(strategy, state_data)
            state_specific_results[state] = result
            
        return state_specific_results
```

## 12. 风险控制与监控

### 12.1 实时风险监控
```python
class RealTimeRiskMonitor:
    def __init__(self):
        self.risk_metrics = {
            'var': ValueAtRisk(),
            'max_drawdown': MaxDrawdown(),
            'volatility': VolatilityCalculator()
        }
        
    async def monitor_portfolio_risk(self, portfolio, market_data):
        """实时监控组合风险"""
        risk_alerts = []
        for metric_name, metric_calc in self.risk_metrics.items():
            risk_level = await metric_calc.calculate(portfolio, market_data)
            if risk_level > self.thresholds[metric_name]:
                risk_alerts.append({
                    'metric': metric_name,
                    'level': risk_level,
                    'threshold': self.thresholds[metric_name]
                })
        return risk_alerts
```

## 13. 项目优势总结

1. **模块化设计**: 各功能模块独立，便于维护和扩展
2. **数据驱动**: 基于FutuAPI和yfinance的可靠数据源
3. **智能研究**: MCP集成的策略研究能力
4. **实时能力**: 支持盘前筛选和实时交易建议
5. **可视化强大**: Dash+Plotly的交互式分析界面
6. **风险可控**: 完善的风险管理和回测验证
7. **技术先进**: 采用现代Python技术栈和最佳实践

## 14. 部署与运维建议

### 14.1 开发环境配置
- 使用Docker容器化部署
- 配置开发/测试/生产环境
- 设置监控和日志系统

### 14.2 性能优化策略
- 数据库索引优化
- 缓存策略设计
- 异步任务处理
- 负载均衡配置

### 14.3 安全考虑
- API密钥安全管理
- 数据传输加密
- 访问权限控制
- 审计日志记录

---

**文档版本**: 1.0  
**创建时间**: 2024年  
**最后更新**: 2024年  
**项目状态**: 架构设计完成，准备实施