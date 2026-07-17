"""
Agent Tools
===========
Ye woh functions hain jo agent khud call kar sakta hai. Ab ye seedha
FileManager (disk-backed) aur CodeVectorStore (RAG) ke sath kaam karte
hain, is liye files persistent hain aur bare codebases me semantic
search bhi mumkin hai.
"""

from langchain_core.tools import tool

from agent.files import FileManager
from agent.memory.vector_store import CodeVectorStore


def create_tools(file_manager: FileManager, vector_store: CodeVectorStore, session_id: str):

    @tool
    def list_files() -> str:
        """Session me maujood tamam files ke naam list karta hai. Kisi
        bhi file ke sath kaam karne se pehle ye check karne ke liye use
        karo ke konsi files available hain."""
        names = file_manager.file_names()
        if not names:
            return "Abhi tak koi file upload ya create nahi hui."
        return "Available files:\n" + "\n".join(f"- {name}" for name in names)

    @tool
    def read_file(filename: str) -> str:
        """Ek file ka poora content parhta hai (line numbers ke sath).
        filename bilkul wahi likho jo list_files se mila ho. Bari files
        ke liye agar sirf ek specific hissa chahiye ho, to iski jagah
        search_codebase use karna zyada behtar hai."""
        if not file_manager.exists(filename):
            return f"Error: '{filename}' naam ki file nahi mili. Pehle list_files check karo."
        content = file_manager.read(filename)
        numbered = "\n".join(f"{i+1}: {line}" for i, line in enumerate(content.splitlines()))
        return f"--- {filename} content (line numbers ke sath) ---\n{numbered}"

    @tool
    def search_codebase(query: str) -> str:
        """Session ki tamam files me se query ke semantically sab se
        zyada milte-julte hisse (chunks) dhoondta hai. Ye tab use karo
        jab codebase bara ho aur poori file parhna zaroori/practical na
        ho — jaise 'authentication logic kahan hai?' ya 'database
        connection kaha setup hoti hai?' jaisay sawalon ke liye."""
        hits = vector_store.search(session_id, query, k=5)
        if not hits:
            return "Koi relevant hissa nahi mila. Pehle files upload/create karo."

        parts = []
        for hit in hits:
            parts.append(
                f"--- {hit['filename']} (lines {hit['start_line']}-{hit['end_line']}) ---\n{hit['text']}"
            )
        return "\n\n".join(parts)

    @tool
    def write_file(filename: str, content: str) -> str:
        """Nayi file banata hai ya kisi existing file ko POORI TARAH
        overwrite karta hai naye content ke sath. Sirf tab use karo jab
        user ne pura naya code ya poori updated file mangi ho. Chote se
        change ke liye edit_file use karna behtar hai."""
        is_new = not file_manager.exists(filename)
        file_manager.write(filename, content)
        action = "create ki gayi" if is_new else "poori tarah update ki gayi"
        return f"'{filename}' successfully {action}."

    @tool
    def edit_file(filename: str, old_snippet: str, new_snippet: str) -> str:
        """Kisi file ke sirf ek chote hisse (snippet) ko dhoond kar
        replace karta hai, poori file dobara likhe bagair. old_snippet
        file me BILKUL waisa hi (exact match, whitespace samet) hona
        chahiye jaisa read_file me dikha tha. Ye tab use karo jab user
        ne kaha ho ke sirf ek hissa/function/line change karni hai,
        poori file nahi."""
        if not file_manager.exists(filename):
            return f"Error: '{filename}' naam ki file nahi mili."

        content = file_manager.read(filename)
        count = content.count(old_snippet)
        if count == 0:
            return (
                f"Error: old_snippet file '{filename}' me nahi mila. "
                f"Pehle read_file se exact text confirm karo, phir dobara try karo."
            )
        if count > 1:
            return (
                f"Error: old_snippet '{filename}' me {count} jagah match hua, "
                f"is liye ambiguous hai. Thora zyada context (surrounding lines) "
                f"shamil karke old_snippet ko unique banao."
            )

        updated = content.replace(old_snippet, new_snippet, 1)
        file_manager.write(filename, updated)
        return f"'{filename}' me diya gaya hissa successfully update ho gaya."

    @tool
    def delete_file(filename: str) -> str:
        """Session se ek file hata deta hai (disk aur RAG index dono se)."""
        if not file_manager.exists(filename):
            return f"Error: '{filename}' naam ki file nahi mili."
        file_manager.delete(filename)
        return f"'{filename}' delete ho gayi."

    return [list_files, read_file, search_codebase, write_file, edit_file, delete_file]
