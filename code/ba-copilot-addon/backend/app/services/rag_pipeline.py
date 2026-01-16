"""
RAG Pipeline for BA Copilot

Provides context retrieval from various knowledge sources.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class RetrievalResult:
    content: str
    source: str
    score: float


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.
    Retrieves relevant context from indexed documentation.
    """

    def __init__(
        self,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
        collection_name: str = "ba_copilot_knowledge",
    ):
        self.qdrant_host = qdrant_host or os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = qdrant_port or int(os.getenv("QDRANT_PORT", 6333))
        self.collection_name = collection_name
        self._initialized = False
        self._vectorstore = None

    def _initialize(self):
        """Lazy initialization of vector store connection."""
        if self._initialized:
            return

        try:
            from langchain_community.vectorstores import Qdrant
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from qdrant_client import QdrantClient

            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
            )

            self.qdrant_client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port,
            )

            # Check if collection exists
            collections = self.qdrant_client.get_collections().collections
            if any(c.name == self.collection_name for c in collections):
                self._vectorstore = Qdrant(
                    client=self.qdrant_client,
                    collection_name=self.collection_name,
                    embeddings=self.embeddings,
                )
                self._initialized = True
            else:
                print(f"Collection {self.collection_name} not found")

        except Exception as e:
            print(f"Failed to initialize RAG pipeline: {e}")

    def retrieve(self, query: str, k: int = 5) -> list[str]:
        """
        Retrieve relevant documents for a query.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of relevant text chunks
        """
        self._initialize()

        if not self._vectorstore:
            return []

        try:
            docs = self._vectorstore.similarity_search(query, k=k)
            return [doc.page_content for doc in docs]
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []

    def retrieve_with_scores(
        self, query: str, k: int = 5
    ) -> list[RetrievalResult]:
        """
        Retrieve documents with similarity scores.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of RetrievalResult objects
        """
        self._initialize()

        if not self._vectorstore:
            return []

        try:
            results = self._vectorstore.similarity_search_with_score(query, k=k)
            return [
                RetrievalResult(
                    content=doc.page_content,
                    source=doc.metadata.get("source", "unknown"),
                    score=score,
                )
                for doc, score in results
            ]
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []

    def add_documents(self, documents: list[dict]):
        """
        Add documents to the knowledge base.

        Args:
            documents: List of dicts with 'content' and 'metadata' keys
        """
        self._initialize()

        if not self._vectorstore:
            raise RuntimeError("Vector store not initialized")

        from langchain.schema import Document

        docs = [
            Document(
                page_content=doc["content"],
                metadata=doc.get("metadata", {}),
            )
            for doc in documents
        ]

        self._vectorstore.add_documents(docs)
