"""
指标注册器
实现指标的动态发现和加载
"""

import importlib
import inspect
from typing import Dict, List, Optional, Type, Any
from pathlib import Path
import pkgutil
from .base_indicator import BaseIndicator


class IndicatorRegistry:
    """
    指标注册器，负责指标类的注册、注销和创建指标对象，创建的对象可以被指标计算器使用
    初始化时不需要传入指标对象，所有指标类都需要通过register_indicator方法注册
    注册的指标对象可以用模块引入方式加载（from...import...或者indicators.technical.SMA()）
    在加载引入后手动注册：registry.register_indicator(SMA)
    也可以用自带的自动导入方式导入并注册指标类：registry.register_package("indicators.technical")
    注册好的指标再实例化后给指标计算器使用：calculator.register_indicator(sma_50, "sma_50")
    带有便捷函数：
        获取实例的方法：indicators_registry()
        手动注册指标类的方法：register_indicator(indicator_class, category)
        创建指标对象的方法：create_indicator(indicator_name, **kwargs)
    建议使用方法：
        使用流程：初始化注册器->批量注册（导入）指标类->创建指标对象->注册指标对象到计算器
        1、from indicators.base.registry import indicators_registry, register_indicator_func, create_indicator_func
        2、registry = indicators_registry()
        3、这时可以使用registry的各种方法了，比如按照包名批量加载并注册指标类：registry.register_package("indicators.technical")
        4、也可以用register_indicator_func方法注册指标类，比如：register_indicator_func(SMA, 'trend')
        5、创建计算用的指标对象：sma_50 = create_indicator("SMA", period=50)
        6、注册指标对象到计算器：calculator.register_indicator(sma_50, "sma_50")
        
    """
    
    def __init__(self):
        self._indicators: Dict[str, Type[BaseIndicator]] = {}
        self._indicator_categories: Dict[str, List[str]] = {}
        self._loaded_packages: set = set()
    
    def register_indicator(self, 
                          indicator_class: Type[BaseIndicator],
                          category: str = "technical"):
        """
        手动注册指标类，将指标子类（这些子类一般是使用from...import...导入的）添加到注册器中,并将指标添加到指定分类
        注意： 
        指标类必须是BaseIndicator的子类，且必须实现calculate方法
        Args:
            indicator_class: 指标类，必须是BaseIndicator的子类，可以直接从指标模块引入（from...import...）
            category: 指标分类，用于指标计算器根据分类选择指标
        """
        if not inspect.isclass(indicator_class) or not issubclass(indicator_class, BaseIndicator):
            raise ValueError("必须提供BaseIndicator的子类")
        
        indicator_name = indicator_class.__name__
        
        if indicator_name in self._indicators:
            raise ValueError(f"指标 '{indicator_name}' 已注册")
        
        self._indicators[indicator_name] = indicator_class
        
        # 添加到分类
        if category not in self._indicator_categories:
            self._indicator_categories[category] = []
        self._indicator_categories[category].append(indicator_name)
    
    def unregister_indicator(self, indicator_name: str):
        """注销指标"""
        if indicator_name in self._indicators:
            del self._indicators[indicator_name]
            
            # 从所有分类中移除
            for category, indicators in self._indicator_categories.items():
                if indicator_name in indicators:
                    indicators.remove(indicator_name)
    
    def create_indicator(self, 
                        indicator_name: str,
                        **kwargs) -> BaseIndicator:
        """
        创建指标实例，要先注册指标类然后才可以创建指标实例，比如先注册SMA指标，然后创建SMA16实例
        然后这个SMA16实例就可以被指标计算器使用了
        
        Args:
            indicator_name: 指标名称
            **kwargs: 指标参数
            
        Returns:
            指标实例
        """
        if indicator_name not in self._indicators:
            raise ValueError(f"未找到指标: {indicator_name}")
        
        indicator_class = self._indicators[indicator_name]
        return indicator_class(**kwargs)
    
    def get_available_indicators(self, 
                                category: Optional[str] = None) -> List[str]:
        """
        获取可用的指标列表
        
        Args:
            category: 指定分类，如果为None则返回所有指标
            
        Returns:
            指标名称列表
        """
        if category:
            return self._indicator_categories.get(category, []).copy()
        else:
            return list(self._indicators.keys())
    
    def get_indicator_categories(self) -> List[str]:
        """获取指标分类列表"""
        return list(self._indicator_categories.keys())
    
    def get_indicator_info(self, indicator_name: str) -> Dict[str, Any]:
        """
        获取指标信息
        
        Args:
            indicator_name: 指标名称
            
        Returns:
            指标信息字典
        """
        if indicator_name not in self._indicators:
            raise ValueError(f"未找到指标: {indicator_name}")
        
        indicator_class = self._indicators[indicator_name]
        
        # 获取类的文档字符串
        docstring = inspect.getdoc(indicator_class) or ""
        
        # 获取构造函数参数
        signature = inspect.signature(indicator_class.__init__)
        parameters = {}
        
        for param_name, param in signature.parameters.items():
            if param_name == 'self':
                continue
            parameters[param_name] = {
                'default': param.default if param.default != param.empty else None,
                'annotation': str(param.annotation) if param.annotation != param.empty else 'Any'
            }
        
        return {
            'name': indicator_name,
            'class': indicator_class,
            'docstring': docstring,
            'parameters': parameters,
            'category': self._get_indicator_category(indicator_name)
        }
    
    def load_indicators_from_package(self, package_name: str):
        """
        从指定包加载所有指标并完成注册，包是指标模块的包，比如'indicators.technical'，
        或者子包indicators.technical.moving_average
        Args:
            package_name: 包名称
        """
        if package_name in self._loaded_packages:
            return
        
        try:
            package = importlib.import_module(package_name)
            
            # 遍历包中的所有模块
            for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + '.'):
                if not is_pkg:  # 只处理模块，不处理子包
                    try:
                        module = importlib.import_module(module_name)
                        self._register_indicators_from_module(module)
                    except ImportError as e:
                        print(f"无法导入模块 {module_name}: {e}")
            
            self._loaded_packages.add(package_name)
            
        except ImportError as e:
            print(f"无法导入包 {package_name}: {e}")
    
    def load_indicators_from_directory(self, directory_path: str):
        """
        从指定目录加载所有指标并完成注册，目录是指标模块的目录，比如indicators/technical，
        或者子目录indicators/technical/moving_average
        
        Args:
            directory_path: 目录路径
        """
        directory = Path(directory_path)
        
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"目录不存在或不是目录: {directory_path}")
        
        # 将目录添加到Python路径
        import sys
        if str(directory.parent) not in sys.path:
            sys.path.insert(0, str(directory.parent))
        
        # 导入目录中的所有Python文件
        for py_file in directory.glob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            module_name = py_file.stem
            package_name = directory.name
            
            try:
                full_module_name = f"{package_name}.{module_name}"
                module = importlib.import_module(full_module_name)
                self._register_indicators_from_module(module)
            except ImportError as e:
                print(f"无法导入模块 {full_module_name}: {e}")
    
    def _register_indicators_from_module(self, module):
        """
        从模块中注册所有指标类，指标类要继承自BaseIndicator，并且不是BaseIndicator类本身，比如：SMA、EMA、MACD等
        是给load_indicators_from_package和load_indicators_from_directory方法调用的
        """
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, BaseIndicator) and 
                obj != BaseIndicator and
                obj.__name__ not in ['TechnicalIndicator', 'StatisticalIndicator', 'FundamentalIndicator', 'BaseFactor']):
                
                # 自动确定分类
                category = self._determine_category(obj)
                self.register_indicator(obj, category)
    
    def _determine_category(self, indicator_class: Type[BaseIndicator]) -> str:
        """自动确定指标分类,是给_register_indicators_from_module方法调用的"""
        class_name = indicator_class.__name__.lower()
        module_name = indicator_class.__module__.lower()
        
        # 基于类名和模块名判断分类
        if 'statistical' in module_name or 'stat' in class_name:
            return 'statistical'
        elif 'volume' in module_name or 'volume' in class_name:
            return 'volume'
        elif 'volatility' in module_name or 'volatility' in class_name:
            return 'volatility'
        elif 'momentum' in module_name or 'momentum' in class_name:
            return 'momentum'
        elif 'trend' in module_name or 'trend' in class_name:
            return 'trend'
        else:
            return 'technical'
    
    def _get_indicator_category(self, indicator_name: str) -> str:
        """获取指标的分类,是给register_indicator和create_indicator方法调用的"""
        for category, indicators in self._indicator_categories.items():
            if indicator_name in indicators:
                return category
        return 'unknown'


'''
带有便捷函数get_registry register_indicator create_indicator：
    1. 先导入指标模块：from indicators.technical import SMA, EMA, MACD
    2. 获取注册器实例：registry = get_registry()，
        也可以先获取实例后使用registry实例的方法从包或者目录导入指标模块
    3. 注册指标类：registry.register_indicator()
    4. 创建指标实例：indicator = registry.create_indicator()
'''
# 创建全局注册器实例
_registry = IndicatorRegistry()


def indicators_registry() -> IndicatorRegistry:
    """获取全局注册器实例(便捷函数)"""
    return _registry


def register_indicator_func(indicator_class: Type[BaseIndicator], category: str = "technical"):
    """注册指标类（便捷函数）"""
    _registry.register_indicator(indicator_class, category)


def create_indicator_func(indicator_name: str, **kwargs) -> BaseIndicator:
    """创建指标实例（便捷函数）"""
    return _registry.create_indicator(indicator_name, **kwargs)