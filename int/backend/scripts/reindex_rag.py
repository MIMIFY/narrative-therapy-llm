#!/usr/bin/env python3
"""Rebuild the local Chroma RAG index from backend/knowledge/*.md."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.config import settings  # noqa: E402
from backend.core.rag_engine import RAGEngine  # noqa: E402

COLLECTION_NAME = "therapy_questions"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild Chroma collection 'therapy_questions' from backend/knowledge/*.md."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Actually delete and rebuild the collection. Without this, only prints a dry run.",
    )
    args = parser.parse_args()

    engine = RAGEngine()
    documents = engine._load_knowledge_files()
    filenames = sorted({doc.metadata.get("filename", "") for doc in documents})

    print(f"Knowledge files loaded: {len(filenames)}")
    print(f"Question documents parsed: {len(documents)}")
    print(f"Chroma persist dir: {settings.chroma_persist_dir}")
    print(f"Collection: {COLLECTION_NAME}")

    if not args.force:
        print("Dry run only. Re-run with --force to rebuild the RAG index.")
        return 0

    print(f"Checking embedding model availability: {settings.embedding_model}")
    HuggingFaceEmbedding(
        model_name=settings.embedding_model,
        trust_remote_code=True,
    )

    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing collection: {COLLECTION_NAME}")
    except Exception as exc:  # noqa: BLE001
        print(f"No existing collection deleted: {exc}")

    engine.initialize()
    collection = engine._chroma_client.get_collection(COLLECTION_NAME)
    print(f"Reindex complete. Collection count: {collection.count()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
