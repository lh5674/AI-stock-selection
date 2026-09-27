const API = ""
const WATCHLIST_KEY = "zhixuan-alpha-watchlist-v1"

const state = {
  market: "A股",
  aiConfigured: false,
  watchlist: loadSavedWatchlist(),
}

function byId(id) {
  return document.getElementById(id)
}

function loadSavedWatchlist() {
  const defaults = [
    { code: "600519", name: "贵州茅台", market: "A股" },
    { code: "NVDA", name: "NVIDIA", market: "美股" },
  ]
  try {
    const parsed = JSON.parse(localStorage.getItem(WATCHLIST_KEY))
    return Array.isArray(parsed) ? parsed.slice(0, 50) : defaults
  } catch {
    return defaults
  }
}

function saveWatchlist() {
  localStorage.setItem(WATCHLIST_KEY, JSON.stringify(state.watchlist))
  byId("watchlist-count").textContent = String(state.watchlist.length)
}

async function fetchJSON(path, options = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), options.timeout || 20000)
  try {
    const response = await fetch(API + path, { ...options, signal: controller.signal })
    let payload = {}
    try {
      payload = await response.json()
    } catch {
      // A non-JSON upstream error still gets a useful product message.
    }
    if (!response.ok) {
      throw new Error(payload.detail || `请求失败（${response.status}）`)
    }
    return payload
  } catch (error) {
    if (error.name === "AbortError") throw new Error("请求超时，请稍后重试")
    throw error
  } finally {
    clearTimeout(timeout)
  }
}

function formatNumber(value, digits = 2) {
  const number = Number(value)
  if (!Number.isFinite(number)) return "--"
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: digits }).format(number)
}

function formatPercent(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return "--"
  return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`
}

function showToast(message) {
  const toast = byId("toast")
  toast.textContent = message
  toast.hidden = false
  clearTimeout(showToast.timer)
  showToast.timer = setTimeout(() => { toast.hidden = true }, 3200)
}

function setLoading(container, message) {
  const wrapper = document.createElement("div")
  wrapper.className = "loading-state"
  const spinner = document.createElement("span")
  spinner.className = "spinner"
  wrapper.append(spinner, document.createTextNode(message))
  container.replaceChildren(wrapper)
}

function setMessage(container, message, isError = false) {
  const wrapper = document.createElement("div")
  wrapper.className = isError ? "error-box" : "empty-state"
  wrapper.textContent = message
  container.replaceChildren(wrapper)
}

function setAIResult(element, message, mode = "result") {
  element.hidden = false
  element.className = "ai-result"
  if (mode === "loading") element.classList.add("loading")
  if (mode === "error") element.classList.add("error-state")
  element.textContent = message
}

async function loadHealth() {
  const connection = byId("connection-status")
  try {
    const health = await fetchJSON("/api/health", { timeout: 6000 })
    state.aiConfigured = Boolean(health.ai_configured)
    connection.className = "connection-status online"
    connection.lastChild.textContent = "服务在线"
    byId("ai-status").textContent = state.aiConfigured ? "已就绪" : "待配置"
    byId("ai-status-copy").textContent = state.aiConfigured
      ? "AI 分析服务可用"
      : "设置新 API Key 后启用"
    byId("ai-model").textContent = state.aiConfigured ? "Qwen Plus · 在线" : "AI 功能已安全暂停"
    return health
  } catch {
    connection.className = "connection-status offline"
    connection.lastChild.textContent = "连接异常"
    byId("ai-status").textContent = "离线"
    byId("ai-status-copy").textContent = "请检查后端服务"
    return null
  }
}

function switchMarket(market) {
  state.market = market
  document.querySelectorAll(".market-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.market === market)
  })
  byId("market-panel-title").textContent = market === "A股" ? "A 股市场热度" : "美股活跃标的"
  byId("sector-detail").hidden = true
  loadMarket()
}

async function loadMarket() {
  const grid = byId("sector-grid")
  setLoading(grid, "正在读取市场行情")
  try {
    const endpoint = state.market === "A股" ? "/api/sectors/a" : "/api/movers/us"
    const payload = await fetchJSON(endpoint, { timeout: 30000 })
    const data = payload.data || []
    if (!data.length) return setMessage(grid, "当前暂无市场数据")

    const fragment = document.createDocumentFragment()
    data.forEach((item) => {
      const name = item["板块名称"] || item.name || item.symbol || "未知"
      const price = item["最新价"] ?? item.price
      const change = Number(item["涨跌幅"] ?? item.change_pct ?? 0)
      const button = document.createElement("button")
      button.type = "button"
      button.className = "sector-item"
      const nameNode = document.createElement("span")
      nameNode.className = "sector-name"
      nameNode.textContent = name
      const priceNode = document.createElement("strong")
      priceNode.className = "sector-price"
      priceNode.textContent = state.market === "美股"
        ? `$${formatNumber(price)}`
        : formatNumber(price)
      const changeNode = document.createElement("span")
      changeNode.className = `sector-change ${change >= 0 ? "up" : "down"}`
      changeNode.textContent = formatPercent(change)
      button.append(nameNode, priceNode, changeNode)
      button.addEventListener("click", () => {
        byId("ai-query").value = `帮我分析${name}方向中基本面稳健、趋势较强的机会`
        if (state.market === "A股" && item.kind === "industry") loadSectorDetails(name)
        else if (state.market === "A股" && item.symbol) selectStock(item.symbol, name, "A股")
        else byId("ai-screener").scrollIntoView({ behavior: "smooth", block: "center" })
      })
      fragment.append(button)
    })
    grid.replaceChildren(fragment)
  } catch (error) {
    setMessage(grid, error.message, true)
  }
}

async function loadSectorDetails(name) {
  const detail = byId("sector-detail")
  const list = byId("constituent-list")
  detail.hidden = false
  byId("sector-detail-title").textContent = name
  setLoading(list, "正在读取成分股")
  try {
    const payload = await fetchJSON(`/api/sectors/a/${encodeURIComponent(name)}`, { timeout: 30000 })
    const data = payload.data || []
    if (!data.length) return setMessage(list, "暂无成分股数据")
    const fragment = document.createDocumentFragment()
    data.slice(0, 12).forEach((item) => {
      const row = document.createElement("button")
      row.type = "button"
      row.className = "constituent"
      const stockName = document.createElement("strong")
      stockName.textContent = item.name
      const code = document.createElement("small")
      code.textContent = item.code
      const change = document.createElement("span")
      change.className = Number(item.change_pct) >= 0 ? "up" : "down"
      change.textContent = formatPercent(item.change_pct)
      row.append(stockName, code, change)
      row.addEventListener("click", () => selectStock(item.code, item.name, "A股"))
      fragment.append(row)
    })
    list.replaceChildren(fragment)
  } catch (error) {
    setMessage(list, error.message, true)
  }
}

function selectStock(code, name, market) {
  switchMarket(market)
  byId("stock-input").value = code
  byId("stock-name-input").value = name || ""
  byId("stock-lab").scrollIntoView({ behavior: "smooth", block: "center" })
}

async function loadNews() {
  const list = byId("news-list")
  setLoading(list, "正在聚合市场快讯")
  try {
    const payload = await fetchJSON(`/api/news?limit=12&t=${Date.now()}`, { timeout: 30000 })
    const news = payload.data || []
    if (!news.length) return setMessage(list, "当前暂无快讯")
    const fragment = document.createDocumentFragment()
    news.forEach((item) => {
      const article = document.createElement("article")
      article.className = "news-item"
      const source = document.createElement("span")
      source.className = "news-source"
      source.textContent = item.source || "快讯"
      const content = document.createElement("div")
      content.className = "news-content"
      const link = document.createElement("a")
      link.textContent = item.title || "未命名快讯"
      link.target = "_blank"
      link.rel = "noopener noreferrer"
      try {
        const url = new URL(item.url, window.location.origin)
        link.href = ["http:", "https:"].includes(url.protocol) ? url.href : "#"
      } catch {
        link.href = "#"
      }
      const time = document.createElement("time")
      time.className = "news-time"
      time.textContent = item.time || "刚刚"
      content.append(link, time)
      article.append(source, content)
      fragment.append(article)
    })
    list.replaceChildren(fragment)
  } catch (error) {
    setMessage(list, error.message, true)
  }
}

async function loadSentiment() {
  if (!state.aiConfigured) {
    updateSentiment({ sentiment_score: 50, sentiment_label: "待配置", summary: "配置新的 AI 服务密钥后生成市场情绪。" })
    return
  }
  try {
    const payload = await fetchJSON("/api/ai/sentiment", { timeout: 45000 })
    updateSentiment(payload.data || {})
  } catch (error) {
    updateSentiment({ sentiment_score: 50, sentiment_label: "暂不可用", summary: error.message })
  }
}

function updateSentiment(data) {
  const rawScore = Number(data.sentiment_score)
  const score = Number.isFinite(rawScore) ? Math.max(0, Math.min(100, rawScore)) : 50
  byId("s-score").textContent = String(Math.round(score))
  byId("s-tag").textContent = data.sentiment_label || "中性"
  byId("sentiment-summary").textContent = data.summary || "等待更多市场信号"
  const fill = byId("s-fill")
  fill.style.width = `${score}%`
  fill.style.background = score > 60 ? "var(--positive)" : score < 40 ? "var(--negative)" : "var(--warning)"
}

async function runAISelection() {
  const query = byId("ai-query").value.trim()
  if (query.length < 2) return showToast("请先描述你的选股要求")
  const button = byId("ai-select-button")
  const result = byId("ai-select-result")
  button.disabled = true
  setAIResult(result, "AI 正在结合市场热度整理研究方向…", "loading")
  try {
    const payload = await fetchJSON("/api/ai/select", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, market: state.market }),
      timeout: 60000,
    })
    setAIResult(result, payload.result || "暂未生成结果")
  } catch (error) {
    setAIResult(result, error.message, "error")
  } finally {
    button.disabled = false
  }
}

async function analyzeStock(event) {
  event.preventDefault()
  const code = byId("stock-input").value.trim().toUpperCase()
  const name = byId("stock-name-input").value.trim() || code
  if (!code) return
  const button = byId("analyze-button")
  const result = byId("ai-analyze-result")
  button.disabled = true
  setAIResult(result, "正在读取价格走势并生成研究摘要…", "loading")
  try {
    const detail = await loadStockPreview(code)
    addToWatchlist(code, name, state.market, false)
    const payload = await fetchJSON("/api/ai/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stock_name: name, market: state.market, code }),
      timeout: 60000,
    })
    setAIResult(result, payload.result || "暂未生成结果")
    if (!detail.history?.length) showToast("已生成 AI 报告，但价格数据不完整")
  } catch (error) {
    setAIResult(result, error.message, "error")
  } finally {
    button.disabled = false
  }
}

async function getStockDetail(code, market) {
  const endpoint = market === "A股"
    ? `/api/stock/a/${encodeURIComponent(code)}`
    : `/api/stock/us/${encodeURIComponent(code)}`
  const payload = await fetchJSON(endpoint, { timeout: 30000 })
  return payload.data || {}
}

async function loadStockPreview(code) {
  const detail = await getStockDetail(code, state.market)
  const history = detail.history || []
  if (!history.length) throw new Error("未找到该股票的近期行情")
  const latest = Number(history.at(-1).close)
  const previous = Number(history.at(-2)?.close ?? latest)
  const change = previous ? ((latest - previous) / previous) * 100 : 0
  byId("stock-preview").hidden = false
  byId("preview-symbol").textContent = code
  byId("preview-price").textContent = `${state.market === "美股" ? "$" : "¥"}${formatNumber(latest)}`
  const changeNode = byId("preview-change")
  changeNode.textContent = formatPercent(change)
  changeNode.className = change >= 0 ? "up" : "down"
  drawChart(history)
  return detail
}

function drawChart(history) {
  const svg = byId("stock-chart")
  svg.replaceChildren()
  const values = history.map((item) => Number(item.close)).filter(Number.isFinite)
  if (values.length < 2) return
  const width = 640
  const height = 160
  const pad = 8
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1
  const points = values.map((value, index) => {
    const x = pad + (index / (values.length - 1)) * (width - pad * 2)
    const y = pad + ((max - value) / range) * (height - pad * 2)
    return [x, y]
  })
  const ns = "http://www.w3.org/2000/svg"
  const defs = document.createElementNS(ns, "defs")
  const gradient = document.createElementNS(ns, "linearGradient")
  gradient.id = "chart-gradient"
  gradient.setAttribute("x1", "0")
  gradient.setAttribute("y1", "0")
  gradient.setAttribute("x2", "0")
  gradient.setAttribute("y2", "1")
  const stopA = document.createElementNS(ns, "stop")
  stopA.setAttribute("offset", "0%")
  stopA.setAttribute("stop-color", "#5b5cf0")
  stopA.setAttribute("stop-opacity", ".22")
  const stopB = document.createElementNS(ns, "stop")
  stopB.setAttribute("offset", "100%")
  stopB.setAttribute("stop-color", "#5b5cf0")
  stopB.setAttribute("stop-opacity", "0")
  gradient.append(stopA, stopB)
  defs.append(gradient)
  svg.append(defs)
  ;[40, 80, 120].forEach((y) => {
    const line = document.createElementNS(ns, "line")
    line.setAttribute("x1", "0")
    line.setAttribute("x2", String(width))
    line.setAttribute("y1", String(y))
    line.setAttribute("y2", String(y))
    line.setAttribute("class", "chart-grid")
    svg.append(line)
  })
  const pathData = points.map(([x, y], index) => `${index ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ")
  const area = document.createElementNS(ns, "path")
  area.setAttribute("d", `${pathData} L${points.at(-1)[0]},${height} L${points[0][0]},${height} Z`)
  area.setAttribute("class", "chart-area")
  const line = document.createElementNS(ns, "path")
  line.setAttribute("d", pathData)
  line.setAttribute("class", "chart-line")
  svg.append(area, line)
}

function addToWatchlist(code, name, market, notify = true) {
  const normalized = code.trim().toUpperCase()
  if (!normalized) return
  if (state.watchlist.some((item) => item.code === normalized && item.market === market)) {
    if (notify) showToast("该股票已在自选列表中")
    return
  }
  state.watchlist.unshift({ code: normalized, name: name || normalized, market })
  state.watchlist = state.watchlist.slice(0, 50)
  saveWatchlist()
  renderWatchlist()
  if (notify) showToast("已加入自选列表")
}

async function renderWatchlist() {
  const container = byId("watchlist-items")
  byId("watchlist-count").textContent = String(state.watchlist.length)
  if (!state.watchlist.length) return setMessage(container, "还没有自选股票，先添加一个吧")
  setLoading(container, "正在更新自选行情")
  const results = await Promise.all(state.watchlist.map(async (item) => {
    try {
      const detail = await getStockDetail(item.code, item.market)
      const history = detail.history || []
      const latest = Number(history.at(-1)?.close)
      const previous = Number(history.at(-2)?.close ?? latest)
      const change = previous ? ((latest - previous) / previous) * 100 : 0
      return { ...item, latest, change }
    } catch {
      return { ...item, latest: null, change: null }
    }
  }))
  const fragment = document.createDocumentFragment()
  results.forEach((item) => {
    const row = document.createElement("div")
    row.className = "watch-item"
    const symbol = document.createElement("button")
    symbol.type = "button"
    symbol.className = "watch-symbol"
    const symbolStrong = document.createElement("strong")
    symbolStrong.textContent = item.name
    const symbolSmall = document.createElement("small")
    symbolSmall.textContent = `${item.code} · ${item.market}`
    symbol.append(symbolStrong, symbolSmall)
    symbol.addEventListener("click", () => selectStock(item.code, item.name, item.market))
    const price = document.createElement("div")
    price.className = "watch-price"
    const priceStrong = document.createElement("strong")
    priceStrong.textContent = item.latest == null ? "--" : `${item.market === "美股" ? "$" : "¥"}${formatNumber(item.latest)}`
    const priceSmall = document.createElement("small")
    priceSmall.textContent = item.change == null ? "暂不可用" : formatPercent(item.change)
    if (item.change != null) priceSmall.className = item.change >= 0 ? "up" : "down"
    price.append(priceStrong, priceSmall)
    const remove = document.createElement("button")
    remove.type = "button"
    remove.className = "remove-watch"
    remove.textContent = "×"
    remove.setAttribute("aria-label", `移除 ${item.name}`)
    remove.addEventListener("click", () => {
      state.watchlist = state.watchlist.filter((saved) => !(saved.code === item.code && saved.market === item.market))
      saveWatchlist()
      renderWatchlist()
    })
    row.append(symbol, price, remove)
    fragment.append(row)
  })
  container.replaceChildren(fragment)
}

function openPricing() {
  const dialog = byId("pricing-dialog")
  if (typeof dialog.showModal === "function") dialog.showModal()
}

function setupNavigation() {
  const sidebar = byId("sidebar")
  const backdrop = byId("mobile-backdrop")
  const closeMobile = () => {
    sidebar.classList.remove("open")
    backdrop.hidden = true
  }
  byId("mobile-menu").addEventListener("click", () => {
    sidebar.classList.add("open")
    backdrop.hidden = false
  })
  backdrop.addEventListener("click", closeMobile)
  document.querySelectorAll(".nav-item").forEach((link) => link.addEventListener("click", closeMobile))
}

function setupEvents() {
  document.querySelectorAll(".market-button").forEach((button) => {
    button.addEventListener("click", () => switchMarket(button.dataset.market))
  })
  byId("refresh-market").addEventListener("click", loadMarket)
  byId("close-sector-detail").addEventListener("click", () => { byId("sector-detail").hidden = true })
  byId("refresh-news").addEventListener("click", loadNews)
  byId("ai-select-button").addEventListener("click", runAISelection)
  byId("stock-form").addEventListener("submit", analyzeStock)
  byId("ai-query").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) runAISelection()
  })
  document.querySelectorAll("#prompt-suggestions button").forEach((button) => {
    button.addEventListener("click", () => {
      byId("ai-query").value = button.textContent
      byId("ai-query").focus()
    })
  })
  byId("add-watchlist").addEventListener("click", () => {
    byId("stock-lab").scrollIntoView({ behavior: "smooth", block: "center" })
    byId("stock-input").focus()
    showToast("输入股票代码并生成诊断，即可加入自选")
  })
  const search = byId("global-search")
  search.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return
    const code = search.value.trim().toUpperCase()
    if (!code) return
    selectStock(code, "", /^\d{6}$/.test(code) ? "A股" : "美股")
  })
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
      event.preventDefault()
      search.focus()
    }
  })
  ;[byId("view-plans"), byId("top-upgrade")].forEach((button) => button.addEventListener("click", openPricing))
  document.querySelectorAll(".plan-interest").forEach((button) => {
    button.addEventListener("click", () => showToast(`${button.dataset.plan}已登记意向；商业发布前将接入正式开通流程。`))
  })
}

function setDateGreeting() {
  const now = new Date()
  const hour = now.getHours()
  document.querySelector(".page-heading h1").textContent = `${hour < 12 ? "早上" : hour < 18 ? "下午" : "晚上"}好，今天关注什么？`
  byId("market-date").textContent = new Intl.DateTimeFormat("zh-CN", {
    year: "numeric", month: "long", day: "numeric", weekday: "long",
  }).format(now)
}

document.addEventListener("DOMContentLoaded", async () => {
  setupNavigation()
  setupEvents()
  setDateGreeting()
  saveWatchlist()
  const health = await loadHealth()
  await Promise.allSettled([loadMarket(), loadNews(), renderWatchlist()])
  if (health) loadSentiment()
})
