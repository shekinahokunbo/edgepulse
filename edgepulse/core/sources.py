"""Live data feeds for EdgePulse.

EdgePulse is a general real-time monitor: give it any stream of numbers and it
forecasts the next value and flags anomalies. For a deployable demo that works
in real time out of the box, we plug in live cryptocurrency prices from
Coinbase's public spot endpoint — no API key, updates every second, and it's
genuinely live market data rather than a simulation.

Each "channel" is just a named numeric stream; the monitoring pipeline is
completely agnostic to what it's watching (crypto here, but equally a
temperature probe, an accelerometer, or a server metric).
"""

from __future__ import annotations

import requests

# Display name -> Coinbase product id.
CHANNELS: dict[str, str] = {
    "BTC · Bitcoin": "BTC-USD",
    "ETH · Ethereum": "ETH-USD",
    "SOL · Solana": "SOL-USD",
    "DOGE · Dogecoin": "DOGE-USD",
}

_SPOT = "https://api.coinbase.com/v2/prices/{product}/spot"


def fetch_value(channel: str, timeout: float = 4.0) -> float | None:
    """Return the current live price for a channel, or None if unavailable."""
    product = CHANNELS.get(channel)
    if product is None:
        return None
    try:
        resp = requests.get(_SPOT.format(product=product), timeout=timeout)
        resp.raise_for_status()
        return float(resp.json()["data"]["amount"])
    except Exception:
        return None
