"""
Confluence integration for RAG pipeline.
Loads, chunks, and indexes Confluence pages into a vector database.
"""

import os
from typing import Optional
from langchain_community.document_loaders import ConfluenceLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams


class ConfluenceRAGPipeline:
    """Pipeline for indexing Confluence content for RAG retrieval."""

    def __init__(
        self,
        confluence_url: str,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "confluence_docs",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.confluence_url = confluence_url
        self.collection_name = collection_name

        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
        )

        # Initialize Qdrant client
        self.qdrant = QdrantClient(host=qdrant_host, port=qdrant_port)

        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def _get_confluence_loader(self, space_key: str) -> ConfluenceLoader:
        """Create a Confluence loader for a specific space."""
        return ConfluenceLoader(
            url=self.confluence_url,
            username=os.getenv("CONFLUENCE_USER"),
            api_key=os.getenv("CONFLUENCE_API_KEY"),
            space_key=space_key,
            include_attachments=False,
            limit=100,
        )

    def _ensure_collection(self, vector_size: int = 384):
        """Ensure the Qdrant collection exists."""
        collections = self.qdrant.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE,
                ),
            )

    def index_space(self, space_key: str) -> int:
        """
        Index all pages from a Confluence space.

        Args:
            space_key: The Confluence space key (e.g., "DATA", "ANALYTICS")

        Returns:
            Number of chunks indexed
        """
        print(f"Loading pages from Confluence space: {space_key}")

        loader = self._get_confluence_loader(space_key)
        documents = loader.load()
        print(f"Loaded {len(documents)} pages")

        # Split into chunks
        chunks = self.text_splitter.split_documents(documents)
        print(f"Split into {len(chunks)} chunks")

        # Ensure collection exists
        self._ensure_collection()

        # Index chunks
        Qdrant.from_documents(
            chunks,
            self.embeddings,
            url=f"http://{self.qdrant._client.host}:{self.qdrant._client.port}",
            collection_name=self.collection_name,
        )

        print(f"Indexed {len(chunks)} chunks to Qdrant")
        return len(chunks)

    def retrieve(self, query: str, k: int = 5) -> list[str]:
        """
        Retrieve relevant context for a query.

        Args:
            query: The search query
            k: Number of results to return

        Returns:
            List of relevant text chunks
        """
        try:
            vectorstore = Qdrant(
                client=self.qdrant,
                collection_name=self.collection_name,
                embeddings=self.embeddings,
            )
            docs = vectorstore.similarity_search(query, k=k)
            return [doc.page_content for doc in docs]
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []

    def retrieve_with_scores(
        self, query: str, k: int = 5
    ) -> list[tuple[str, float]]:
        """
        Retrieve relevant context with similarity scores.

        Args:
            query: The search query
            k: Number of results to return

        Returns:
            List of (text, score) tuples
        """
        try:
            vectorstore = Qdrant(
                client=self.qdrant,
                collection_name=self.collection_name,
                embeddings=self.embeddings,
            )
            results = vectorstore.similarity_search_with_score(query, k=k)
            return [(doc.page_content, score) for doc, score in results]
        except Exception as e:
            print(f"Retrieval error: {e}")
            return []


if __name__ == "__main__":
    # Example usage
    pipeline = ConfluenceRAGPipeline(
        confluence_url="https://your-company.atlassian.net/wiki",
        qdrant_host="localhost",
        qdrant_port=6333,
    )

    # Index a space
    # pipeline.index_space("DATA")

    # Test retrieval
    results = pipeline.retrieve("What is the definition of active user?")
    for i, result in enumerate(results):
        print(f"\n--- Result {i+1} ---")
        print(result[:500])
