# Tiny Donchian Bot

[![make.fun](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![rank](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/Djebrix/tiny-bot-easy/rank.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
[![reward](https://make.fun/badge/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1/Djebrix/tiny-bot-easy/reward.svg)](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)

A Donchian channel breakout bot for hourly Solana prices, written for the
[Tiny Bot, Easy $2: Beat Buy-and-Hold on Solana](https://make.fun/bounty/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1)
bounty on make.fun.

## Strategy

- **Entry:** the close breaks above the highest high of the previous 16 bars.
- **Size:** 10% of equity per symbol, at most 5 open positions, never over the
  25% per-symbol weight cap.
- **Exit:** the close falls below the lowest low of the previous 8 bars, or
  below the position's peak close minus 0.8 × ATR(14).
- No shorts, no leverage, no lookahead: every decision uses only bars the
  harness has already delivered. Orders decided on a batch fill at the next
  bar's open.

## Grade-local result (kit dev window, 136 hourly bars)

| | Net PnL | Trades | Max drawdown |
| --- | --- | --- | --- |
| Tiny Donchian Bot | −42.09 USDC | 29 | 1.12% |
| Buy-and-hold baseline | −869.34 USDC | 7 | 10.92% |

The bot beats buy-and-hold by **+827.25 USDC** on the dev window, and on
rolling 72-bar windows (the final window's length) it beats buy-and-hold in
7 of 9 windows with 10–17 trades each. Two grade-local runs produce
byte-identical action logs (deterministic).

## Run

```sh
python3 main.py
```

Python 3 stdlib only. Speaks `agent-fun/bars-replay/v1` on stdin/stdout via
the vendored `vendor/makefun_bars.py` shim (a byte-identical copy of the
kit's `sdk/makefun_bars.py`).
