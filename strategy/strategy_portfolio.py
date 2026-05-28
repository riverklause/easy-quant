"""
策略组合管理器
管理策略、指标组合和适用股票的对应关系
"""

from typing import Dict, List, Optional
from datetime import datetime


class StrategyPortfolio:
    """
    策略组合管理器
    管理策略、指标组合和适用股票的对应关系
    """
    
    def __init__(self, name: str):
        """
        初始化策略组合
        
        Args:
            name: 策略组合名称
        """
        self.name = name
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        # 策略组合配置
        self.strategy_configs = []
        
        # 股票映射表: {股票代码: 适用的策略列表}
        self.stock_strategy_map = {}
        
        # 全局策略列表
        self.global_strategies = []
    
    def add_strategy(self, 
                   strategy_id: str,
                   strategy_type: str,  # 'technical' 或 'multi_factor'
                   indicators: List[str],
                   params: Dict,
                   applicable_stocks: Optional[List[str]] = None):
        """
        添加策略到组合
        
        Args:
            strategy_id: 策略ID
            strategy_type: 策略类型
            indicators: 指标组合列表
            params: 策略参数
            applicable_stocks: 适用的股票列表，None表示适用于所有股票
        """
        # 添加策略配置
        self.strategy_configs.append({
            'strategy_id': strategy_id,
            'strategy_type': strategy_type,
            'indicators': indicators,
            'params': params,
            'applicable_stocks': applicable_stocks
        })
        
        # 更新股票策略映射
        if applicable_stocks:
            for stock in applicable_stocks:
                if stock not in self.stock_strategy_map:
                    self.stock_strategy_map[stock] = []
                self.stock_strategy_map[stock].append(strategy_id)
        else:
            # 全局策略
            self.global_strategies.append(strategy_id)
        
        self.updated_at = datetime.now()
        print(f"[+] 策略 '{strategy_id}' 已添加到组合")
    
    def get_strategies_for_stock(self, stock_symbol: str) -> List[str]:
        """
        获取适用于特定股票的策略列表
        
        Args:
            stock_symbol: 股票代码
            
        Returns:
            适用的策略ID列表
        """
        # 全局策略 + 股票特定策略
        return self.global_strategies + self.stock_strategy_map.get(stock_symbol, [])
    
    def remove_strategy(self, strategy_id: str):
        """
        从组合中移除策略
        
        Args:
            strategy_id: 策略ID
        """
        # 移除策略配置
        self.strategy_configs = [
            config for config in self.strategy_configs 
            if config['strategy_id'] != strategy_id
        ]
        
        # 从全局策略中移除
        if strategy_id in self.global_strategies:
            self.global_strategies.remove(strategy_id)
        
        # 从股票策略映射中移除
        for stock, strategies in self.stock_strategy_map.items():
            if strategy_id in strategies:
                strategies.remove(strategy_id)
        
        self.updated_at = datetime.now()
        print(f"[x] 策略 '{strategy_id}' 已从组合中移除")
    
    def get_portfolio_info(self) -> Dict:
        """
        获取组合信息
        
        Returns:
            组合信息字典
        """
        return {
            'name': self.name,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'strategy_count': len(self.strategy_configs),
            'global_strategies_count': len(self.global_strategies),
            'stock_specific_strategies_count': sum(len(strategies) for strategies in self.stock_strategy_map.values()),
            'covered_stocks': len(self.stock_strategy_map)
        }
    
    def export_config(self) -> Dict:
        """
        导出组合配置
        
        Returns:
            组合配置字典
        """
        return {
            'name': self.name,
            'description': getattr(self, 'description', ''),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'strategy_configs': self.strategy_configs,
            'stock_strategy_map': self.stock_strategy_map,
            'global_strategies': self.global_strategies,
            'params': getattr(self, 'params', {})
        }
    
    @classmethod
    def import_config(cls, config: Dict) -> 'StrategyPortfolio':
        """
        从配置导入组合
        
        Args:
            config: 组合配置字典
            
        Returns:
            策略组合实例
        """
        portfolio = cls(config['name'])
        portfolio.created_at = datetime.fromisoformat(config['created_at'])
        portfolio.updated_at = datetime.fromisoformat(config['updated_at'])
        portfolio.strategy_configs = config['strategy_configs']
        portfolio.stock_strategy_map = config['stock_strategy_map']
        portfolio.global_strategies = config['global_strategies']
        if 'description' in config:
            portfolio.description = config['description']
        if 'params' in config:
            portfolio.params = config['params']
        return portfolio
    
    def update_strategy_params(self, strategy_id: str, **kwargs):
        """
        更新策略参数
        
        Args:
            strategy_id: 策略ID
            **kwargs: 新的策略参数
        """
        for config in self.strategy_configs:
            if config['strategy_id'] == strategy_id:
                config['params'].update(kwargs)
                self.updated_at = datetime.now()
                print(f"✅ 策略 '{strategy_id}' 参数已更新: {kwargs}")
                return
        
        print(f"[-] 未找到策略 '{strategy_id}'")
    
    def get_strategy_config(self, strategy_id: str) -> Optional[Dict]:
        """
        获取策略配置
        
        Args:
            strategy_id: 策略ID
            
        Returns:
            策略配置字典，None表示策略不存在
        """
        for config in self.strategy_configs:
            if config['strategy_id'] == strategy_id:
                return config.copy()
        return None
    
    def get_all_strategies(self) -> List[str]:
        """
        获取组合中的所有策略ID
        
        Returns:
            所有策略ID列表
        """
        return [config['strategy_id'] for config in self.strategy_configs]
    
    def copy_portfolio(self, new_name: str) -> 'StrategyPortfolio':
        """
        复制组合
        
        Args:
            new_name: 新组合名称
            
        Returns:
            新的策略组合实例
        """
        # 导出配置并创建新组合
        config = self.export_config()
        config['name'] = new_name
        return self.import_config(config)
