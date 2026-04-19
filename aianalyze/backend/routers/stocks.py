from fastapi import APIRouter
from services.market_data import (
    get_hot_sectors_a, get_sector_stocks,
    get_stock_detail_a, get_stock_detail_us, get_us_movers
)

router = APIRouter(prefix="/api", tags=["stocks"])

@router.get("/sectors/a")
def sectors_a():
    return {"data": get_hot_sectors_a()}

@router.get("/sectors/a/{sector_name}")
def sector_stocks(sector_name: str):
    return {"data": get_sector_stocks(sector_name)}

@router.get("/stock/a/{code}")
def stock_a(code: str):
    return {"data": get_stock_detail_a(code)}

@router.get("/stock/us/{symbol}")
def stock_us(symbol: str):
    return {"data": get_stock_detail_us(symbol.upper())}

@router.get("/movers/us")
def us_movers():
    return {"data": get_us_movers()}