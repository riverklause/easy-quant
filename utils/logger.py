"""
系统日志模块
支持多级别日志记录和文件输出
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

from .settings import settings

class Logger:
    """系统日志类"""
    
    def __init__(self, name='easy_quant', log_level=None):
        self.name = name
        self.log_level = log_level or settings.LOG_LEVEL
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """配置日志器"""
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.log_level.upper()))
        
        # 清除已有处理器
        logger.handlers.clear()
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, self.log_level.upper()))
        
        # 添加文件处理器
        log_dir = settings.DATA_BASE_PATH / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f'easy_quant_{datetime.now().strftime("%Y%m%d")}.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        
        return logger
    
    def debug(self, message):
        """调试级别日志"""
        self.logger.debug(message)
        
    def info(self, message):
        """信息级别日志"""
        self.logger.info(message)
        
    def warning(self, message):
        """警告级别日志"""
        self.logger.warning(message)
        
    def error(self, message):
        """错误级别日志"""
        self.logger.error(message)
        
    def critical(self, message):
        """严重级别日志"""
        self.logger.critical(message)

# 创建全局日志实例
logger = Logger()

# 便捷访问函数
def get_logger(name=None):
    """获取日志器实例"""
    if name:
        return Logger(name)
    return logger

def log_performance(func):
    """性能日志装饰器"""
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        result = func(*args, **kwargs)
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        logger.info(f"函数 {func.__name__} 执行时间: {execution_time:.4f} 秒")
        return result
    return wrapper

if __name__ == "__main__":
    # 测试日志功能
    logger.debug("这是一条调试信息")
    logger.info("这是一条普通信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    
    # 测试性能日志装饰器
    @log_performance
    def test_function():
        import time
        time.sleep(0.1)
        return "测试完成"
    
    result = test_function()
    print(result)