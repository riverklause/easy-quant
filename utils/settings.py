"""
系统配置文件
支持数据文件夹路径自定义和代理配置
"""
import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path


# 数据路径配置
# 默认数据路径
default_data_path = 'data'

# 如果需要修改默认数据路径，取消注释并修改
# data_path = "c:\\data"
data_path = None

# 计算最终路径
from pathlib import Path
import os
base_path = Path.cwd()

@dataclass
class DataConfig:
    """数据配置"""
    #基础配置
    default_data_path = 'data'
    # 如果需要修改默认数据路径，下一行可以改为如：data_path = "c:\\data
    data_path = None
    data_dir = os.path.expandvars(data_path) if data_path else Path.cwd() / default_data_path  # 数据存储目录
    cache_dir = data_dir / 'cache'  # 缓存目录
    update_interval: int = 3600  # 数据更新间隔(秒)

    #可用的数据源
    available_data_sources: List[str] = None
    
    def __post_init__(self):
        if self.available_data_sources is None:
            self.available_data_sources = ['futu', 'yfinance']

    #Futu数据格式
    Futu_dataFormat = ["time_key","code","open","close","high","low","pe_ratio","turnover_rate","volume","turnover","change_rate","last_close"]
    
    #Futu前缀和yfinance市场后缀映射
    Futu_yf_MarketMap = {
        'HK': 'HK',
        'US': 'US',
        'SZ': 'SZ',
        'SH': 'SS'
    }

    # yfinance配置
    yfinance_proxy: str = "http://127.0.0.1:5644"  # yfinance代理地址
    
    # Futu配置
    Futu_Host: str = "127.0.0.1"
    Futu_Port: int = 11111
    Futu_WebSocketPort: int = 33333
    Futu_WebSocketKey: str = "75072ca35607dcd"
    Futu_TrdEnv: str = "SIMULATE"
    Futu_RsaPrivateKey = data_dir / 'rsa.key' # Futu RSA私钥路径
    Futu_Username: str = "17372346"
    Futu_Pwd_md5: str = "2be7fc55805288f65ffe3bf2bac193b1"


@dataclass
class TradingConfig:
    """交易配置"""
    commission_rate: float = 0.0003  # 交易佣金率
    slippage: float = 0.001  # 滑点
    initial_capital: float = 100000.0  # 初始资金


@dataclass
class RiskConfig:
    """风险配置"""
    max_position_ratio: float = 0.8  # 最大持仓比例
    stop_loss_rate: float = 0.05  # 止损比例
    take_profit_rate: float = 0.1  # 止盈比例
    max_drawdown_limit: float = 0.2  # 最大回撤限制


@dataclass
class RedisConfig:
    """Redis配置"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    cache_ttl: int = 3600  # 缓存过期时间(秒)


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"  # 日志级别
    dir: str = "logs"  # 日志目录
    max_size: int = 100  # 日志文件最大大小(MB)
    backup_count: int = 10  # 备份文件数量


class Settings:
    """系统设置"""
    
    def __init__(self):
        self.data = DataConfig()
        self.trading = TradingConfig()
        self.risk = RiskConfig()
        self.redis = RedisConfig()
        self.log = LogConfig()
    
    @property
    def futu_rsa_key_path(self):
        """获取Futu RSA私钥的完整路径"""
        return str(Path(self.data.data_dir) / "rsa.key")


# 全局配置实例
settings = Settings()

# 便捷访问函数
def get_data_path(data_type):
    """获取数据路径的便捷函数"""
    return Path(settings.data.data_dir) / data_type

def get_yfinance_proxy():
    """获取yfinance代理配置的便捷函数"""
    if settings.data.yfinance_proxy:
        return {
            'http': settings.data.yfinance_proxy,
        }
    return None

def update_settings(data_path=None, yfinance_proxy=None):
    """更新系统设置的便捷函数"""
    if data_path:
        settings.data.data_dir = data_path
        print(f"数据文件夹路径已更新为: {data_path}")
    if yfinance_proxy:
        settings.data.yfinance_proxy = yfinance_proxy
        print(f"yfinance代理已更新为: {yfinance_proxy}")


def get_futu_rsa_key_path():
    """获取Futu RSA私钥完整路径的便捷函数"""
    return settings.futu_rsa_key_path

# 环境变量配置说明
ENV_CONFIG_DOC = """
环境变量配置说明：

# 数据文件夹路径（支持自定义迁移）
DATA_BASE_PATH=/path/to/your/data/folder

# yfinance代理配置
yfinance需要指定代理地址才能正常运行
YFINANCE_PROXY=http://your-proxy-server:port

# 其他配置
LOG_LEVEL=INFO|DEBUG|WARNING
MAX_WORKERS=10
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
DEFAULT_DATA_SOURCE=futu
"""

if __name__ == "__main__":
    # 测试配置
    print("当前数据路径:", settings.DATA_BASE_PATH)
    print("yfinance代理:", settings.YFINANCE_PROXY)
    print("环境变量配置说明:")
    print(ENV_CONFIG_DOC)