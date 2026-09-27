# XAUUSD MT5 Scalper V1

New MT5/cloud version. Architecture: MT5 broker account -> MetaApi cloud -> FastAPI backend -> web dashboard.

Safety defaults: PAPER_ONLY=true and BOT_ENABLED=false. The current paper-order endpoint does not send a broker order.

Render:
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app:app --host 0.0.0.0 --port $PORT

Required backend secrets:
METAAPI_TOKEN
METAAPI_ACCOUNT_ID

The dashboard accepts MT5 Login, Password, Server and Symbol. Credentials are kept only in process memory in this starter and are never returned by the API.

The strategy is intentionally not live-trading yet. First verify MT5 cloud connection and XAUUSD symbol/quotes, then add and test the candle-based scalping engine.
