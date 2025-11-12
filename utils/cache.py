"""
缓存管理模块
支持内存缓存和Redis缓存
"""
import pickle
import time
from typing import Any, Optional
import redis

from .settings import settings
from .logger import logger

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.memory_cache = {}
        self.redis_client = None
        self._setup_redis()
        
    def _setup_redis(self):
        """设置Redis连接"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=False
            )
            # 测试连接
            self.redis_client.ping()
            logger.info("Redis连接成功")
        except Exception as e:
            logger.warning(f"Redis连接失败，将使用内存缓存: {e}")
            self.redis_client = None
    
    def set(self, key: str, value: Any, expire: int = 3600, use_redis: bool = True):
        """设置缓存"""
        try:
            if use_redis and self.redis_client:
                # Redis缓存
                serialized_value = pickle.dumps(value)
                self.redis_client.setex(key, expire, serialized_value)
            else:
                # 内存缓存
                self.memory_cache[key] = {
                    'value': value,
                    'expire_time': time.time() + expire
                }
            logger.debug(f"缓存设置成功: {key}")
        except Exception as e:
            logger.error(f"缓存设置失败 {key}: {e}")
    
    def get(self, key: str, default: Any = None, use_redis: bool = True) -> Optional[Any]:
        """获取缓存"""
        try:
            if use_redis and self.redis_client:
                # Redis缓存
                serialized_value = self.redis_client.get(key)
                if serialized_value:
                    return pickle.loads(serialized_value)
            else:
                # 内存缓存
                cache_item = self.memory_cache.get(key)
                if cache_item and time.time() < cache_item['expire_time']:
                    return cache_item['value']
                elif cache_item:
                    # 缓存过期，删除
                    del self.memory_cache[key]
            
            return default
        except Exception as e:
            logger.error(f"缓存获取失败 {key}: {e}")
            return default
    
    def delete(self, key: str, use_redis: bool = True):
        """删除缓存"""
        try:
            if use_redis and self.redis_client:
                self.redis_client.delete(key)
            if key in self.memory_cache:
                del self.memory_cache[key]
            logger.debug(f"缓存删除成功: {key}")
        except Exception as e:
            logger.error(f"缓存删除失败 {key}: {e}")
    
    def clear(self, pattern: str = None):
        """清除缓存"""
        try:
            if pattern:
                # 按模式清除
                if self.redis_client:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
                
                # 内存缓存模式清除
                keys_to_delete = [k for k in self.memory_cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.memory_cache[key]
            else:
                # 清除所有
                if self.redis_client:
                    self.redis_client.flushdb()
                self.memory_cache.clear()
            
            logger.info(f"缓存清除完成: {pattern or 'all'}")
        except Exception as e:
            logger.error(f"缓存清除失败: {e}")
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            if self.redis_client:
                return self.redis_client.exists(key) > 0
            return key in self.memory_cache
        except Exception as e:
            logger.error(f"缓存存在检查失败 {key}: {e}")
            return False

# 创建全局缓存实例
cache_manager = CacheManager()

# 缓存装饰器
def cached(expire: int = 3600, key_prefix: str = "", use_redis: bool = True):
    """缓存装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key, use_redis=use_redis)
            if cached_result is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 设置缓存
            cache_manager.set(cache_key, result, expire, use_redis)
            logger.debug(f"缓存设置: {cache_key}")
            
            return result
        return wrapper
    return decorator

# 便捷访问函数
def get_cache():
    """获取缓存管理器实例"""
    return cache_manager

def clear_indicator_cache(symbol: str = None):
    """清除指标缓存"""
    pattern = f"indicator:*{symbol or ''}*"
    cache_manager.clear(pattern)

if __name__ == "__main__":
    # 测试缓存功能
    cache_manager.set("test_key", "test_value", 60)
    value = cache_manager.get("test_key")
    print(f"缓存值: {value}")
    
    # 测试缓存装饰器
    @cached(expire=300, key_prefix="calc_")
    def expensive_calculation(x, y):
        print("执行计算...")
        return x + y
    
    result1 = expensive_calculation(10, 20)
    result2 = expensive_calculation(10, 20)  # 应该从缓存获取
    print(f"计算结果: {result1}, {result2}")