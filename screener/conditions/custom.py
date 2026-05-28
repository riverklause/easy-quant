"""
自定义条件，通过传入的evaluate_func评估
比如：
def volatility_check(data):
    returns = data['close'].pct_change()
    volatility = returns.std() * np.sqrt(252)
    return volatility < 0.3

"""

from screener.filter_condition import FilterCondition


class CustomCondition(FilterCondition):
    """自定义条件"""

    def __init__(self, name: str, evaluate_func):
        """
        初始化自定义条件

        Args:
            name: 条件名称
            evaluate_func: 评估函数，接收data返回bool
        """
        super().__init__(name)
        self.evaluate_func = evaluate_func

    def evaluate(self, data) -> bool:
        """评估自定义条件"""
        try:
            return self.evaluate_func(data)
        except Exception:
            return False