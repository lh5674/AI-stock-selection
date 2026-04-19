from fastapi import APIRouter
from pydantic import BaseModel
from services.market_data import get_hot_sectors_a, get_us_movers
from services.news_scraper import get_finance_news
from services.ai_analyst import analyze_stock, ai_select_stocks, analyze_market_sentiment

router = APIRouter(prefix="/api/ai", tags=["ai"])

class StockAnalysisReq(BaseModel):
    stock_name: str
    market: str = "A股"
    code: str = ""

class SelectStocksReq(BaseModel):
    query: str
    market: str = "A股"

@router.post("/analyze")
def ai_analyze(req: StockAnalysisReq):
    news_list = get_finance_news(5)
    if req.market == "A股" and req.code:
        from services.market_data import get_stock_detail_a
        detail = get_stock_detail_a(req.code)
        history = detail.get("history", [])
    else:
        from services.market_data import get_stock_detail_us
        detail = get_stock_detail_us(req.stock_name)
        history = detail.get("history", [])
    result = analyze_stock(req.stock_name, req.market, history, news_list)
    return {"result": result}

@router.post("/select")
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

@router.get("/sentiment")
def ai_sentiment():
    news_list = get_finance_news(15)
    result = analyze_market_sentiment(news_list)
    return {"data": result, "news": news_list}