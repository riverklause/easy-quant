"""
数据状态管理器 - 统一管理实时数据、指标、告警和策略
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np
import json
from pathlib import Path


@dataclass
class AlertConfig:
    """告警配置"""
    symbol: str
    alert_type: str
    threshold: float
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AlertRecord:
    """告警记录"""
    symbol: str
    alert_type: str
    message: str
    triggered_value: float
    triggered_at: datetime = field(default_factory=datetime.now)


@dataclass
class RealtimeQuote:
    """实时行情数据结构"""
    code: str
    last_price: float
    prev_close: float
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    turnover: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open: float = 0.0
    bid_price: float = 0.0
    ask_price: float = 0.0
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class StrategySignal:
    """策略信号"""
    strategy_id: str
    symbol: str
    signal_type: str  # 'buy', 'sell', 'hold'
    price: float
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = ""


@dataclass
class StrategyStatus:
    """策略运行状态"""
    strategy_id: str
    name: str
    status: str = "stopped"  # 'running', 'stopped'
    mode: str = "realtime"  # 'realtime', 'filter', 'backtest'
    monitored_symbols: List[str] = field(default_factory=list)
    last_signal: Optional[StrategySignal] = None
    positions: Dict[str, float] = field(default_factory=dict)
    cash: float = 0.0
    total_asset: float = 0.0
    logs: List[str] = field(default_factory=list)
    data_connected: bool = False


class DataStateManager:
    """统一数据状态管理器"""

    def __init__(self, config: Dict[str, Any] = None, socketio=None):
        self.config = config or {}
        self._socketio = socketio

        self._realtime_quotes: Dict[str, RealtimeQuote] = {}
        self._indicator_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self._alert_configs: List[AlertConfig] = []
        self._alert_history: List[AlertRecord] = []
        self._strategy_status: Dict[str, StrategyStatus] = {}
        self._strategy_signals: List[StrategySignal] = []

        self._ui_update_callbacks: List[Callable] = []
        self._strategy_callbacks: List[Callable] = []
        self._alert_callbacks: List[Callable] = []

        self._update_version = 0
        self._last_update_data: Dict[str, Any] = {}

        self._data_dir = Path("data")
        self._load_alert_configs()
        self._load_strategy_status()

    def set_socketio(self, socketio):
        """设置 SocketIO 实例"""
        self._socketio = socketio

    def update_quote(self, quote_data: pd.DataFrame) -> None:
        """更新实时行情 - 被 FutuRTProcessor 回调调用"""
        if quote_data is None or quote_data.empty:
            return
        
        df = quote_data
        symbol = df['code'].iloc[0] if 'code' in df.columns else ''
        prev_close = float(df['prev_close_price'].iloc[0]) if 'prev_close_price' in df.columns else 0
        last_price = float(df['last_price'].iloc[0]) if 'last_price' in df.columns else 0
        change = last_price - prev_close
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        
        quote = RealtimeQuote(
            code=symbol,
            last_price=last_price,
            prev_close=prev_close,
            change=change,
            change_pct=change_pct,
            volume=int(df['volume'].iloc[0]) if 'volume' in df.columns else 0,
            turnover=float(df['turnover'].iloc[0]) if 'turnover' in df.columns else 0,
            high=float(df['high_price'].iloc[0]) if 'high_price' in df.columns else 0,
            low=float(df['low_price'].iloc[0]) if 'low_price' in df.columns else 0,
            open=float(df['open_price'].iloc[0]) if 'open_price' in df.columns else 0,
            bid_price=0,
            ask_price=0
        )
        
        self._realtime_quotes[symbol] = quote
        
        self._recalculate_indicators(symbol)
        
        self._check_alerts(symbol, quote)
        
        self._trigger_strategies(symbol, quote)
        
        self._update_version += 1
        self._last_update_data = {
            'version': self._update_version,
            'type': 'quote',
            'symbol': symbol,
            'data': {
                'last_price': last_price,
                'change': change,
                'change_pct': change_pct,
                'volume': int(df['volume'].iloc[0]) if 'volume' in df.columns else 0
            }
        }
        
        self._notify_ui_update()

    def _recalculate_indicators(self, symbol: str) -> None:
        """重新计算指定股票的指标"""
        pass

    def _check_alerts(self, symbol: str, quote: RealtimeQuote) -> None:
        """检查告警条件"""
        for config in self._alert_configs:
            if config.symbol != symbol or not config.enabled:
                continue

            triggered = False
            message = ""

            if config.alert_type == 'price_above':
                if quote.last_price > config.threshold:
                    triggered = True
                    message = f"{symbol} 价格上涨超过 {config.threshold}，当前价格: {quote.last_price}"

            elif config.alert_type == 'price_below':
                if quote.last_price < config.threshold:
                    triggered = True
                    message = f"{symbol} 价格跌破 {config.threshold}，当前价格: {quote.last_price}"

            elif config.alert_type == 'price_change_pct':
                if abs(quote.change_pct) > config.threshold:
                    triggered = True
                    message = f"{symbol} 涨跌幅超过 {config.threshold}%，当前涨跌幅: {quote.change_pct:+.2f}%"

            if triggered:
                record = AlertRecord(
                    symbol=symbol,
                    alert_type=config.alert_type,
                    message=message,
                    triggered_value=quote.last_price
                )
                self._alert_history.append(record)

                for callback in self._alert_callbacks:
                    try:
                        callback(record)
                    except Exception as e:
                        print(f"告警回调错误: {e}")

                if self._socketio:
                    self._socketio.emit('alert', {
                        'symbol': symbol,
                        'alert_type': config.alert_type,
                        'message': message,
                        'price': quote.last_price,
                        'timestamp': datetime.now().isoformat()
                    })

    def _trigger_strategies(self, symbol: str, quote: RealtimeQuote) -> None:
        """触发策略执行"""
        for strategy_id, status in self._strategy_status.items():
            if status.status != 'running':
                continue

            if symbol not in status.monitored_symbols:
                continue

            for callback in self._strategy_callbacks:
                try:
                    callback(symbol, quote, self)
                except Exception as e:
                    print(f"策略执行错误: {e}")

    def _notify_ui_update(self) -> None:
        """通知 UI 更新"""
        for callback in self._ui_update_callbacks:
            try:
                callback(self._last_update_data)
            except Exception as e:
                print(f"UI 更新回调错误: {e}")

        if self._socketio:
            self._socketio.emit('data_update', self._last_update_data)

    def register_ui_callback(self, callback: Callable) -> None:
        """注册 UI 更新回调"""
        self._ui_update_callbacks.append(callback)

    def register_strategy_callback(self, callback: Callable) -> None:
        """注册策略回调"""
        self._strategy_callbacks.append(callback)

    def register_alert_callback(self, callback: Callable) -> None:
        """注册告警回调"""
        self._alert_callbacks.append(callback)

    def get_quote(self, symbol: str) -> Optional[RealtimeQuote]:
        """获取指定股票行情"""
        return self._realtime_quotes.get(symbol)

    def get_all_quotes(self) -> Dict[str, RealtimeQuote]:
        """获取所有股票行情"""
        return self._realtime_quotes.copy()

    def get_update_version(self) -> int:
        """获取当前更新版本号"""
        return self._update_version

    def get_last_update_data(self) -> Dict[str, Any]:
        """获取上次更新的数据"""
        return self._last_update_data

    def get_alert_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[AlertRecord]:
        """获取告警历史"""
        if symbol:
            return [r for r in self._alert_history if r.symbol == symbol][-limit:]
        return self._alert_history[-limit:]

    def add_alert(self, config: AlertConfig) -> None:
        """添加告警配置"""
        self._alert_configs.append(config)
        self._save_alert_configs()

    def remove_alert(self, symbol: str, alert_type: str) -> None:
        """移除告警配置"""
        self._alert_configs = [
            c for c in self._alert_configs
            if not (c.symbol == symbol and c.alert_type == alert_type)
        ]
        self._save_alert_configs()

    def get_alert_configs(self) -> List[AlertConfig]:
        """获取所有告警配置"""
        return self._alert_configs.copy()

    def _save_alert_configs(self) -> None:
        """保存告警配置到文件"""
        try:
            data = []
            for config in self._alert_configs:
                data.append({
                    'symbol': config.symbol,
                    'alert_type': config.alert_type,
                    'threshold': config.threshold,
                    'enabled': config.enabled,
                    'created_at': config.created_at.isoformat()
                })
            file_path = self._data_dir / 'AlertConfig.parquet'
            if data:
                pd.DataFrame(data).to_parquet(file_path)
        except Exception as e:
            print(f"保存告警配置失败: {e}")

    def _load_alert_configs(self) -> None:
        """从文件加载告警配置"""
        try:
            file_path = self._data_dir / 'AlertConfig.parquet'
            if file_path.exists():
                df = pd.read_parquet(file_path)
                for _, row in df.iterrows():
                    self._alert_configs.append(AlertConfig(
                        symbol=row['symbol'],
                        alert_type=row['alert_type'],
                        threshold=row['threshold'],
                        enabled=row['enabled'],
                        created_at=datetime.fromisoformat(row['created_at'])
                    ))
        except Exception as e:
            print(f"加载告警配置失败: {e}")

    def update_strategy_status(self, strategy_id: str, **kwargs) -> None:
        """更新策略状态"""
        if strategy_id not in self._strategy_status:
            self._strategy_status[strategy_id] = StrategyStatus(
                strategy_id=strategy_id,
                name=kwargs.get('name', strategy_id)
            )

        for key, value in kwargs.items():
            if hasattr(self._strategy_status[strategy_id], key):
                setattr(self._strategy_status[strategy_id], key, value)

        self._save_strategy_status()

    def get_strategy_status(self, strategy_id: str = None) -> Dict[str, StrategyStatus] | StrategyStatus:
        """获取策略状态"""
        if strategy_id:
            return self._strategy_status.get(strategy_id)
        return self._strategy_status.copy()

    def add_strategy_signal(self, signal: StrategySignal) -> None:
        """添加策略信号"""
        self._strategy_signals.append(signal)

        if strategy := self._strategy_status.get(signal.strategy_id):
            strategy.last_signal = signal
            if signal.signal_type == 'buy':
                strategy.positions[signal.symbol] = strategy.positions.get(signal.symbol, 0) + 1
            elif signal.signal_type == 'sell':
                strategy.positions[signal.symbol] = max(0, strategy.positions.get(signal.symbol, 0) - 1)

        if self._socketio:
            self._socketio.emit('strategy_signal', {
                'strategy_id': signal.strategy_id,
                'symbol': signal.symbol,
                'signal_type': signal.signal_type,
                'price': signal.price,
                'message': signal.message,
                'timestamp': signal.timestamp.isoformat()
            })

    def get_strategy_signals(self, strategy_id: str = None, limit: int = 50) -> List[StrategySignal]:
        """获取策略信号"""
        signals = self._strategy_signals
        if strategy_id:
            signals = [s for s in signals if s.strategy_id == strategy_id]
        return signals[-limit:]

    def _save_strategy_status(self) -> None:
        """保存策略状态到文件"""
        try:
            data = []
            for strategy_id, status in self._strategy_status.items():
                data.append({
                    'strategy_id': strategy_id,
                    'name': status.name,
                    'status': status.status,
                    'mode': status.mode,
                    'monitored_symbols': json.dumps(status.monitored_symbols),
                    'positions': json.dumps(status.positions),
                    'cash': status.cash,
                    'total_asset': status.total_asset,
                    'logs': json.dumps(status.logs[-20:])
                })
            file_path = self._data_dir / 'StrategyStatus.parquet'
            if data:
                pd.DataFrame(data).to_parquet(file_path)
        except Exception as e:
            print(f"保存策略状态失败: {e}")

    def _load_strategy_status(self) -> None:
        """从文件加载策略状态"""
        try:
            file_path = self._data_dir / 'StrategyStatus.parquet'
            if file_path.exists():
                df = pd.read_parquet(file_path)
                for _, row in df.iterrows():
                    status = StrategyStatus(
                        strategy_id=row['strategy_id'],
                        name=row['name'],
                        status=row.get('status', 'stopped'),
                        mode=row.get('mode', 'realtime'),
                        monitored_symbols=json.loads(row.get('monitored_symbols', '[]')),
                        positions=json.loads(row.get('positions', '{}')),
                        cash=row.get('cash', 0),
                        total_asset=row.get('total_asset', 0),
                        logs=json.loads(row.get('logs', '[]'))
                    )
                    self._strategy_status[row['strategy_id']] = status
        except Exception as e:
            print(f"加载策略状态失败: {e}")
