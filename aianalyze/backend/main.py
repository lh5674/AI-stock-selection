import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from services.market_data import (
    get_hot_sectors_a, get_sector_stocks,
    get_stock_detail_a, get_stock_detail_us, get_us_movers
)
from services.news_scraper import get_finance_news
from services.ai_analyst import analyze_stock, ai_select_stocks, analyze_market_sentiment

app = FastAPI(title="AI选股助手")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Market Data ───────────────────────────────────────────────

@app.get("/api/sectors/a")
def sectors_a():
    return {"data": get_hot_sectors_a()}

@app.get("/api/sectors/a/{sector_name}")
def sector_stocks(sector_name: str):
    return {"data": get_sector_stocks(sector_name)}

@app.get("/api/stock/a/{code}")
def stock_a(code: str):
    return {"data": get_stock_detail_a(code)}

@app.get("/api/stock/us/{symbol}")
def stock_us(symbol: str):
    return {"data": get_stock_detail_us(symbol.upper())}

@app.get("/api/movers/us")
def us_movers():
    return {"data": get_us_movers()}

# ── News ──────────────────────────────────────────────────────

@app.get("/api/news")
def news():
    return {"data": get_finance_news()}

# ── AI ───────────────────────────────────────────────────────

class StockAnalysisReq(BaseModel):
    stock_name: str
    market: str = "A股"
    code: str = ""

@app.post("/api/ai/analyze")
def ai_analyze(req: StockAnalysisReq):
    news_list = get_finance_news(5)
    if req.market == "A股" and req.code:
        detail = get_stock_detail_a(req.code)
        history = detail.get("history", [])
    else:
        detail = get_stock_detail_us(req.stock_name)
        history = detail.get("history", [])
    result = analyze_stock(req.stock_name, req.market, history, news_list)
    return {"result": result}


class SelectStocksReq(BaseModel):
    query: str
    market: str = "A股"

@app.post("/api/ai/select")
def ai_select(req: SelectStocksReq):
    if req.market == "A股":
        sectors = get_hot_sectors_a()
    else:
        sectors = [
            {"name": s["name"], "change_pct": s["change_pct"]}
            for s in get_us_movers()
        ]
    result = ai_select_stocks(req.query, req.market, sectors)
    return {"result": result}


@app.get("/api/ai/sentiment")
def ai_sentiment():
    news_list = get_finance_news(15)
    result = analyze_market_sentiment(news_list)
    return {"data": result, "news": news_list}

# ── Serve Frontend ────────────────────────────────────────────

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    def root():
        return FileResponse(os.path.join(frontend_path, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)