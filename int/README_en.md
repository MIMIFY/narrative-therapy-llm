# INT: Interactive Narrative Therapist

[English](README.md) | [Chinese](README_zh.md)

A locally runnable implementation accompanying the EMNLP 2025 paper **"Reframe Your Life Story"**.

Paper: https://aclanthology.org/2025.emnlp-main.1245/

> This system is for research purposes only and cannot replace professional mental health care.

## Overview

INT is an AI-assisted narrative therapy system. It guides users through four therapeutic stages to help them reframe and re-author their life narratives. Each stage uses fine-grained reflection levels and retrieval-augmented generation (RAG) to surface therapist-quality exemplar questions.

## Architecture

```text
User message
  │
  ├─ [Stage Planner]      LLM decides whether to advance the therapeutic stage
  ├─ [Reflection Planner] LLM selects a reflection level within the current stage
  ├─ [RAG Engine]         BGE-M3 embeddings + ChromaDB retrieve exemplar questions
  ├─ [Response Generator] LLM generates the final therapeutic response
  └─ [Goal Checker]       LLM checks whether the current stage goal is satisfied
```

## Therapeutic Stages

| Stage | Reflection levels |
| --- | --- |
| Trust Building | Exploring the Problem Event; Empathic Comforting |
| Problem Externalization | Negotiation of the Dominant Problem; Mapping Problem Effects; Evaluating Problem Effects; Justification of Evaluation |
| Re-authoring | Elaboration of Unique Outcomes; Exploration of Identity Landscape; Exploration of Action Landscape |
| Re-membering | Significant Others' Contributions; Self through Others; One's Contributions; Implications for Identity |

## Quick Start

### Prerequisites

- Python 3.10+
- OpenRouter API key or another OpenAI-compatible provider
- Network access on the first RAG build, because the BGE-M3 embedding model is downloaded from HuggingFace
- About 600 MB disk space for the BGE-M3 embedding model, plus local Chroma index files

### 1. Install dependencies

```bash
cd int
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your API key:

```text
OPENROUTER_API_KEY=your-openrouter-api-key
```

For a temporary smoke test before downloading BGE-M3, set `DISABLE_RAG=1`.
Therapeutic responses will still run, but RAG exemplar retrieval will be skipped.

### 3. Build the RAG index

INT uses 13 Markdown question-bank files under `backend/knowledge/`.
The first run downloads the BGE-M3 embedding model and builds a local Chroma index.
This can take several minutes depending on network speed and machine performance.

```bash
venv/bin/python backend/scripts/reindex_rag.py --force
```

Expected dry-run counts after the knowledge files are loaded:

```text
Knowledge files loaded: 13
Question documents parsed: 366
Collection: therapy_questions
```

Dry run without rebuilding:

```bash
venv/bin/python backend/scripts/reindex_rag.py
```

### 4. Start the server

```bash
venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open the participant UI:

```text
http://127.0.0.1:8000
```

Open the researcher dashboard:

```text
http://127.0.0.1:8000/admin.html
```

The example/default local admin key in `.env.example` is `change-me-before-running-admin`. Use it only for local testing and replace it in `.env` before sharing or deployment.

## Directory Structure

```text
int/
├── backend/
│   ├── main.py              # FastAPI app entry
│   ├── config.py            # Environment configuration
│   ├── database.py          # SQLite async persistence
│   ├── core/
│   │   ├── stages.py        # Stage definitions, reflection levels, prompts
│   │   ├── utils.py         # YAML parsing and pure helpers
│   │   ├── llm_client.py    # OpenRouter async LLM client
│   │   ├── rag_engine.py    # LlamaIndex + ChromaDB + BGE-M3 RAG
│   │   ├── narrative_memory.py
│   │   └── int_engine.py    # Stage -> reflection -> RAG -> response -> goal check
│   ├── routers/
│   │   ├── chat.py
│   │   └── sessions.py
│   └── knowledge/           # 13 narrative therapy question-bank files
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

## RAG Knowledge Reindex

The RAG knowledge base is stored as Markdown files under:

```text
backend/knowledge/
```

The current implementation only indexes files registered in:

```text
backend/core/stages.py
KNOWLEDGE_FILE_MAP
```

To supplement RAG:

1. Edit one of the existing stage/reflection `.md` files, or add a new `.md` file.
2. If adding a new file, register it in `KNOWLEDGE_FILE_MAP` with the correct internal `stage` and `level`.
3. Stop the running server.
4. Rebuild the Chroma index.

```bash
venv/bin/python backend/scripts/reindex_rag.py --force
```

5. Restart the server.

```bash
venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Notes:

- `chroma_db/` stores the local RAG vector index.
- `sessions.db` and `memory_chroma_db/` store user/session data.
- Deleting or rebuilding `chroma_db/` does not delete user conversations or memories in `sessions.db`.
- After adding or changing knowledge files, run `venv/bin/python backend/scripts/reindex_rag.py --force` again before starting the server.

## Long-Term Memory and Story Cards

INT stores local runtime state in SQLite:

```text
sessions.db
```

The memory subsystem is implemented in:

```text
backend/core/narrative_memory.py
```

Runtime behavior:

- Every session stores all turns, stage/reflection decisions, RAG hits, and trace logs.
- Participant memory is updated every `MEMORY_UPDATE_INTERVAL` turns, default `5`.
- Memory extraction tracks problem narratives, unique outcomes, preferred identity, session summaries, and narrative trajectories.
- Response generation retrieves a compact memory context instead of pasting every historical turn.
- "My Story" cards are available after `STORY_MIN_TURNS`, default `20`.
- Opening "My Story" only shows existing story history. Generating or updating a story requires clicking the separate generation button.

Important local files:

```text
sessions.db          # sessions, traces, memories, story cards
memory_chroma_db/    # optional local vector memory store
chroma_db/           # RAG index
```

These files are local runtime files created by the application.

## Simulation and Evaluation

Generate simulated INT dialogues:

```bash
venv/bin/python simulate_client.py \
  --esconv ../data/esconv_profiles/ESConv.json \
  --max-profiles 10 \
  --turns 35 \
  --language en \
  --output-dir ./simulation_output
```

Then run evaluation from the repository root:

```bash
cd evaluation
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

IMA / IMCS:

```bash
cd ima
../venv/bin/python IMCS_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/imcs \
  --number INT-full \
  --language en
```

Therapeutic dimension metrics:

```bash
cd ../dimension_metrics
../venv/bin/python dimention_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/dimensions \
  --number INT-full
```

## API Reference

### `POST /api/chat`

Send a user message and receive a Server-Sent Events stream.

Request body:

```json
{
  "session_id": "optional-existing-session-id",
  "message": "I have been under a lot of pressure recently.",
  "participant_id": "P001"
}
```

### `GET /api/session/{session_id}`

Retrieve the full session record including all turns.

### `GET /api/sessions`

Researcher endpoint for all session summaries. Requires the admin key via query or header.

```bash
curl "http://127.0.0.1:8000/api/sessions?admin_key=$ADMIN_KEY"
curl -H "X-Admin-Key: $ADMIN_KEY" "http://127.0.0.1:8000/api/sessions"
```

### `GET /api/participant/{participant_id}/sessions`

Retrieve one participant's session summaries for the participant-side history list.

### `GET /api/participant/{participant_id}/stories`

Read story-card history only; this does not trigger story generation.

### `POST /api/participant/{participant_id}/story`

Generate or update a personal story card. Available after `STORY_MIN_TURNS`; returns cached content when the current turn count has not changed.

### `GET /api/export/{session_id}`

Export a session as a JSON file in an IMA-compatible format.

### `GET /health`

Health check.

## Tech Stack

| Component | Technology |
| --- | --- |
| Web framework | FastAPI + Uvicorn |
| LLM access | OpenRouter / OpenAI-compatible API |
| Embedding model | BAAI/BGE-M3 via sentence-transformers |
| Vector database | ChromaDB |
| RAG framework | LlamaIndex |
| Session storage | SQLite with aiosqlite |
| Frontend | Plain HTML/CSS/JS |

## Citation

```bibtex
@inproceedings{feng2025reframe,
  title={Reframe Your Life Story: Interactive Narrative Therapist and Innovative Moment Assessment with Large Language Models},
  author={Feng, Yi and Wang, Jiaqi and Zhang, Wenxuan and Chen, Zhuang and Yutong, Shen and Xiao, Xiyao and Huang, Minlie and Jing, Liping and Yu, Jian},
  booktitle={Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing},
  pages={24495--24520},
  year={2025}
}
```
