from pathlib import Path
from typing import Dict, List

import chromadb
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from ..config import settings
from .stages import KNOWLEDGE_FILE_MAP

KNOWLEDGE_DIR: Path = Path(__file__).parent.parent / "knowledge"


class RAGEngine:
    def __init__(self) -> None:
        self._index: VectorStoreIndex | None = None
        self._chroma_client: chromadb.PersistentClient | None = None
        self._embed_model: HuggingFaceEmbedding | None = None

    def initialize(self) -> None:
        """
        Initialize the embedding model, ChromaDB client, and LlamaIndex index.

        On first run the model weights are downloaded from HuggingFace and the
        knowledge documents are embedded and stored.  Subsequent runs reuse the
        persisted ChromaDB collection.
        """
        # 1. Load BGE-M3 embedding model (downloads on first run)
        self._embed_model = HuggingFaceEmbedding(
            model_name=settings.embedding_model,
            trust_remote_code=True,
        )

        # 2. Persistent ChromaDB client
        self._chroma_client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir
        )
        collection = self._chroma_client.get_or_create_collection(
            name="therapy_questions",
            metadata={"hnsw:space": "cosine"},
        )

        # 3. Build index from scratch if the collection is empty, otherwise reuse
        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        if collection.count() == 0:
            documents = self._load_knowledge_files()
            self._index = VectorStoreIndex.from_documents(
                documents,
                storage_context=storage_context,
                embed_model=self._embed_model,
                show_progress=True,
            )
        else:
            self._index = VectorStoreIndex.from_vector_store(
                vector_store,
                embed_model=self._embed_model,
            )

    def _load_knowledge_files(self) -> List[Document]:
        """
        Parse all 13 knowledge .md files.

        Each file stores pipe-separated therapy questions.  Every individual
        question becomes an independent ``Document`` with stage and
        reflection-level metadata so it can be filtered during retrieval.
        """
        documents: List[Document] = []
        for filename, meta in KNOWLEDGE_FILE_MAP.items():
            filepath = KNOWLEDGE_DIR / filename
            if not filepath.exists():
                continue
            content = filepath.read_text(encoding="utf-8")
            questions = [
                q.strip().strip("**").strip() for q in content.split("|") if q.strip()
            ]
            for q in questions:
                if len(q) > 5:  # skip fragments that are too short
                    doc = Document(
                        text=q,
                        metadata={
                            "stage": meta["stage"],
                            "reflection_level": meta["level"],
                            "filename": filename,
                        },
                    )
                    documents.append(doc)
        return documents

    async def retrieve(
        self,
        query: str,
        stage: str,
        reflection_level: str,
        top_k: int = 3,
    ) -> List[str]:
        """
        Retrieve the top-k most relevant exemplar questions for the given query,
        filtered to the current stage and reflection level.
        """
        from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

        if self._index is None:
            return []

        filters = MetadataFilters(
            filters=[
                MetadataFilter(key="stage", value=stage),
                MetadataFilter(key="reflection_level", value=reflection_level),
            ]
        )
        retriever = self._index.as_retriever(
            similarity_top_k=top_k,
            filters=filters,
        )
        nodes = retriever.retrieve(query)
        return [node.get_content() for node in nodes]


rag_engine = RAGEngine()
