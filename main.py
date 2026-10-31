from fastapi import FastAPI
import requests

app = FastAPI(title="Delta AI Trading Bot")

BASE_URL = "https://api.india.delta.exchange"

def fetch_options(asset, expiry=None):
    params = {
        "contract_types": "call_options,put_options",
        "underlying_asset_symbols": asset
    }

    if expiry:
        params["expiry_date"] = expiry

    r = requests.get(
        BASE_URL + "/v2/tickers",
        params=params,
        timeout=20
    )
    r.raise_for_status()
    return r.json().get("result", [])

@app.get("/")
def home():
    return {"status": "online", "bot": "Delta AI Trading Bot"}

@app.get("/market")
def market():
    try:
        r = requests.get(
            BASE_URL + "/v2/tickers",
            params={"underlying_asset_symbols": "BTC,ETH"},
            timeout=20
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}

@app.get("/options/{asset}")
def options(asset: str, expiry: str = None):
    asset = asset.upper()

    if asset not in ["BTC", "ETH"]:
        return {"error": "Use BTC or ETH"}

    try:
        data = fetch_options(asset, expiry)
        return {"status": "success", "count": len(data), "data": data}
    except Exception as e:
        return {"error": str(e)}

@app.get("/analysis/{asset}")
def analysis(asset: str, expiry: str = None):
    asset = asset.upper()

    if asset not in ["BTC", "ETH"]:
        return {"error": "Use BTC or ETH"}

    try:
        data = fetch_options(asset, expiry)

        calls = []
        puts = []

        for item in data:
            oi = float(item.get("oi") or 0)
            strike = float(item.get("strike_price") or 0)

            item_data = {
                "symbol": item.get("symbol"),
                "strike": strike,
                "oi": oi,
                "ltp": item.get("close"),
                "greeks": item.get("greeks", {})
            }

            if item.get("contract_type") == "call_options":
                calls.append(item_data)

            elif item.get("contract_type") == "put_options":
                puts.append(item_data)

        call_oi = sum(x["oi"] for x in calls)
        put_oi = sum(x["oi"] for x in puts)

        pcr = put_oi / call_oi if call_oi else None

        strikes = sorted(set(
            x["strike"] for x in calls + puts if x["strike"] > 0
        ))

        max_pain = None
        min_payout = None

        if strikes:
            payouts = {}

            for price in strikes:
                call_loss = sum(
                    max(price - x["strike"], 0) * x["oi"]
                    for x in calls
                )

                put_loss = sum(
                    max(x["strike"] - price, 0) * x["oi"]
                    for x in puts
                )

                payouts[price] = call_loss + put_loss

            max_pain = min(payouts, key=payouts.get)
            min_payout = payouts[max_pain]

        return {
            "status": "success",
            "asset": asset,
            "total_call_oi": call_oi,
            "total_put_oi": put_oi,
            "pcr": pcr,
            "max_pain": max_pain,
            "estimated_min_payout": min_payout,
            "calls": calls,
            "puts": puts
        }

    except Exception as e:
        return {"error": str(e)}
@app.get("/gold-contracts")
def gold_contracts():
    try:
        response = requests.get(
            BASE_URL + "/v2/products",
            params={"page_size": 50},
            timeout=20
        )
        response.raise_for_status()

        products = response.json().get("result", [])

        matches = []

        for p in products:
            text = (
                str(p.get("symbol", "")) + " " +
                str(p.get("description", "")) + " " +
                str(p.get("underlying_asset_symbol", ""))
            ).lower()

            if "gold" in text or "xau" in text:
                matches.append(p)

        return {
            "status": "success",
            "count": len(matches),
            "contracts": matches
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
