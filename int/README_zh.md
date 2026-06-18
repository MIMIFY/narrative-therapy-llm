# INT：交互式叙事疗法系统

[English](README.md) | [中文](README_zh.md)

本地可运行实现，基于 EMNLP 2025 论文 **"Reframe Your Life Story"**。

论文链接：https://aclanthology.org/2025.emnlp-main.1245/

> 本系统仅用于研究目的，不能替代专业心理咨询或专业心理健康服务。

## 项目简介

INT 是一个基于叙事疗法的 AI 心理咨询助手。系统通过四个治疗阶段引导来访者重新审视并重构自身的生命故事，每个阶段配备细粒度反思层级，并结合检索增强生成（RAG）提供针对性的治疗性提问示例。

## 系统架构

```text
用户消息
  │
  ├─ [Stage Planner]      LLM 判断是否推进治疗阶段
  ├─ [Reflection Planner] LLM 在当前阶段内选择反思水平
  ├─ [RAG Engine]         BGE-M3 向量化 + ChromaDB 检索示例问题
  ├─ [Response Generator] LLM 生成最终治疗性回应
  └─ [Goal Checker]       LLM 判断当前阶段目标是否达成
```

## 治疗阶段

| 阶段 | 反思水平 |
| --- | --- |
| Trust Building | Exploring the Problem Event; Empathic Comforting |
| Problem Externalization | Negotiation of the Dominant Problem; Mapping Problem Effects; Evaluating Problem Effects; Justification of Evaluation |
| Re-authoring | Elaboration of Unique Outcomes; Exploration of Identity Landscape; Exploration of Action Landscape |
| Re-membering | Significant Others' Contributions; Self through Others; One's Contributions; Implications for Identity |

## 快速开始

### 前提条件

- Python 3.10+
- OpenRouter API key 或其他 OpenAI-compatible 服务
- 首次构建 RAG 时需要网络，因为系统会从 HuggingFace 下载 BGE-M3 嵌入模型
- 约 600 MB 磁盘空间用于 BGE-M3 嵌入模型，另外还会生成本地 Chroma 索引文件

### 1. 安装依赖

```bash
cd int
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入 API key：

```text
OPENROUTER_API_KEY=your-openrouter-api-key
```

如果只是临时 smoke test、暂时不下载 BGE-M3，可以设置 `DISABLE_RAG=1`。
此时治疗性回复仍会运行，但不会进行 RAG 示例问题检索。

### 3. 构建 RAG 索引

INT 使用 `backend/knowledge/` 下的 13 个 Markdown 问题库文件。
首次运行会下载 BGE-M3 嵌入模型，并构建本地 Chroma 索引。
根据网络和机器性能不同，这一步可能需要几分钟。

```bash
venv/bin/python backend/scripts/reindex_rag.py --force
```

知识文件加载后的 dry-run 预期数量：

```text
Knowledge files loaded: 13
Question documents parsed: 366
Collection: therapy_questions
```

只检查、不重建：

```bash
venv/bin/python backend/scripts/reindex_rag.py
```

### 4. 启动服务

```bash
venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

打开用户端：

```text
http://127.0.0.1:8000
```

打开研究者后台：

```text
http://127.0.0.1:8000/admin.html
```

`.env.example` 中的示例/默认本地管理员 key 是 `change-me-before-running-admin`。它只适合本地测试，分享或部署前请在 `.env` 中替换。

## 目录结构

```text
int/
├── backend/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 环境变量配置
│   ├── database.py          # SQLite 异步持久化
│   ├── core/
│   │   ├── stages.py        # 阶段、反思水平、prompt
│   │   ├── utils.py         # YAML 解析与工具函数
│   │   ├── llm_client.py    # OpenRouter 异步 LLM 客户端
│   │   ├── rag_engine.py    # LlamaIndex + ChromaDB + BGE-M3 RAG
│   │   ├── narrative_memory.py
│   │   └── int_engine.py    # 阶段 -> 反思 -> RAG -> 回复 -> 目标检查
│   ├── routers/
│   │   ├── chat.py
│   │   └── sessions.py
│   └── knowledge/           # 13 个叙事疗法问题库文件
├── frontend/
│   ├── index.html
│   ├── admin.html
│   ├── style.css
│   └── app.js
├── tests/
├── .env.example
├── requirements.txt
├── setup.py
└── simulate_client.py
```

## RAG 知识库重建

RAG 知识库以 Markdown 文件存储在：

```text
backend/knowledge/
```

当前实现只会索引以下映射中注册的文件：

```text
backend/core/stages.py
KNOWLEDGE_FILE_MAP
```

补充 RAG：

1. 编辑已有 stage/reflection `.md` 文件，或新增 `.md` 文件。
2. 如果新增文件，需要在 `KNOWLEDGE_FILE_MAP` 中登记正确的内部 `stage` 和 `level`。
3. 停止正在运行的服务。
4. 重建 Chroma 索引。

```bash
venv/bin/python backend/scripts/reindex_rag.py --force
```

5. 重启服务。

```bash
venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

注意：

- `chroma_db/` 存储本地 RAG 向量索引。
- `sessions.db` 和 `memory_chroma_db/` 存储用户/session 数据。
- 删除或重建 `chroma_db/` 不会删除 `sessions.db` 中的对话和记忆。
- 新增或修改知识文件后，需要重新运行 `venv/bin/python backend/scripts/reindex_rag.py --force`，再启动服务。

## 长期记忆与个人故事卡

INT 将本地运行状态存储在 SQLite：

```text
sessions.db
```

记忆子系统实现在：

```text
backend/core/narrative_memory.py
```

运行逻辑：

- 每个 session 保存完整轮次、stage/reflection 决策、RAG 命中和 trace 日志。
- 参与者长期记忆每 `MEMORY_UPDATE_INTERVAL` 轮更新一次，默认值为 `5`。
- 记忆抽取会追踪问题叙事、例外事件、偏好身份、session 摘要和叙事轨迹。
- 回复生成时会检索压缩后的记忆上下文，而不是每轮粘贴全部历史。
- “我的故事”卡片在 `STORY_MIN_TURNS` 轮后可用，默认值为 `20`。
- 打开“我的故事”只查看历史版本；生成或更新故事需要单独点击生成按钮。

重要本地文件：

```text
sessions.db          # sessions、traces、memories、story cards
memory_chroma_db/    # 可选本地向量记忆库
chroma_db/           # RAG 索引
```

这些文件是应用运行时创建的本地文件。

## 模拟与评估

生成模拟 INT 对话：

```bash
venv/bin/python simulate_client.py \
  --esconv ../data/esconv_profiles/ESConv.json \
  --max-profiles 10 \
  --turns 35 \
  --language en \
  --output-dir ./simulation_output
```

然后从仓库根目录运行评估：

```bash
cd evaluation
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

IMA / IMCS：

```bash
cd ima
../venv/bin/python IMCS_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/imcs \
  --number INT-full \
  --language en
```

治疗维度评分：

```bash
cd ../dimension_metrics
../venv/bin/python dimention_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/dimensions \
  --number INT-full
```

## API 接口

### `POST /api/chat`

发送用户消息，返回 Server-Sent Events 流式响应。

请求体：

```json
{
  "session_id": "optional-existing-session-id",
  "message": "我最近压力很大。",
  "participant_id": "P001"
}
```

### `GET /api/session/{session_id}`

获取完整会话记录，包含所有轮次数据。

### `GET /api/sessions`

研究者接口，列出所有会话摘要。需要通过 query 或 header 提供 admin key。

```bash
curl "http://127.0.0.1:8000/api/sessions?admin_key=$ADMIN_KEY"
curl -H "X-Admin-Key: $ADMIN_KEY" "http://127.0.0.1:8000/api/sessions"
```

### `GET /api/participant/{participant_id}/sessions`

获取某个参与者的会话摘要，用于用户端跨 session 历史。

### `GET /api/participant/{participant_id}/stories`

只读取个人故事历史版本，不触发模型生成。

### `POST /api/participant/{participant_id}/story`

生成或更新个人故事卡。达到 `STORY_MIN_TURNS` 后可用；如果当前轮次数与最新故事一致，会返回缓存。

### `GET /api/export/{session_id}`

导出会话为 IMA 兼容的 JSON 文件。

### `GET /health`

服务健康检查。

## 技术栈

| 组件 | 技术 |
| --- | --- |
| Web 框架 | FastAPI + Uvicorn |
| LLM 接入 | OpenRouter / OpenAI-compatible API |
| 嵌入模型 | BAAI/BGE-M3 via sentence-transformers |
| 向量数据库 | ChromaDB |
| RAG 框架 | LlamaIndex |
| 会话存储 | SQLite with aiosqlite |
| 前端 | 原生 HTML/CSS/JS |

## 引用

```bibtex
@inproceedings{feng2025reframe,
  title={Reframe Your Life Story: Interactive Narrative Therapist and Innovative Moment Assessment with Large Language Models},
  author={Feng, Yi and Wang, Jiaqi and Zhang, Wenxuan and Chen, Zhuang and Yutong, Shen and Xiao, Xiyao and Huang, Minlie and Jing, Liping and Yu, Jian},
  booktitle={Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing},
  pages={24495--24520},
  year={2025}
}
```
