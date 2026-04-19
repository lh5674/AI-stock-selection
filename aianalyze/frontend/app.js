const API = ""
let currentMarket = "A股"

// ── 市场切换 ──────────────────────────────────────────────────
function switchMarket(market, btn) {
  currentMarket = market
  document.querySelectorAll(".mkt-btn").forEach(b => b.classList.remove("active"))
  btn.classList.add("active")
  loadSectors()
}

// ── 热点板块 ──────────────────────────────────────────────────
async function loadSectors() {
  const grid = document.getElementById("sector-grid")
  grid.innerHTML = '<div class="loading">加载中...</div>'
  try {
    const endpoint = currentMarket === "A股" ? "/api/sectors/a" : "/api/movers/us"
    const res  = await fetch(API + endpoint)
    const json = await res.json()
    const data = json.data || []
    if (!data.length) {
      grid.innerHTML = '<div class="loading">暂无数据</div>'
      return
    }
    grid.innerHTML = data.map(s => {
      const name   = s["板块名称"] || s.name || s.symbol || ""
      const price  = s["最新价"]   || s.price || ""
      const change = parseFloat(s["涨跌幅"] || s.change_pct || 0)
      const cls    = change >= 0 ? "up" : "dn"
      const sign   = change >= 0 ? "+" : ""
      return `<div class="sector-item" onclick="fillQuery('${name}')">
        <div class="sector-name">${name}</div>
        ${price ? `<div class="sector-price">${price}</div>` : ""}
        <div class="sector-change ${cls}">${sign}${change.toFixed(2)}%</div>
      </div>`
    }).join("")
  } catch(e) {
    console.error("loadSectors error:", e)
    grid.innerHTML = '<div class="loading">加载失败，请刷新重试</div>'
  }
}

function fillQuery(name) {
  document.getElementById("ai-query").value = `帮我找${name}相关的强势股`
}

// ── 新闻 ──────────────────────────────────────────────────────
async function loadNews() {
  const newsList = document.getElementById("news-list")
  if (!newsList) return
  newsList.innerHTML = '<div class="loading">加载新闻中...</div>'
  try {
    const res  = await fetch(API + "/api/news")
    const json = await res.json()
    const news = json.data || []
    console.log("[news] received:", news.length, news)
    if (!news.length) {
      newsList.innerHTML = '<div class="loading">暂无新闻，请刷新重试</div>'
      return
    }
    renderNews(newsList, news)
  } catch(e) {
    console.error("[news] error:", e)
    newsList.innerHTML = `<div class="loading">新闻加载失败: ${e.message}</div>`
  }
}

function renderNews(container, news) {
  container.innerHTML = news.map(n => `
    <div class="news-item">
      <div class="news-title">
        ${n.source ? `<span class="news-source">${n.source}</span>` : ""}
        <a href="${n.url || '#'}" target="_blank" rel="noopener">${n.title || ''}</a>
      </div>
      <div class="news-time">${n.time || ''}</div>
    </div>
  `).join("")
}

// ── 市场情绪 ──────────────────────────────────────────────────
async function loadSentiment() {
  try {
    const res  = await fetch(API + "/api/ai/sentiment")
    const json = await res.json()
    const d    = json.data || {}
    const score = d.sentiment_score || 50

    const fill = document.getElementById("s-fill")
    const ss   = document.getElementById("s-score")
    const stag = document.getElementById("s-tag")

    if (fill) {
      fill.style.width      = score + "%"
      fill.style.background = score > 60 ? "#34c759" : score < 40 ? "#e63946" : "#ff9f0a"
    }
    if (ss)   ss.textContent = score
    if (stag) {
      stag.textContent      = d.sentiment_label || "中性"
      stag.style.background = score > 60 ? "#e8faf0" : score < 40 ? "#fdecea" : "#fff3ee"
      stag.style.color      = score > 60 ? "#1a7f4b" : score < 40 ? "#c0392b" : "#b7770d"
    }

    const detail = document.getElementById("sentiment-detail")
    if (detail) {
      const themes = (d.key_themes   || []).map(t => `<span class="theme-tag">${t}</span>`).join("")
      const risks  = (d.risk_factors || []).map(r => `<span class="risk-tag">${r}</span>`).join("")
      detail.innerHTML = `<div class="sentiment-detail">${themes}${risks}</div>`
    }

    // ⚠️ 情绪接口不再覆盖新闻列表
    // 新闻由 loadNews() 独立管理

  } catch(e) {
    console.error("[sentiment] error:", e)
  }
}

// ── AI 选股 ───────────────────────────────────────────────────
async function aiSelect() {
  const query = document.getElementById("ai-query").value.trim()
  if (!query) return
  const btn    = document.querySelector("[onclick='aiSelect()']")
  const result = document.getElementById("ai-select-result")
  btn.disabled    = true
  btn.textContent = "分析中..."
  result.textContent = "AI 正在分析市场数据..."
  try {
    const res  = await fetch(API + "/api/ai/select", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ query, market: currentMarket })
    })
    const json = await res.json()
    result.textContent = json.result || "暂无结果"
  } catch(e) {
    result.textContent = `请求失败: ${e.message}`
  } finally {
    btn.disabled    = false
    btn.textContent = "AI 选股"
  }
}

// ── 个股诊断 ──────────────────────────────────────────────────
async function analyzeStock() {
  const code = document.getElementById("stock-input").value.trim()
  const name = document.getElementById("stock-name-input").value.trim() || code
  if (!code) return
  const btn    = document.querySelector("[onclick='analyzeStock()']")
  const result = document.getElementById("ai-analyze-result")
  btn.disabled    = true
  btn.textContent = "诊断中..."
  result.textContent = "AI 正在生成诊断报告..."
  try {
    const res  = await fetch(API + "/api/ai/analyze", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ stock_name: name, market: currentMarket, code })
    })
    const json = await res.json()
    result.textContent = json.result || "暂无结果"
  } catch(e) {
    result.textContent = `请求失败: ${e.message}`
  } finally {
    btn.disabled    = false
    btn.textContent = "AI 诊断"
  }
}

// ── 刷新按钮 ──────────────────────────────────────────────────
function refreshNews() {
  loadNews()
}

// ── 初始化 ────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("ai-query").addEventListener("keydown", e => {
    if (e.key === "Enter") aiSelect()
  })
  document.getElementById("stock-input").addEventListener("keydown", e => {
    if (e.key === "Enter") analyzeStock()
  })

  loadSectors()    // 热点板块
  loadNews()       // 新闻独立加载，不被情绪覆盖
  loadSentiment()  // 情绪分析单独跑
})