import os
from datetime import datetime, timezone
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
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


HOME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CoinPaprika Wrapper</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  background:#0a0a0a;
  color:#e0e0e0;
  line-height:1.5;
  padding:20px;
  opacity:0;
  animation:fadeIn 0.6s forwards;
}
@keyframes fadeIn{to{opacity:1}}
.container{max-width:640px;margin:0 auto}
.card{
  background:rgba(255,255,255,.03);
  border:1px solid rgba(255,255,255,.07);
  border-radius:16px;
  padding:24px;
  margin-bottom:20px;
}
.header{
  display:flex;
  justify-content:space-between;
  align-items:center;
  margin-bottom:8px;
}
.title{
  font-family:"Courier New",monospace;
  font-size:28px;
  color:#00D4AA;
  font-weight:700;
}
.health{
  font-family:"Courier New",monospace;
  font-size:13px;
  color:#555;
  display:flex;
  align-items:center;
  gap:6px;
}
.health .d{
  width:8px;
  height:8px;
  border-radius:50%;
  background:#555;
  transition:background .3s;
}
.health .d.on{
  background:#4CAF50;
}
.subtitle{
  color:#888;
  font-size:14px;
  margin-bottom:24px;
}
.global-stats{
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:16px;
  margin-bottom:24px;
}
.stat-box{
  text-align:center;
  padding:12px;
  background:rgba(0,212,170,.05);
  border:1px solid rgba(0,212,170,.15);
  border-radius:8px;
}
.stat-label{
  font-size:11px;
  color:#888;
  text-transform:uppercase;
  letter-spacing:0.5px;
  margin-bottom:4px;
}
.stat-value{
  font-family:"Courier New",monospace;
  font-size:18px;
  font-weight:bold;
  color:#00D4AA;
}
.crypto-grid{
  display:grid;
  grid-template-columns:repeat(2,1fr);
  gap:12px;
  margin-bottom:24px;
}
.crypto-card{
  background:rgba(255,255,255,.02);
  border:1px solid rgba(255,255,255,.06);
  border-radius:8px;
  padding:12px;
  display:flex;
  align-items:center;
  gap:10px;
  transition:background 0.2s;
}
.crypto-card:hover{background:rgba(255,255,255,.04)}
.icon-circle{
  width:32px;
  height:32px;
  border-radius:50%;
  background:#00D4AA;
  color:#0a0a0a;
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight:bold;
  font-size:14px;
  flex-shrink:0;
}
.crypto-info{flex:1;min-width:0}
.crypto-symbol{
  font-weight:bold;
  font-size:13px;
  color:#fff;
}
.crypto-price{
  font-family:"Courier New",monospace;
  font-size:12px;
  color:#aaa;
}
.crypto-change{
  font-family:"Courier New",monospace;
  font-size:12px;
  font-weight:600;
  white-space:nowrap;
}
.crypto-change.positive{color:#00D4AA}
.crypto-change.negative{color:#ff4444}
.form-section{margin-top:20px}
.input-group{
  display:flex;
  gap:8px;
  margin-bottom:12px;
}
.input-group input{
  flex:1;
  background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.1);
  border-radius:8px;
  padding:10px 14px;
  color:#fff;
  font-size:14px;
}
.input-group input:focus{
  outline:none;
  border-color:#00D4AA;
}
.input-group button{
  background:#00D4AA;
  color:#0a0a0a;
  border:none;
  border-radius:8px;
  padding:10px 20px;
  font-weight:600;
  cursor:pointer;
  transition:opacity 0.2s;
}
.input-group button:hover{opacity:0.85}
.try-section{
  font-size:13px;
  color:#666;
}
.try-section span{
  color:#00D4AA;
  cursor:pointer;
  text-decoration:underline;
  margin:0 4px;
}
.try-section span:hover{color:#00ffcc}
.result{
  margin-top:16px;
  padding:12px;
  background:rgba(0,212,170,.08);
  border:1px solid rgba(0,212,170,.2);
  border-radius:8px;
  font-family:"Courier New",monospace;
  font-size:12px;
  color:#e0e0e0;
  white-space:pre-wrap;
  word-break:break-all;
  max-height:300px;
  overflow-y:auto;
  display:none;
}
.loading{color:#888;text-align:center;padding:12px;font-size:13px}
</style>
</head>
<body>
<div class="container">
  <div class="card">
    <div class="header">
      <div class="title">CoinPaprika</div>
      <div class="health"><span class="d" id="dot"></span><span id="health-text">connecting...</span></div>
    </div>
    <div class="subtitle">Crypto fundamentals, on-chain metrics, and OHLCV history</div>

    <div class="global-stats" id="globalStats">
      <div class="stat-box">
        <div class="stat-label">Market Cap</div>
        <div class="stat-value" id="marketCap">...</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">24h Volume</div>
        <div class="stat-value" id="volume24h">...</div>
      </div>
      <div class="stat-box">
        <div class="stat-label">BTC Dom.</div>
        <div class="stat-value" id="btcDom">...</div>
      </div>
    </div>

    <div class="crypto-grid" id="cryptoGrid">
      <div class="loading">Loading crypto prices...</div>
    </div>

    <div class="form-section">
      <div class="input-group">
        <input type="text" id="symbolInput" placeholder="BTC" />
        <button onclick="fetchPrice()">\\u2192 price</button>
      </div>
      <div class="try-section">
        Try:
        <span onclick="trySymbol('ETH')">ETH</span>\\u00B7
        <span onclick="trySymbol('SOL')">SOL</span>\\u00B7
        <span onclick="trySymbol('DOGE')">DOGE</span>\\u00B7
        <span onclick="trySymbol('ADA')">ADA</span>\\u00B7
        <span onclick="trySymbol('XRP')">XRP</span>
      </div>
      <div class="result" id="result"></div>
    </div>
  </div>
</div>

<script>
const symbols = ['BTC', 'ETH', 'SOL', 'XRP'];

async function checkHealth() {
  const t0 = Date.now();
  try {
    await fetch('/health');
    const ms = Date.now() - t0;
    document.getElementById('dot').classList.add('on');
    document.getElementById('health-text').textContent = 'online \\u00B7 ' + ms + 'ms';
  } catch {
    document.getElementById('health-text').textContent = 'offline';
  }
}

async function loadDashboard() {
  try {
    const res = await fetch('/dashboard');
    const data = await res.json();

    // Update global stats
    const mcap = data.global.total_market_cap_usd;
    const vol = data.global.volume_24h_usd;
    const btcDom = data.global.bitcoin_dominance_pct;

    document.getElementById('marketCap').textContent = mcap ?
      '$' + (mcap / 1e12).toFixed(2) + 'T' : 'N/A';
    document.getElementById('volume24h').textContent = vol ?
      '$' + (vol / 1e9).toFixed(1) + 'B' : 'N/A';
    document.getElementById('btcDom').textContent = btcDom ?
      btcDom.toFixed(1) + '%' : 'N/A';

    // Update crypto prices
    const grid = document.getElementById('cryptoGrid');
    grid.innerHTML = '';

    for (const crypto of data.prices) {
      if (crypto.error) {
        console.error('Error loading ' + crypto.symbol + ':', crypto.error);
        continue;
      }

      const card = document.createElement('div');
      card.className = 'crypto-card';

      const icon = document.createElement('div');
      icon.className = 'icon-circle';
      icon.textContent = crypto.symbol[0];

      const info = document.createElement('div');
      info.className = 'crypto-info';

      const symbolDiv = document.createElement('div');
      symbolDiv.className = 'crypto-symbol';
      symbolDiv.textContent = crypto.symbol;

      const priceDiv = document.createElement('div');
      priceDiv.className = 'crypto-price';
      priceDiv.textContent = crypto.price ? '$' + crypto.price.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
      }) : 'N/A';

      info.appendChild(symbolDiv);
      info.appendChild(priceDiv);

      const changeDiv = document.createElement('div');
      changeDiv.className = 'crypto-change';
      const change = crypto.change_24h_pct;
      if (change !== null && change !== undefined) {
        const arrow = change >= 0 ? '\\u2191' : '\\u2193';
        changeDiv.textContent = arrow + ' ' + Math.abs(change).toFixed(1) + '%';
        changeDiv.classList.add(change >= 0 ? 'positive' : 'negative');
      } else {
        changeDiv.textContent = 'N/A';
        changeDiv.style.color = '#666';
      }

      card.appendChild(icon);
      card.appendChild(info);
      card.appendChild(changeDiv);
      grid.appendChild(card);
    }
  } catch (err) {
    console.error('Dashboard error:', err);
  }
}

async function fetchPrice() {
  const input = document.getElementById('symbolInput');
  const result = document.getElementById('result');
  const symbol = input.value.trim().toUpperCase();

  if (!symbol) {
    alert('Please enter a symbol');
    return;
  }

  result.style.display = 'block';
  result.textContent = 'Loading...';

  try {
    const res = await fetch('/price?symbol=' + symbol);
    const data = await res.json();
    result.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    result.textContent = 'Error: ' + err.message;
  }
}

function trySymbol(sym) {
  document.getElementById('symbolInput').value = sym;
  fetchPrice();
}

document.getElementById('symbolInput').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') fetchPrice();
});

checkHealth();
loadDashboard();
</script>
</body>
</html>
"""


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
    return HTMLResponse(content=HOME_HTML)


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


@app.get("/dashboard")
async def get_dashboard():
    """Get all homepage data in a single call (global stats + crypto prices)."""
    import asyncio

    # Fetch global stats
    global_data = await _cp_request("/global")

    # Small delay
    await asyncio.sleep(0.2)

    # Fetch prices for homepage symbols
    symbols = ['BTC', 'ETH', 'SOL', 'XRP']
    prices = []

    for symbol in symbols:
        try:
            coin_id = _resolve_coin_id(symbol)
            data = await _cp_request(f"/tickers/{coin_id}")
            quotes = data.get("quotes", {}).get("USD", {})

            prices.append({
                "symbol": data.get("symbol", symbol),
                "name": data.get("name"),
                "price": quotes.get("price"),
                "change_24h_pct": quotes.get("percent_change_24h"),
                "volume_24h": quotes.get("volume_24h"),
                "market_cap": quotes.get("market_cap"),
            })

            # Small delay between requests
            await asyncio.sleep(0.2)
        except Exception as e:
            # Continue on errors, just skip this symbol
            prices.append({
                "symbol": symbol,
                "error": str(e)
            })

    return {
        "global": {
            "total_market_cap_usd": global_data.get("market_cap_usd"),
            "volume_24h_usd": global_data.get("volume_24h_usd"),
            "bitcoin_dominance_pct": global_data.get("bitcoin_dominance_percentage"),
        },
        "prices": prices,
        "timestamp": _ts(),
    }
