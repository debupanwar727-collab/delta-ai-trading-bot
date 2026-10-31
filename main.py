from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("Delta AI Trading")

BASE_URL = "https://api.india.delta.exchange"

@mcp.tool()
def get_btc_eth_market_data():
    """Get live BTC and ETH market data from Delta Exchange."""
    try:
        response = requests.get(
            BASE_URL + "/v2/tickers",
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        return data.get("result", [])
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_server_status():
    """Check whether the trading assistant is running."""
    return {"status": "online"}

app = mcp.streamable_http_app()
