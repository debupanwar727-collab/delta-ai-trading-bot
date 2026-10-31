from fastapi import FastAPI
import requests

app = FastAPI(title="Delta AI Trading Bot")

BASE_URL = "https://api.india.delta.exchange"

@app.get("/")
def home():
    return {"status": "online", "bot": "Delta AI Trading Bot"}

@app.get("/market")
def market():
    return get_data({
        "underlying_asset_symbols": "BTC,ETH"
    })

@app.get("/options/{asset}")
def options(asset: str, expiry_date: str = None):
    asset = asset.upper()

    if asset not in ["BTC", "ETH"]:
        return {"error": "Only BTC and ETH are supported"}

    params = {
        "contract_types": "call_options,put_options",
        "underlying_asset_symbols": asset
    }

    if expiry_date:
        params["expiry_date"] = expiry_date

    return get_data(params)

def get_data(params):
    try:
        response = requests.get(
            BASE_URL + "/v2/tickers",
            params=params,
            timeout=20
        )
        response.raise_for_status()
        result = response.json()

        return {
            "status": "success",
            "count": len(result.get("result", [])),
            "data": result.get("result", [])
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
