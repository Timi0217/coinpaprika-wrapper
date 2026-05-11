import os
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
import httpx


BASE_URL = "https://api.coinpaprika.com/v1"

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=15.0)
    yield
    await http_client.aclose()


app = FastAPI(title="CoinPaprika Wrapper", lifespan=lifespan)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# CoinPaprika uses IDs like "btc-bitcoin", "eth-ethereum"
SYMBOL_TO_ID = {
    "BTC": "btc-bitcoin",
    "ETH": "eth-ethereum",
    "SOL": "sol-solana",
    "ADA": "ada-cardano",
    "DOT": "dot-polkadot",
    "AVAX": "avax-avalanche",
    "MATIC": "matic-polygon",
    "LINK": "link-chainlink",
    "UNI": "uni-uniswap",
    "DOGE": "doge-dogecoin",
    "SHIB": "shib-shiba-inu",
    "XRP": "xrp-xrp",
    "BNB": "bnb-binance-coin",
    "LTC": "ltc-litecoin",
    "ATOM": "atom-cosmos",
    "NEAR": "near-near-protocol",
    "FTM": "ftm-fantom",
    "APT": "apt-aptos",
    "ARB": "arb-arbitrum",
    "OP": "op-optimism",
    "SUI": "sui-sui",
    "INJ": "inj-injective",
    "PEPE": "pepe-pepe",
    "AAVE": "aave-aave",
    "MKR": "mkr-maker",
    "CRV": "crv-curve-dao-token",
    "RUNE": "rune-thorchain",
    "ICP": "icp-internet-computer",
    "FIL": "fil-filecoin",
    "GRT": "grt-the-graph",
    "TAO": "tao-bittensor",
    "RENDER": "rndr-render-token",
    "FET": "fet-fetch-ai",
    "STX": "stx-stacks",
}


async def _cp_request(path: str) -> dict | list:
    """Make a request to CoinPaprika API (no auth needed)."""
    url = f"{BASE_URL}{path}"
    try:
        response = await http_client.get(url)
        if response.status_code == 429:
            raise HTTPException(status_code=429, detail="CoinPaprika rate limit exceeded")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Not found on CoinPaprika")
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Network error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Unexpected error: {str(e)}")


def _resolve_coin_id(symbol: str) -> str:
    """Resolve a symbol to a CoinPaprika coin ID."""
    upper = symbol.upper()
    if upper in SYMBOL_TO_ID:
        return SYMBOL_TO_ID[upper]
    # If it already looks like a coin ID (contains dash), use as-is
    if "-" in symbol:
        return symbol.lower()
    raise HTTPException(
        status_code=404,
        detail=f"Symbol '{symbol}' not found. Supported: {', '.join(sorted(SYMBOL_TO_ID.keys()))}. Or pass a coin ID like 'btc-bitcoin'.",
    )


# ── Endpoints ────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    return {
        "name": "CoinPaprika Wrapper",
        "description": "Crypto project data, team info, on-chain metrics, OHLCV history, and market tickers from CoinPaprika",
        "endpoints": [
            {"path": "/price?symbol=BTC", "description": "Get current crypto price and market data"},
            {"path": "/coin?symbol=BTC", "description": "Get detailed coin info (team, links, tags)"},
            {"path": "/ohlcv?symbol=BTC&days=30", "description": "Get OHLCV historical data"},
            {"path": "/markets?symbol=BTC", "description": "Get exchange markets for a coin"},
            {"path": "/search?query=bitcoin", "description": "Search coins"},
            {"path": "/global", "description": "Global crypto market stats"},
            {"path": "/health", "description": "Health check"},
        ],
        "supported_symbols": sorted(SYMBOL_TO_ID.keys()),
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": _ts()}


@app.get("/price")
async def get_price(symbol: str = Query(..., description="Crypto symbol (e.g., BTC) or coin ID (e.g., btc-bitcoin)")):
    """Get current price and market data for a crypto."""
    coin_id = _resolve_coin_id(symbol)
    data = await _cp_request(f"/tickers/{coin_id}")

    quotes = data.get("quotes", {}).get("USD", {})

    return {
        "symbol": data.get("symbol", symbol.upper()),
        "name": data.get("name"),
        "rank": data.get("rank"),
        "price": quotes.get("price"),
        "currency": "USD",
        "volume_24h": quotes.get("volume_24h"),
        "market_cap": quotes.get("market_cap"),
        "change_1h_pct": quotes.get("percent_change_1h"),
        "change_24h_pct": quotes.get("percent_change_24h"),
        "change_7d_pct": quotes.get("percent_change_7d"),
        "change_30d_pct": quotes.get("percent_change_30d"),
        "ath_price": quotes.get("ath_price"),
        "ath_date": quotes.get("ath_date"),
        "circulating_supply": data.get("circulating_supply"),
        "total_supply": data.get("total_supply"),
        "max_supply": data.get("max_supply"),
        "timestamp": _ts(),
    }


@app.get("/coin")
async def get_coin(symbol: str = Query(..., description="Crypto symbol or coin ID")):
    """Get detailed coin information including team, links, tags."""
    coin_id = _resolve_coin_id(symbol)
    data = await _cp_request(f"/coins/{coin_id}")

    # Extract team
    team = []
    for member in (data.get("team") or [])[:10]:
        team.append({
            "name": member.get("name"),
            "position": member.get("position"),
        })

    # Extract links
    links = {}
    for link_group in (data.get("links") or {}).values():
        if isinstance(link_group, list):
            for link in link_group:
                links[link.get("type", "unknown")] = link.get("url")

    # Extract tags
    tags = [t.get("name") for t in (data.get("tags") or []) if t.get("name")]

    return {
        "symbol": data.get("symbol"),
        "name": data.get("name"),
        "rank": data.get("rank"),
        "type": data.get("type"),
        "is_active": data.get("is_active"),
        "description": data.get("description"),
        "started_at": data.get("started_at"),
        "proof_type": data.get("proof_type"),
        "hash_algorithm": data.get("hash_algorithm"),
        "org_structure": data.get("org_structure"),
        "open_source": data.get("open_source"),
        "team": team,
        "tags": tags,
        "links": links,
        "whitepaper_link": (data.get("whitepaper") or {}).get("link"),
        "timestamp": _ts(),
    }


@app.get("/ohlcv")
async def get_ohlcv(
    symbol: str = Query(..., description="Crypto symbol or coin ID"),
    days: int = Query(30, description="Number of days of history", ge=1, le=365),
):
    """Get OHLCV historical data."""
    coin_id = _resolve_coin_id(symbol)

    end = datetime.now(timezone.utc)
    start = end.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    start = start - timedelta(days=days)

    path = f"/coins/{coin_id}/ohlcv/historical?start={start.strftime('%Y-%m-%d')}&end={end.strftime('%Y-%m-%d')}"
    data = await _cp_request(path)

    if not data:
        raise HTTPException(status_code=404, detail=f"No OHLCV data for {symbol}")

    points = []
    for item in data:
        points.append({
            "date": item.get("time_open", "")[:10],
            "open": item.get("open"),
            "high": item.get("high"),
            "low": item.get("low"),
            "close": item.get("close"),
            "volume": item.get("volume"),
            "market_cap": item.get("market_cap"),
        })

    return {
        "symbol": symbol.upper(),
        "days": days,
        "data": points,
        "timestamp": _ts(),
    }


@app.get("/markets")
async def get_markets(symbol: str = Query(..., description="Crypto symbol or coin ID")):
    """Get exchange markets where this coin trades."""
    coin_id = _resolve_coin_id(symbol)
    data = await _cp_request(f"/coins/{coin_id}/markets")

    if not data:
        return {"symbol": symbol.upper(), "markets": [], "timestamp": _ts()}

    markets = []
    for item in data[:20]:  # Top 20 markets
        markets.append({
            "exchange": item.get("exchange_name"),
            "pair": item.get("pair"),
            "base": item.get("base_currency_name"),
            "quote": item.get("quote_currency_name"),
            "price": item.get("quotes", {}).get("USD", {}).get("price"),
            "volume_24h": item.get("quotes", {}).get("USD", {}).get("volume_24h"),
            "trust_score": item.get("trust_score"),
        })

    return {"symbol": symbol.upper(), "markets": markets, "timestamp": _ts()}


@app.get("/search")
async def search_coins(query: str = Query(..., description="Search query")):
    """Search for coins by name or symbol."""
    data = await _cp_request(f"/search?q={query}")

    results = []
    for item in (data.get("currencies") or [])[:10]:
        results.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "symbol": item.get("symbol"),
            "rank": item.get("rank"),
            "is_active": item.get("is_active"),
        })

    return {"query": query, "results": results, "timestamp": _ts()}


@app.get("/global")
async def get_global():
    """Get global crypto market stats."""
    data = await _cp_request("/global")

    return {
        "total_market_cap_usd": data.get("market_cap_usd"),
        "volume_24h_usd": data.get("volume_24h_usd"),
        "bitcoin_dominance_pct": data.get("bitcoin_dominance_percentage"),
        "active_cryptocurrencies": data.get("cryptocurrencies_number"),
        "market_cap_change_24h_pct": data.get("market_cap_change_24h"),
        "volume_change_24h_pct": data.get("volume_24h_change_24h"),
        "market_cap_ath_value": data.get("market_cap_ath_value"),
        "market_cap_ath_date": data.get("market_cap_ath_date"),
        "timestamp": _ts(),
    }
