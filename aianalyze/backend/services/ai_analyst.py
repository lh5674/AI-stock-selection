import os
import json
import re
from dotenv import load_dotenv
import dashscope
from dashscope import Generation

load_dotenv()

dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY")


def _call_qwen(prompt: str, max_tokens: int = 1000) -> str:
    """统一调用千问 API"""
    response = Generation.call(
        model="qwen-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        result_format="message",
    )
    if response.status_code == 200:
        return response.output.choices[0].message.content
    else:
        raise Exception(f"Qwen API error: {response.code} — {response.message}")


def analyze_stock(stock_name: str, market: str, history: list, news: list) -> str:
    """AI个股诊断"""
    hist_summary = "\n".join(
        [f"  {d.get('date', d.get('日期',''))}: 收盘={d.get('close', d.get('收盘',''))}"
         for d in history[-10:]]
    )
    news_summary = "\n".join([f"  - {n['title']}" for n in news[:5]])

    prompt = f"""你是一位专业的股票分析师，请对以下股票进行全面分析，用简洁易懂的语言面向散户用户解释。

股票名称: {stock_name}
市场: {market}

近期价格走势（最近10个交易日）:
{hist_summary}

相关新闻:
{news_summary}

请从以下维度分析（每项2-3句话）：
1. 技术面：趋势、支撑位、压力位
2. 基本面：行业地位、近期动态
3. 情绪面：市场情绪、资金关注度
4. 综合建议：给散户的操作参考（注明：仅供参考，不构成投资建议）

回答要简洁，适合手机端阅读，用中文。"""

    return _call_qwen(prompt, max_tokens=1000)


def ai_select_stocks(user_query: str, market: str, sector_data: list) -> str:
    """AI自然语言选股"""
    sector_info = "\n".join(
        [f"  - {s.get('板块名称', s.get('name', ''))}：涨跌幅 {s.get('涨跌幅', s.get('change_pct', ''))}"
         for s in sector_data[:10]]
    )

    prompt = f"""你是一位AI选股助手，根据用户需求和当前市场数据，推荐最合适的投资方向。

用户需求: {user_query}
目标市场: {market}

当前热点板块数据:
{sector_info}

请：
1. 分析用户需求匹配哪些板块/方向
2. 推荐3-5个具体关注方向或个股（A股用股票名+代码，美股用英文名+ticker）
3. 给出每个推荐的简短理由（1-2句）
4. 提示风险（1句）

格式清晰，适合散户阅读，中文回答。
注意：所有推荐仅供参考，不构成投资建议。"""

    return _call_qwen(prompt, max_tokens=1000)


def analyze_market_sentiment(news_list: list) -> dict:
    """AI新闻情绪分析"""
    headlines = "\n".join([f"- {n['title']}" for n in news_list[:15]])

    prompt = f"""分析以下财经新闻标题，判断当前市场情绪。

新闻标题:
{headlines}

请返回JSON格式（只返回JSON，不要其他文字）：
{{
  "sentiment_score": 75,
  "sentiment_label": "偏多",
  "summary": "市场整体情绪简短总结（2句话）",
  "key_themes": ["主题1", "主题2", "主题3"],
  "risk_factors": ["风险1", "风险2"]
}}

sentiment_score范围0-100（0=极度悲观，50=中性，100=极度乐观）"""

    text = _call_qwen(prompt, max_tokens=500)
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return {
        "sentiment_score": 50,
        "sentiment_label": "中性",
        "summary": text,
        "key_themes": [],
        "risk_factors": []
    }