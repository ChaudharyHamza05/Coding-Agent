"""
Chat Memory Store
=================
Conversation history ko ChromaDB me persist karta hai taky server restart
hone par bhi purani chat yaad rahe.

Is collection ke liye semantic search ki zaroorat nahi (hum sirf
session_id se sab messages wapas nikalte hain, order se) — lekin ChromaDB
har collection ke liye ek embedding function maangta hai. Chroma ka
built-in "default" embedding pehli dafa use hone par internet se ek model
download karta hai, jo firewall/limited-internet setups par fail ho sakta
hai. Is liye hum yahan ek chota, offline, hash-based embedding function
use karte hain — koi download, koi API key, koi extra dependency nahi.
"""

import hashlib
import os
import time
import uuid

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings

CHROMA_DIR = os.environ.get("CHROMA_DIR", "data/chroma")
COLLECTION_NAME = "chat_history"
_VECTOR_DIM = 16


class _OfflineHashEmbeddingFunction(EmbeddingFunction):
    """Bilkul offline, deterministic embedding — sirf isliye chahiye taky
    ChromaDB documents store kar sake. Semantic quality yahan matter nahi
    karti kyunke hum is collection par kabhi similarity search nahi karte,
    sirf metadata (session_id) se filter karte hain."""

    def __call__(self, input: Documents) -> Embeddings:
        vectors = []
        for text in input:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            vector = [b / 255.0 for b in digest[:_VECTOR_DIM]]
            vectors.append(vector)
        return vectors


class ChatMemoryStore:
    def __init__(self):
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(path=CHROMA_DIR)
        # Local, free, no-API-key, no-download embedding — sirf storage/
        # retrieval ke liye chahiye, semantic quality yahan matter nahi karti.
        self._embedding_fn = _OfflineHashEmbeddingFunction()
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embedding_fn,
        )

    def add_message(self, session_id: str, role: str, content: str, turn_index: int) -> None:
        self._collection.add(
            ids=[str(uuid.uuid4())],
            documents=[content],
            metadatas=[
                {
                    "session_id": session_id,
                    "role": role,
                    "turn_index": turn_index,
                    "timestamp": time.time(),
                }
            ],
        )

    def get_history(self, session_id: str) -> list[tuple[str, str]]:
        """Session ki poori history (role, content) tuples ki list ke
        roop me, sahi order me wapas deta hai."""
        result = self._collection.get(where={"session_id": session_id})

        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])

        paired = list(zip(metadatas, documents))
        paired.sort(key=lambda item: item[0].get("turn_index", 0))

        return [(meta["role"], doc) for meta, doc in paired]

    def has_history(self, session_id: str) -> bool:
        result = self._collection.get(where={"session_id": session_id}, limit=1)
        return len(result.get("ids", [])) > 0

    def clear_session(self, session_id: str) -> None:
        self._collection.delete(where={"session_id": session_id})

    def list_sessions(self) -> list[dict]:
        """Tamam sessions ki list deta hai (naye se purane order me),
        har ek ka pehla user message 'preview' ke roop me."""
        result = self._collection.get()
        metadatas = result.get("metadatas", [])
        documents = result.get("documents", [])

        sessions: dict[str, dict] = {}
        for meta, doc in zip(metadatas, documents):
            sid = meta["session_id"]
            entry = sessions.setdefault(sid, {
                "session_id": sid,
                "preview": None,
                "last_timestamp": 0,
                "first_turn": None,
            })
            entry["last_timestamp"] = max(entry["last_timestamp"], meta.get("timestamp", 0))

            if meta["role"] == "user":
                turn = meta.get("turn_index", 0)
                if entry["first_turn"] is None or turn < entry["first_turn"]:
                    entry["first_turn"] = turn
                    entry["preview"] = doc[:60]

        result_list = list(sessions.values())
        result_list.sort(key=lambda s: s["last_timestamp"], reverse=True)
        for s in result_list:
            s.pop("first_turn", None)
        return result_list
