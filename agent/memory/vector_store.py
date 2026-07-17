"""
Vector Store (RAG)
==================
Uploaded/created code files ko chunk karke ChromaDB me embed karta hai,
taky agent bare codebase me se sirf relevant hissa dhoond sake — poori
file har baar read karne ki bajaye.

Persistent hai: `data/chroma/` folder me disk par store hota hai, is liye
server restart hone par bhi index bana rehta hai.
"""

import os

import chromadb

from agent.memory.chunking import chunk_text
from agent.memory.embeddings import GeminiEmbeddingFunction

CHROMA_DIR = os.environ.get("CHROMA_DIR", "data/chroma")
COLLECTION_NAME = "code_chunks"


class CodeVectorStore:
    def __init__(self, api_key: str):
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=CHROMA_DIR)

        if api_key:
            self._embedding_fn = GeminiEmbeddingFunction(api_key=api_key)
        else:
            from chromadb.utils import embedding_functions
            self._embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embedding_fn,
        )

    def index_file(self, session_id: str, filename: str, content: str) -> None:
        """File ke purane chunks hata kar naye content se dobara index karta hai.
        Har baar jab file write/edit ho, isay call karo."""
        self.delete_file(session_id, filename)

        chunks = chunk_text(content)
        if not chunks:
            return

        ids = [f"{session_id}::{filename}::{c.chunk_index}" for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "session_id": session_id,
                "filename": filename,
                "start_line": c.start_line,
                "end_line": c.end_line,
            }
            for c in chunks
        ]
        self._collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def delete_file(self, session_id: str, filename: str) -> None:
        """Kisi file ke tamam chunks index se hata deta hai (delete ya
        overwrite se pehle purana index saaf karne ke liye)."""
        self._collection.delete(where={"$and": [
            {"session_id": session_id},
            {"filename": filename},
        ]})

    def delete_session(self, session_id: str) -> None:
        self._collection.delete(where={"session_id": session_id})

    def search(self, session_id: str, query: str, k: int = 5) -> list[dict]:
        """Query se semantically milte-julte top-k chunks dhoondta hai,
        sirf isi session ki files me se."""
        if hasattr(self._embedding_fn, "embed_query"):
            query_embedding = self._embedding_fn.embed_query(query)
        else:
            query_embedding = self._embedding_fn([query])[0]
            
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where={"session_id": session_id},
        )

        hits = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        for doc, meta in zip(documents, metadatas):
            hits.append(
                {
                    "filename": meta.get("filename"),
                    "start_line": meta.get("start_line"),
                    "end_line": meta.get("end_line"),
                    "text": doc,
                }
            )
        return hits
