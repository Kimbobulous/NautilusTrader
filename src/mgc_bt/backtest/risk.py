from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from mgc_bt.config import RiskConfig

MGC_DOLLARS_PER_POINT = 10.0


@dataclass
class RiskManager:
    max_loss_per_trade_dollars: float
    max_daily_trades: int
    max_daily_loss_dollars: float
    max_consecutive_losses: int
    max_drawdown_pct: float
    daily_trade_count: int = 0
    daily_pnl: float = 0.0
    consecutive_losses: int = 0
    trading_halted_for_session: bool = False
    equity_peak: float | None = None
    session_start_equity: float | None = None
    current_session_date: datetime.date | None = None
    _position_open: bool = False
    _entry_equity: float | None = None

    @classmethod
    def from_config(cls, config: RiskConfig) -> RiskManager:
        return cls(
            max_loss_per_trade_dollars=config.max_loss_per_trade_dollars,
            max_daily_trades=config.max_daily_trades,
            max_daily_loss_dollars=config.max_daily_loss_dollars,
            max_consecutive_losses=config.max_consecutive_losses,
            max_drawdown_pct=config.max_drawdown_pct,
        )

    def can_enter(self, direction, stop_distance: float, account_equity: float) -> bool:
        del direction
        self._finalize_closed_trade(account_equity)

        if self.trading_halted_for_session:
            return False
        if (stop_distance * MGC_DOLLARS_PER_POINT) > self.max_loss_per_trade_dollars:
            return False
        if self.daily_trade_count >= self.max_daily_trades:
            return False
        if self.daily_pnl <= -abs(self.max_daily_loss_dollars):
            return False
        if self.consecutive_losses >= self.max_consecutive_losses:
            return False
        self.daily_trade_count += 1
        self._position_open = True
        self._entry_equity = account_equity
        return True

    def should_exit(self, position, current_bar, account_equity: float) -> bool:
        del position
        self._sync_session(int(current_bar.ts_event_ns), account_equity)
        self._position_open = True
        if self._entry_equity is None:
            self._entry_equity = account_equity

        if self.equity_peak is not None and self.equity_peak > 0:
            drawdown_pct = ((self.equity_peak - account_equity) / self.equity_peak) * 100.0
            if drawdown_pct >= self.max_drawdown_pct:
                self.trading_halted_for_session = True
                return True

        if self.daily_pnl <= -abs(self.max_daily_loss_dollars):
            self.trading_halted_for_session = True
            return True

        return False

    def _sync_session(self, ts_event_ns: int, account_equity: float) -> None:
        session_date = datetime.fromtimestamp(ts_event_ns / 1_000_000_000, tz=UTC).date()
        if self.current_session_date != session_date:
            self.current_session_date = session_date
            self.daily_trade_count = 0
            self.daily_pnl = 0.0
            self.consecutive_losses = 0
            self.trading_halted_for_session = False
            self.session_start_equity = account_equity
            self.equity_peak = account_equity
            return

        if self.equity_peak is None:
            self.equity_peak = account_equity
        else:
            self.equity_peak = max(self.equity_peak, account_equity)

        if self.session_start_equity is None:
            self.session_start_equity = account_equity
        self.daily_pnl = account_equity - self.session_start_equity

    def _finalize_closed_trade(self, account_equity: float) -> None:
        if not self._position_open or self._entry_equity is None:
            return

        trade_pnl = account_equity - self._entry_equity
        self.consecutive_losses = self.consecutive_losses + 1 if trade_pnl < 0 else 0
        self._position_open = False
        self._entry_equity = None
