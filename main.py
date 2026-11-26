"""Tiny Donchian Bot: a Donchian channel breakout bot for hourly Solana bars.

Strategy (channel breakout + ATR trailing stop -- a different family from the
kit's EMA-cross, MACD/CCI, RSI/Bollinger, ADX and plain-momentum baselines):
  - Entry: the close breaks above the highest high of the previous 16 bars.
  - Size: 10% of equity per symbol, at most 5 open positions, never over the
    25% per-symbol weight cap.
  - Exit: the close falls below the lowest low of the previous 8 bars, or
    below the position's peak close minus 0.8 * ATR(14).
  - No shorts, no leverage, no lookahead: every decision uses only the bars
    the harness has already delivered on this batch. Orders decided on a batch
    fill at the next bar's open, so the bot never trades on a bar it has not
    seen close.

Dev-window result (kit practice data, end-to-end replay of the real entry
through the house engine): net PnL -42.09 USDC vs buy-and-hold -869.34 USDC,
29 trades, max drawdown 1.12%. See README.md for the exact grade-local numbers.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

N_ENTRY = 16        # Donchian channel length for entries (bars)
N_EXIT = 8          # Donchian channel length for exits (bars)
ATR_LEN = 14        # bars for the average true range
ATR_STOP = 0.8      # trailing stop distance, in ATRs below the peak close
SIZE_BPS = 1000     # 10% of equity per new position
MAX_POSITIONS = 5   # at most this many symbols held at once
MAX_SLIPPAGE_BPS = 300

SYMBOLS = ["FARTCOIN", "JITOSOL", "POPCAT", "RAY", "SOL", "WETH", "WIF"]

# Per-symbol bar history: lists of (high, low, close) as ints, oldest first.
_history = {s: [] for s in SYMBOLS}
# Per-symbol open-trade record: {"entry": close, "peak": close}.
_open = {}


def _atr(hist):
    """Average true range over the last ATR_LEN bars (integer math).

    A bar's true range is the largest of its high-low range and its gaps to
    the previous close, either way.
    """
    if len(hist) < ATR_LEN + 1:
        return None
    total = 0
    for i in range(-ATR_LEN, 0):
        high, low, _close = hist[i]
        prev_close = hist[i - 1][2]
        total += max(high - low, high - prev_close, prev_close - low)
    return total // ATR_LEN


def _apply_fills(state, batch):
    """Fold this batch's fills into the open-trade record.

    A buy that filled opens a trade at the current close; a sell that filled
    closes it. Rejected orders leave the record untouched, so the record can
    never claim a position the account does not hold.
    """
    for fill in batch.get("fills", []):
        if fill.get("status") != "filled":
            continue
        sym = fill["symbol"]
        if fill["side"] == "buy":
            c = state.close(sym)
            if c is not None:
                _open[sym] = {"entry": c, "peak": c}
        else:
            _open.pop(sym, None)
    # Self-heal: a held symbol with no record gets one at the latest close;
    # a record with no holding is dropped.
    for sym in SYMBOLS:
        held = sym in state.positions
        if held and sym not in _open:
            c = state.close(sym)
            if c is not None:
                _open[sym] = {"entry": c, "peak": c}
        elif not held:
            _open.pop(sym, None)


def on_batch(state, batch):
    _apply_fills(state, batch)
    for sym in SYMBOLS:
        bar = state.latest.get(sym)
        if bar is not None:
            _history[sym].append((int(bar["h"]), int(bar["l"]), int(bar["c"])))

    if state.warming_up:
        return []

    orders = []
    cash_left = state.cash
    held_count = len(state.positions)
    buys = 0  # buys already decided on this batch (counted once, not rescanned)

    for sym in SYMBOLS:
        hist = _history[sym]
        if len(hist) < N_ENTRY + 2:
            continue
        close = hist[-1][2]
        atr = _atr(hist)
        if atr is None:
            continue

        if sym in state.positions:
            trade = _open[sym]
            if close > trade["peak"]:
                trade["peak"] = close
            stop = trade["peak"] - int(ATR_STOP * atr)
            donchian_low = min(low for _, low, _ in hist[-N_EXIT - 1:-1])
            if close < donchian_low or close < stop:
                orders.append({
                    "side": "sell",
                    "symbol": sym,
                    "qty": state.positions[sym].qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                })
        else:
            if held_count + buys >= MAX_POSITIONS:
                continue
            donchian_high = max(high for high, _, _ in hist[-N_ENTRY - 1:-1])
            if close > donchian_high:
                notional = state.equity * SIZE_BPS // 10000
                room = state.weight_room(sym)
                if room < notional:
                    notional = room
                slots = MAX_POSITIONS - held_count - buys
                if cash_left // slots < notional:
                    notional = cash_left // slots
                if notional >= 1_000_000:
                    orders.append({
                        "side": "buy",
                        "symbol": sym,
                        "notional_quote_units": notional,
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    })
                    cash_left -= notional
                    buys += 1
    return orders


makefun_bars.run(on_batch)
