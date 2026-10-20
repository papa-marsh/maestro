from dataclasses import dataclass
from math import isfinite

import requests

from scripts.config.secrets import FINNHUB_TOKEN

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"

SPY_SYMBOL = "SPY"
NET_SYMBOL = "NET"


@dataclass
class FinnhubResponse:
    """
    Stock quote as returned from the Finnhub API.
    c=Current Price, d=Change, dp=Percent Change,
    h=High, l=Low, o=Open, pc=Previous Close, t=Update Timestamp
    """

    c: float  # Current Price
    d: float  # Change
    dp: float  # Percent Change
    h: float  # High
    l: float  # Low
    o: float  # Open
    pc: float  # Previous Close
    t: float  # Update Timestamp


def get_stock_quote(symbol: str = SPY_SYMBOL) -> FinnhubResponse:
    """Returns a stock quote for the given stock symbol"""
    url = f"{FINNHUB_BASE_URL}/quote"
    params = {"symbol": symbol.upper(), "token": FINNHUB_TOKEN}

    response = requests.get(url, params, timeout=30)
    quote = FinnhubResponse(**response.json())

    return quote


def get_private_share_price(symbol: str) -> float:
    """Read the latest indicative private-market price from Yahoo's chart feed."""
    response = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"interval": "1d", "range": "5d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    response.raise_for_status()
    price = float(response.json()["chart"]["result"][0]["meta"]["regularMarketPrice"])
    if not isfinite(price) or price <= 0:
        raise ValueError
    return price
