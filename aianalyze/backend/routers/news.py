from fastapi import APIRouter
from services.news_scraper import get_finance_news

router = APIRouter(prefix="/api", tags=["news"])

@router.get("/news")
def news(limit: int = 15):
    return {"data": get_finance_news(limit)}