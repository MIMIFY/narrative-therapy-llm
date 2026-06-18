# Reframe Your Life Story：交互式叙事疗法系统与创新时刻评估

[English](README.md) | [中文](README_zh.md)

这是 EMNLP 2025 论文的官方代码与数据。

论文链接：https://aclanthology.org/2025.emnlp-main.1245/

> 本仓库仅用于研究，不能替代专业心理健康服务。

## 项目概览

本仓库包含三个公开部分：

- `int/`：可本地运行的 Interactive Narrative Therapist (INT)，包括 FastAPI 后端、网页界面、RAG、会话记忆、个人故事卡和研究者后台。
- `evaluation/`：Innovative Moment Assessment (IMA/IMCS) 标注和治疗维度评分脚本。
- `data/`：公开的 NTConv 数据和从 ESConv 提取的来访者画像。

## 演示视频

https://github.com/user-attachments/assets/3240ae8f-9e38-4ff1-8300-7c6ddd63f5c6

## 论文简介

本文研究如何用大语言模型支持叙事疗法。叙事疗法关注人如何讲述自己的生命故事，并帮助来访者从被问题主导的叙事中，逐步发展出更有力量的替代性叙事。论文提出两个相互关联的部分：INT 是一个基于规划的交互式叙事治疗师，会追踪治疗阶段和反思层级，检索专家叙事疗法示例，并生成贴合上下文的回应；IMA 是 Innovative Moment Assessment 评估框架，用于识别来访者话语中的叙事转变，并沿着完整对话过程衡量治疗进展。模拟来访者和真人参与者实验表明，相比标准 LLM 角色扮演基线，INT 在治疗质量和对话深度上表现更好，而 IMA 提供了一种面向过程的叙事变化评估方式。

## 仓库结构

```text
.
├── int/
│   ├── backend/                  # INT 编排、RAG、memory、API routes
│   ├── backend/knowledge/        # 13 个 Markdown RAG 知识文件
│   ├── frontend/                 # 用户端和研究者后台
│   ├── simulate_client.py        # 自动来访者模拟
│   ├── README.md                 # 英文版
│   └── README_zh.md              # 中文版
├── evaluation/
│   ├── ima/                      # IMA / IMCS 标注
│   ├── dimension_metrics/        # 治疗维度评分
│   ├── README.md                 # 英文版
│   └── README_zh.md              # 中文版
├── data/
│   ├── esconv_profiles/
│   ├── ntconv/
│   ├── README.md                 # 英文版
│   └── README_zh.md              # 中文版
└── README.md
```

## 快速开始：运行 INT

前提条件：

- Python 3.10+
- OpenRouter API key，或在 `.env` 中配置其他 OpenAI-compatible 服务
- 首次构建 RAG 时需要网络，因为系统会从 HuggingFace 下载 BGE-M3 嵌入模型
- 约 600 MB 磁盘空间用于嵌入模型，另外还会生成本地 Chroma 索引文件

### 1. 安装依赖

```bash
cd int
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. 配置模型

```bash
cp .env.example .env
```

编辑 `int/.env`，填入 OpenRouter API key：

```text
OPENROUTER_API_KEY=your-key
```

也可以修改 `STAGE_PLANNER_MODEL`、`REFLECTION_PLANNER_MODEL`、`RESPONSE_MODEL` 和 `GOAL_CHECKER_MODEL`。

### 3. 构建 RAG 索引

INT 使用 `int/backend/knowledge/` 下的 13 个 Markdown 问题库文件。
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

如果只是做后端 smoke test，不想下载 embedding 或启用 RAG，可以在 `int/.env` 中设置 `DISABLE_RAG=1`。
此时治疗性回复仍会运行，但不会进行 RAG 示例问题检索。

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

请在 `.env` 中设置 `ADMIN_KEY`。示例/默认本地管理员 key 是 `change-me-before-running-admin`；它只适合本地测试，分享或部署前必须修改。

## INT 流程

```text
用户输入
  -> Stage Planner
  -> Reflection Planner
  -> 在 13 个知识文件上进行 RAG 检索
  -> 检索用户记忆上下文
  -> 流式生成回复
  -> 异步目标检查
  -> 每 N 轮更新长期记忆
```

| 阶段 | 反思水平 |
| --- | --- |
| Trust Building | Exploring the Problem Event; Empathic Comforting |
| Problem Externalization | Negotiation of the Dominant Problem; Mapping Problem Effects; Evaluating Problem Effects; Justification of Evaluation |
| Re-authoring | Elaboration of Unique Outcomes; Exploration of Identity Landscape; Exploration of Action Landscape |
| Re-membering | Significant Others' Contributions; Self through Others; One's Contributions; Implications for Identity |

## RAG 知识更新

RAG 源文件：

```text
int/backend/knowledge/
```

索引器只会读取以下映射中注册的文件：

```text
int/backend/core/stages.py
KNOWLEDGE_FILE_MAP
```

更新 RAG：

1. 编辑已有 `.md` 文件，或在 `int/backend/knowledge/` 下新增文件。
2. 如果新增文件，需要在 `KNOWLEDGE_FILE_MAP` 中登记正确的 `stage` 和 `level`。
3. 重建索引。

```bash
cd int
venv/bin/python backend/scripts/reindex_rag.py --force
```

`int/chroma_db/` 是本地生成的向量索引。

新增或修改知识文件后，需要重新运行 `venv/bin/python backend/scripts/reindex_rag.py --force`，再启动服务。

## 记忆与个人故事卡

运行状态存储在本地 SQLite：

```text
int/sessions.db
```

记忆逻辑：

- 每个 session 保存完整对话历史。
- 研究者后台 trace 包含阶段、反思水平、RAG 命中、模型名、目标检查结果和记忆更新状态。
- 长期用户记忆每 `MEMORY_UPDATE_INTERVAL` 轮更新一次，默认值为 `5`。
- 个人故事卡在 `STORY_MIN_TURNS` 轮后可用，默认值为 `20`。
- 点击“我的故事”会优先查看历史；生成新故事需要单独点击生成按钮。

`int/sessions.db` 和 `int/memory_chroma_db/` 是本地运行文件，可能包含参与者数据。

## 模拟对话

使用 `simulate_client.py` 和 `data/esconv_profiles/ESConv.json` 生成模拟对话。

单个画像：

```bash
cd int
venv/bin/python simulate_client.py \
  --esconv ../data/esconv_profiles/ESConv.json \
  --profile-index 42 \
  --turns 35 \
  --language en \
  --output-dir ./simulation_output
```

批量模式：

```bash
venv/bin/python simulate_client.py \
  --esconv ../data/esconv_profiles/ESConv.json \
  --max-profiles 10 \
  --turns 35 \
  --language en \
  --output-dir ./simulation_output
```

模拟输出可直接用于 evaluation 脚本。

## 运行评估

安装评估依赖：

```bash
cd evaluation
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

设置 OpenAI-compatible API key：

```bash
export OPENAI_API_KEY=your-key
export OPENAI_BASE_URL=https://api.openai.com/v1
```

如使用 OpenRouter，可设置 `OPENROUTER_API_KEY` 和 `OPENROUTER_BASE_URL`。

### IMA / IMCS 标注

```bash
cd ima
../venv/bin/python IMCS_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/imcs \
  --number INT-full \
  --language en
```

中文对话使用 `--language zh`。

### 治疗维度评分

```bash
cd ../dimension_metrics
../venv/bin/python dimention_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/dimensions \
  --number INT-full \
  --key_client client \
  --key_therapist therapist
```

封装脚本：

```bash
OPENAI_API_KEY=your-key ./run_evaluation.sh
```

更多细节见 `evaluation/README_zh.md`。

## 数据

`data/ntconv/` 包含 1300 个英文叙事疗法对话，已划分为训练集和测试集。

`data/esconv_profiles/ESConv.json` 包含 1300 条从 ESConv 提取的模拟来访者画像。

## 引用

论文链接：https://aclanthology.org/2025.emnlp-main.1245/

```bibtex
@inproceedings{feng2025reframe,
  title={Reframe Your Life Story: Interactive Narrative Therapist and Innovative Moment Assessment with Large Language Models},
  author={Feng, Yi and Wang, Jiaqi and Zhang, Wenxuan and Chen, Zhuang and Yutong, Shen and Xiao, Xiyao and Huang, Minlie and Jing, Liping and Yu, Jian},
  booktitle={Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing},
  pages={24495--24520},
  year={2025}
}
```

## 联系

Yi Feng: yifeng@bjtu.edu.cn
