"""
Embeddings
==========
ChromaDB ko embeddings chahiye hoti hain taky text ko vectors me convert
kiya ja sake aur semantic similarity search ho sake. Ye module Google ka
free "text-embedding-004" model use karke ChromaDB-compatible embedding
function provide karta hai.
"""

import os

from chromadb import Documents, EmbeddingFunction, Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

EMBEDDING_MODEL = os.environ.get("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")


class GeminiEmbeddingFunction(EmbeddingFunction):
    """ChromaDB collections ke liye Gemini-based embedding function."""

    def __init__(self, api_key: str, model: str = EMBEDDING_MODEL):
        self._client = GoogleGenerativeAIEmbeddings(model=model, google_api_key=api_key)

    def __call__(self, input: Documents) -> Embeddings:
        # LangChain ka embed_documents batch me kaam karta hai — ye
        # ek hi API call me multiple chunks embed kar deta hai (fast + kam quota use).
        return self._client.embed_documents(list(input))

    def embed_query(self, text: str) -> list[float]:
        """Search query ke liye alag embedding (Gemini query vs document
        embeddings ko thora differently treat karta hai, behtar results ke liye)."""
        return self._client.embed_query(text)
