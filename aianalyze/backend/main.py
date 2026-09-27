import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from services.ai_analyst import (
    AIConfigurationError,
    AIServiceError,
    ai_select_stocks,
    analyze_market_sentiment,
    analyze_stock,
)
from services.market_data import (
    MarketDataError,
    get_hot_sectors_a,
    get_sector_stocks,
    get_stock_detail_a,
    get_stock_detail_us,
    get_us_movers,
)
from services.news_scraper import get_finance_news


app = FastAPI(
    title="智选 Alpha API",
    description="面向个人投资者的市场数据与 AI 研究 API",
    version="0.2.0",
)

cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'"
    )
    return response


@app.exception_handler(ValueError)
async def invalid_input_handler(_request: Request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(MarketDataError)
async def market_data_handler(_request: Request, exc: MarketDataError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(AIConfigurationError)
async def ai_configuration_handler(_request: Request, exc: AIConfigurationError):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(AIServiceError)
async def ai_service_handler(_request: Request, exc: AIServiceError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/api/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "service": "智选 Alpha",
        "ai_configured": bool(os.environ.get("DASHSCOPE_API_KEY", "").strip()),
    }


@app.get("/api/sectors/a", tags=["market"])
def sectors_a():
    return {"data": get_hot_sectors_a()}


@app.get("/api/sectors/a/{sector_name}", tags=["market"])
def sector_stocks(sector_name: str):
    return {"data": get_sector_stocks(sector_name)}


@app.get("/api/stock/a/{code}", tags=["market"])
def stock_a(code: str):
    return {"data": get_stock_detail_a(code)}


@app.get("/api/stock/us/{symbol}", tags=["market"])
def stock_us(symbol: str):
    return {"data": get_stock_detail_us(symbol)}


@app.get("/api/movers/us", tags=["market"])
def us_movers():
    return {"data": get_us_movers()}


@app.get("/api/news", tags=["news"])
def news(limit: int = Query(default=12, ge=1, le=30)):
    return {"data": get_finance_news(limit)}


class StockAnalysisRequest(BaseModel):
    stock_name: str = Field(min_length=1, max_length=80)
    market: str = Field(default="A股", pattern="^(A股|美股)$")
    code: str = Field(default="", max_length=12)


@app.post("/api/ai/analyze", tags=["ai"])
def ai_analyze(payload: StockAnalysisRequest):
    news_list = get_finance_news(5)
    if payload.market == "A股":
        detail = get_stock_detail_a(payload.code)
    else:
        detail = get_stock_detail_us(payload.code or payload.stock_name)
    result = analyze_stock(
        payload.stock_name,
        payload.market,
        detail.get("history", []),
        news_list,
    )
    return {"result": result}


class SelectStocksRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    market: str = Field(default="A股", pattern="^(A股|美股)$")


@app.post("/api/ai/select", tags=["ai"])
def ai_select(payload: SelectStocksRequest):
    if payload.market == "A股":
        market_context = get_hot_sectors_a()
    else:
        market_context = [
            {"name": item["name"], "change_pct": item["change_pct"]}
            for item in get_us_movers()
        ]
    result = ai_select_stocks(payload.query, payload.market, market_context)
    return {"result": result}


@app.get("/api/ai/sentiment", tags=["ai"])
def ai_sentiment():
    news_list = get_finance_news(15)
    result = analyze_market_sentiment(news_list)
    return {"data": result, "news": news_list}


frontend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend")
)
if os.path.isdir(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(os.path.join(frontend_path, "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
