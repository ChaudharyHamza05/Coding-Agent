"""
File Manager
============
Har session ki files ko disk par (`workspace/<session_id>/`) store karta
hai — is liye server restart hone par bhi files udd nahi jatin, jaisa
pehle in-memory dict ke sath hota tha.

Ye vector store ke sath bhi jura hota hai: jab bhi koi file likhi/edit/
delete ki jati hai, us ka RAG index (agent/memory/vector_store.py) khud
ba khud update ho jata hai.
"""

import os

from agent.memory.vector_store import CodeVectorStore

WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR", "workspace")


class FileManager:
    def __init__(self, session_id: str, vector_store: CodeVectorStore):
        self.session_id = session_id
        self.vector_store = vector_store
        self.session_dir = os.path.join(WORKSPACE_DIR, session_id)
        os.makedirs(self.session_dir, exist_ok=True)

    def _path(self, filename: str) -> str:
        # filename ke andar path traversal (../) rokte hain, security ke liye.
        safe_name = os.path.basename(filename)
        return os.path.join(self.session_dir, safe_name)

    def list_files(self) -> dict[str, str]:
        files = {}
        if not os.path.isdir(self.session_dir):
            return files
        for name in sorted(os.listdir(self.session_dir)):
            path = os.path.join(self.session_dir, name)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    files[name] = f.read()
        return files

    def file_names(self) -> list[str]:
        if not os.path.isdir(self.session_dir):
            return []
        return sorted(
            name for name in os.listdir(self.session_dir)
            if os.path.isfile(os.path.join(self.session_dir, name))
        )

    def exists(self, filename: str) -> bool:
        return os.path.isfile(self._path(filename))

    def read(self, filename: str) -> str:
        with open(self._path(filename), "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def write(self, filename: str, content: str) -> None:
        with open(self._path(filename), "w", encoding="utf-8") as f:
            f.write(content)

        if self.vector_store is not None:
            try:
                self.vector_store.index_file(self.session_id, filename, content)
            except Exception as exc:
                print(f"[warning] '{filename}' ke liye RAG index banane me masla hua: {exc}")

    def delete(self, filename: str) -> None:
        path = self._path(filename)
        if os.path.isfile(path):
            os.remove(path)
        if self.vector_store is not None:
            try:
                self.vector_store.delete_file(self.session_id, filename)
            except Exception as exc:
                print(f"[warning] '{filename}' ka RAG index hatane me masla hua: {exc}")

    def delete(self, filename: str) -> None:
        path = self._path(filename)
        if os.path.isfile(path):
            os.remove(path)
        if self.vector_store is not None:
            self.vector_store.delete_file(self.session_id, filename)
