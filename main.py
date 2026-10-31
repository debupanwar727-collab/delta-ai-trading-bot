from fastapi import FastAPI
import requests

app = FastAPI()

BASE_URL = "https://api.india.delta.exchange"

@app.get("/")
def home():
    return {"status": "AI Trading Bot Running"}

@app.get("/market")
def market():
    try:
        r = requests.get(
            BASE_URL + "/v2/tickers",
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}
