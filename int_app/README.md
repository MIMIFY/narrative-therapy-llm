# INT — Interactive Narrative Therapist / 叙事疗法 AI 咨询师

本地可运行实现，基于 EMNLP 2025 论文 **"Reframe Your Life Story"**。

A locally-runnable implementation accompanying the EMNLP 2025 paper **"Reframe Your Life Story"**.

---

## 项目简介 / Overview

INT 是一个基于叙事疗法的 AI 心理咨询助手。系统通过四个治疗阶段引导来访者重新审视并重构自身的生命故事，每个阶段配备了细粒度的反思层级，并结合检索增强生成（RAG）技术提供针对性的治疗性提问。

INT is an AI-assisted narrative therapy system. It guides users through four therapeutic stages to help them reframe and re-author their life narratives. Each stage uses fine-grained reflection levels and retrieval-augmented generation (RAG) to surface therapist-quality exemplar questions.

> **声明 / Disclaimer**: 本系统仅用于研究目的，不能替代专业心理咨询。  
> This system is for research purposes only and cannot replace professional mental health care.

---

## 系统架构 / Architecture

```
用户消息
  │
  ├─ [Stage Planner]      LLM 判断是否推进治疗阶段（4 个阶段）
  │
  ├─ [Reflection Planner] LLM 在当前阶段内选择反思层级（共 11 个）
  │
  ├─ [RAG Engine]         BGE-M3 向量化 + ChromaDB 检索匹配例句
  │     知识库：13 个 .md 文件，覆盖全部 4 阶段 × 11 层级
  │
  ├─ [Response Generator] LLM 生成最终治疗性回应（SSE 流式输出）
  │
  └─ [Goal Checker]       LLM 判断当前阶段目标是否达成
```

**四个治疗阶段 / Four Therapeutic Stages:**

| 阶段 | 英文名 | 反思层级 |
|------|--------|----------|
| 建立信任 | Trust Building | 探索问题事件、共情安慰来访 |
| 问题外化 | Problem Externalization | 隐喻命名问题、描绘问题影响、评估问题影响、论证评估 |
| 重述故事 | Re-authoring | 丰厚例外事件、认同蓝图、行动蓝图 |
| 重组关系 | Re-membering | 重要人物对来访者生活的贡献、来访者通过重要人物形成的身份认同、来访者对重要人物生活的贡献、来访者的这些贡献对重要人物身份认同的意义 |

---

## 快速开始 / Quick Start

### 前提条件 / Prerequisites

- Python 3.10+
- [OpenRouter](https://openrouter.ai) API key（支持 GPT-4o、Claude 3.5、Gemini 等模型）
- 约 600MB 磁盘空间（BGE-M3 嵌入模型）

### 五步启动 / Five Steps

**1. 克隆仓库 / Clone the repo**
```bash
git clone <repo-url>
cd <repo>/int_app
```

**2. 安装依赖 / Install dependencies**
```bash
pip install -r requirements.txt
```

**3. 配置环境变量 / Configure environment**
```bash
cp .env.example .env
# 用编辑器打开 .env，填入你的 OpenRouter API key
```

**4. 一键初始化 / One-command setup**
```bash
# 在 int_app/ 目录下运行
python setup.py
# 首次运行会下载 BGE-M3 模型（约 600MB），请耐心等待
```

**5. 启动服务 / Start the server**
```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

打开浏览器访问 / Open browser at: **http://localhost:8000**

---

## 目录结构 / Directory Structure

```
int_app/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 环境变量配置（pydantic-settings）
│   ├── database.py          # SQLite 异步会话持久化
│   ├── core/
│   │   ├── stages.py        # 阶段定义、反思层级、全部提示词模板
│   │   ├── llm_client.py    # OpenRouter 异步 LLM 客户端（支持流式）
│   │   ├── rag_engine.py    # LlamaIndex + ChromaDB + BGE-M3 RAG 引擎
│   │   └── int_engine.py    # 四步编排：阶段→反思→RAG→生成→目标检查
│   ├── routers/
│   │   ├── chat.py          # POST /api/chat（SSE 流式）
│   │   └── sessions.py      # GET /api/sessions、GET /api/export/{id}
│   └── knowledge/           # 13 个叙事疗法问题知识库（.md 格式）
├── frontend/
│   ├── index.html           # 单页聊天界面
│   ├── style.css            # 样式
│   └── app.js               # 前端逻辑（SSE 接收、会话管理、导出）
├── .env.example             # 环境变量模板
├── requirements.txt         # Python 依赖
├── setup.py                 # 一键初始化脚本
└── README.md
```

---

## API 接口 / API Reference

### `POST /api/chat`

发送用户消息，返回 Server-Sent Events 流式响应。

Send a user message; returns a Server-Sent Events stream.

**Request body:**
```json
{
  "session_id": "optional-existing-session-id",
  "message": "我最近压力很大...",
  "participant_id": "P001"
}
```

**SSE events:**
```
data: {"token": "我", "done": false}
data: {"token": "理解", "done": false}
...
data: {"done": true, "session_id": "uuid", "stage": "trust building", "reflection_level": "探索问题事件"}
```

### `GET /api/session/{session_id}`

获取完整会话记录，包含所有轮次数据。

Retrieve the full session record including all turns.

### `GET /api/sessions`

列出所有会话摘要。/ List all session summaries.

### `GET /api/export/{session_id}`

导出会话为 JSON 文件（IMA 格式兼容）。

Export a session as a JSON file (IMA-compatible format).

### `GET /health`

服务健康检查。/ Health check.

---

## 技术栈 / Tech Stack

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| LLM 接入 | OpenRouter (OpenAI-compatible API) |
| 嵌入模型 | BAAI/BGE-M3 (via sentence-transformers) |
| 向量数据库 | ChromaDB (本地持久化) |
| RAG 框架 | LlamaIndex |
| 会话存储 | SQLite (aiosqlite) |
| 前端 | 原生 HTML/CSS/JS，无依赖框架 |

---

## 引用 / Citation

如果你在研究中使用了本系统，请引用：

If you use this system in your research, please cite:

```bibtex
@inproceedings{int2025emnlp,
  title     = {Reframe Your Life Story: An Interactive Narrative Therapy System},
  booktitle = {Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing},
  year      = {2025},
  publisher = {Association for Computational Linguistics},
}
```

---

## 许可证 / License

详见根目录 LICENSE 文件。/ See LICENSE in the repository root.
