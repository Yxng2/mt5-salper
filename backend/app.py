import os
from datetime import datetime, timezone
from collections import deque
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
try:
    from metaapi_cloud_sdk import MetaApi
except ImportError:
    MetaApi = None

load_dotenv()
app = FastAPI(title="XAUUSD MT5 Scalper V1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

METAAPI_TOKEN=os.getenv("METAAPI_TOKEN","")
METAAPI_ACCOUNT_ID=os.getenv("METAAPI_ACCOUNT_ID","")
MT5_LOGIN=os.getenv("MT5_LOGIN","")
MT5_PASSWORD=os.getenv("MT5_PASSWORD","")
MT5_SERVER=os.getenv("MT5_SERVER","")
MT5_SYMBOL=os.getenv("MT5_SYMBOL","XAUUSD")
BOT_ENABLED=os.getenv("BOT_ENABLED","false").lower()=="true"
PAPER_ONLY=os.getenv("PAPER_ONLY","true").lower()=="true"
MAX_TRADES_PER_DAY=int(os.getenv("MAX_TRADES_PER_DAY","10"))

api=None
account=None
connection=None
last_price=None
last_setup=None
paper_trades=deque(maxlen=50)
trades_today=0

class Credentials(BaseModel):
    login:str
    password:str
    server:str
    symbol:str="XAUUSD"

class BotToggle(BaseModel):
    enabled:bool

async def get_connection():
    global api, account, connection
    if not METAAPI_TOKEN or not METAAPI_ACCOUNT_ID:
        raise RuntimeError("MetaApi token/account ID are not configured on the server.")
    if MetaApi is None:
        raise RuntimeError("MetaApi SDK is not installed.")
    if connection is not None:
        return connection
    api=MetaApi(token=METAAPI_TOKEN)
    account=await api.metatrader_account_api.get_account(account_id=METAAPI_ACCOUNT_ID)
    await account.wait_connected()
    connection=account.get_rpc_connection()
    await connection.connect()
    await connection.wait_synchronized()
    return connection

@app.get("/health")
async def health():
    return {"ok":True,"mode":"MT5-CLOUD","paper_only":PAPER_ONLY,"instrument":MT5_SYMBOL,"enabled":BOT_ENABLED,"metaapi_configured":bool(METAAPI_TOKEN and METAAPI_ACCOUNT_ID)}

@app.get("/state")
async def state():
    return {"enabled":BOT_ENABLED,"paper_only":PAPER_ONLY,"symbol":MT5_SYMBOL,"last_price":last_price,"last_setup":last_setup,"trades_today":trades_today,"max_trades_per_day":MAX_TRADES_PER_DAY}

@app.post("/credentials")
async def credentials(c:Credentials):
    global MT5_LOGIN,MT5_PASSWORD,MT5_SERVER,MT5_SYMBOL
    MT5_LOGIN=c.login.strip()
    MT5_PASSWORD=c.password
    MT5_SERVER=c.server.strip()
    MT5_SYMBOL=c.symbol.strip() or "XAUUSD"
    return {"ok":True,"saved":True,"symbol":MT5_SYMBOL}

@app.post("/bot")
async def bot(t:BotToggle):
    global BOT_ENABLED
    BOT_ENABLED=t.enabled
    return {"ok":True,"enabled":BOT_ENABLED,"paper_only":PAPER_ONLY}

@app.get("/account")
async def account_info():
    try:
        return await (await get_connection()).get_account_information()
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))

@app.get("/symbols")
async def symbols():
    try:
        return await (await get_connection()).get_symbols()
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))

@app.get("/price")
async def price():
    global last_price
    try:
        c=await get_connection()
        await c.subscribe_to_market_data(symbol=MT5_SYMBOL)
        last_price=await c.get_symbol_price(MT5_SYMBOL)
        return last_price
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))

@app.post("/paper-order")
async def paper_order(direction:str="BUY",volume:float=0.01):
    global trades_today
    if trades_today>=MAX_TRADES_PER_DAY:
        raise HTTPException(status_code=400,detail="Daily trade limit reached.")
    trade={"time":datetime.now(timezone.utc).isoformat(),"symbol":MT5_SYMBOL,"direction":direction.upper(),"volume":volume,"paper":True}
    paper_trades.appendleft(trade)
    trades_today+=1
    return {"ok":True,"trade":trade}

@app.get("/paper-trades")
async def paper_trades_list():
    return list(paper_trades)

@app.get("/scan")
async def scan():
    global last_setup
    try:
        c=await get_connection()
        await c.subscribe_to_market_data(symbol=MT5_SYMBOL)
        p=await c.get_symbol_price(MT5_SYMBOL)
        last_setup={"signal":"WAIT","reason":"MT5 connected; strategy candle validation comes next.","symbol":MT5_SYMBOL,"price":p}
        return last_setup
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))
