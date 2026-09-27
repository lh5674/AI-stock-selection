# 智选 Alpha

面向个人投资者的双市场 AI 投研工作台。项目聚合 A 股行业与个股行情、美股行情、中文财经快讯，并通过阿里云百炼生成自然语言选股和个股研究摘要。

> 本产品提供的内容仅用于信息和研究，不构成任何投资建议。

## 产品能力

- A 股热门行业、行业成分股和个股近期行情
- 美股活跃标的和近期行情
- AI 自然语言选股、个股诊断和市场情绪分析
- 浏览器本地自选列表
- 响应式 SaaS 工作台、方案展示和可靠的加载/错误状态
- FastAPI 健康检查、输入校验、安全响应头和上游错误隔离

## 本地启动

需要 Python 3.11 或更新版本。

```powershell
cd aianalyze\backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，填入一个**新创建**的百炼密钥：

```dotenv
DASHSCOPE_API_KEY=your-new-key
DASHSCOPE_MODEL=qwen-plus
```

启动服务：

```powershell
.\.venv\Scripts\python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

打开 <http://127.0.0.1:8000>，API 文档位于 <http://127.0.0.1:8000/docs>。

## 验证

```powershell
cd aianalyze\backend
.\.venv\Scripts\python -m unittest discover -s tests -v
```

不配置 AI 密钥也可以使用行情、快讯和自选功能；AI 接口会返回明确的 `503` 配置状态。

## 商业发布前清单

当前界面已具备 SaaS 产品展示和使用体验，但正式收费发布仍需接入：

- 用户注册、登录、会话和密码找回
- 服务端自选同步、账户隔离和数据备份
- 支付、订阅、发票、试用期和额度控制
- 持久化缓存、任务队列、限流和可观测性
- 正式域名、HTTPS、隐私政策、用户协议和金融免责声明审查
- 经授权且符合商业使用条款的市场数据源

## 安全

密钥只允许保存在 `aianalyze/backend/.env` 或部署平台的密钥管理服务中。仓库曾包含一个明文密钥文件；该密钥必须在阿里云控制台撤销并重新创建。仅从当前分支删除文件不能撤销已经暴露的凭据。
