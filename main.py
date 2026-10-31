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
@app.get("/signal/{asset}")
def trading_signal(asset: str):
    asset = asset.upper()

    if asset not in ["BTC", "ETH"]:
        return {"error": "Only BTC and ETH supported"}

    try:
        result = analysis(asset)

        if result.get("status") != "success":
            return result

        pcr = result.get("pcr")

        if pcr is None:
            signal = "WAIT"
            reason = "OI data unavailable"

        elif pcr >= 1.3:
            signal = "BULLISH"
            reason = "Put OI is relatively higher"

        elif pcr <= 0.7:
            signal = "BEARISH"
            reason = "Call OI is relatively higher"

        else:
            signal = "WAIT"
            reason = "PCR is in neutral range"

        return {
            "asset": asset,
            "signal": signal,
            "pcr": pcr,
            "max_pain": result.get("max_pain"),
            "reason": reason,
            "warning": "PCR-based indication only. Not a guaranteed trade."
        }

    except Exception as e:
        return {"error": str(e)}
@app.get("/trade-plan/{asset}")
def trade_plan(asset: str):
    asset = asset.upper()

    if asset not in ["BTC", "ETH"]:
        return {"error": "Only BTC and ETH supported"}

    try:
        response = requests.get(
            BASE_URL + "/v2/tickers",
            params={"underlying_asset_symbols": asset},
            timeout=20
        )
        response.raise_for_status()

        tickers = response.json().get("result", [])

        futures = [
            x for x in tickers
            if x.get("contract_type") == "perpetual_futures"
        ]

        if not futures:
            return {
                "error": "Live futures price not found",
                "available_tickers": len(tickers)
            }

        ticker = futures[0]
        price = float(
            ticker.get("mark_price") or ticker.get("close") or 0
        )

        if price <= 0:
            return {"error": "Valid live price unavailable"}

        signal_data = trading_signal(asset)
        signal = signal_data.get("signal")

        if signal not in ["BULLISH", "BEARISH"]:
            return {
                "asset": asset,
                "price": price,
                "signal": "WAIT",
                "reason": "No directional signal"
            }

        if signal == "BULLISH":
            sl = price * 0.995
            risk = price - sl
            target1 = price + (risk * 2)
            target2 = price + (risk * 3)
            direction = "BUY"

        else:
            sl = price * 1.005
            risk = sl - price
            target1 = price - (risk * 2)
            target2 = price - (risk * 3)
            direction = "SELL"

        return {
            "asset": asset,
            "market_price": price,
            "direction": direction,
            "entry_reference": price,
            "stop_loss": round(sl, 2),
            "target_1": round(target1, 2),
            "target_2": round(target2, 2),
            "risk_reward": "1:2 and 1:3",
            "mode": "PAPER_ONLY",
            "warning": "Illustrative PCR-based plan. Not a validated trading strategy."
        }

    except Exception as e:
        return {"error": str(e)}
@app.get("/smart-signal/{asset}")
def smart_signal(asset: str):
    import time

    asset = asset.upper()

    if asset not in ["BTC", "ETH"]:
        return {"error": "Only BTC and ETH supported"}

    try:
        ticker_response = requests.get(
            BASE_URL + "/v2/tickers",
            timeout=20
        )
        ticker_response.raise_for_status()

        tickers = ticker_response.json().get("result", [])

        futures = [
            x for x in tickers
            if x.get("contract_type") == "perpetual_futures"
            and asset in x.get("symbol", "").upper()
        ]

        if not futures:
            return {"error": "Futures contract not found"}

        symbol = futures[0]["symbol"]

        end = int(time.time())
        start = end - (100 * 15 * 60)

        candle_response = requests.get(
             BASE_URL + "/v2/history/candles",
            params={
                "symbol": symbol,
                "resolution": "15m",
                "start": start,
                "end": end
            },
            timeout=20
        )
        candle_response.raise_for_status()

        candles = candle_response.json().get("result", [])

        if len(candles) < 50:
            return {"error": "Not enough candle data"}

        candles = sorted(candles, key=lambda x: x["time"])

        closes = [float(x["close"]) for x in candles]
        volumes = [float(x["volume"]) for x in candles]

        def ema(values, period):
            k = 2 / (period + 1)
            value = sum(values[:period]) / period

            for price in values[period:]:
                value = price * k + value * (1 - k)

            return value

        gains = []
        losses = []

        for i in range(len(closes) - 14, len(closes)):
            change = closes[i] - closes[i - 1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))

        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14

        if avg_loss == 0:
            rsi = 100
        else:
            rsi = 100 - (100 / (1 + avg_gain / avg_loss))

        total_volume = sum(volumes)

        if total_volume <= 0:
            return {"error": "Volume data unavailable"}

        vwap = sum(
            (
                (
                    float(x["high"])
                    + float(x["low"])
                    + float(x["close"])
                ) / 3
            ) * float(x["volume"])
            for x in candles
        ) / total_volume

        ema20 = ema(closes, 20)
        ema50 = ema(closes, 50)
        price = closes[-1]

        if (
            price > ema20 > ema50
            and price > vwap
            and 50 < rsi < 70
        ):
            signal = "BUY"

        elif (
            price < ema20 < ema50
            and price < vwap
            and 30 < rsi < 50
        ):
            signal = "SELL"

        else:
            signal = "WAIT"

        return {
            "asset": asset,
            "timeframe": "15m",
            "price": price,
            "ema20": round(ema20, 2),
            "ema50": round(ema50, 2),
            "vwap": round(vwap, 2),
            "rsi": round(rsi, 2),
            "smart_signal": signal,
            "warning": "Experimental indicator signal. Paper trading only."
        }

    except Exception as e:
        return {"error": str(e)}
