from fastapi import FastAPI
import requests

app = FastAPI(title="Delta AI Trading Bot")

BASE_URL = "https://api.india.delta.exchange"

@app.get("/")
def home():
    return {
        "status": "online",
        "bot": "Delta AI Trading Bot",
        "message": "Bot is running successfully"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/market")
def market():
    try:
        response = requests.get(
            f"{BASE_URL}/v2/tickers",
            timeout=20
        )
        response.raise_for_status()

        data = response.json()
        tickers = data.get("result", [])

        selected = []

        for item in tickers:
            symbol = item.get("symbol", "")

            if "BTC" in symbol or "ETH" in symbol:
                selected.append(item)

        return {
            "status": "success",
            "count": len(selected),
            "data": selected
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error)
        }
