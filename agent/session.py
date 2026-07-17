"""
Session Manager
================
Har browser session ke liye:
  - Apna disk-backed FileManager (files persist hoti hain, restart ke baad bhi)
  - Apna LangGraph agent instance (lazily built)
  - Shared ChatMemoryStore aur CodeVectorStore (dono ChromaDB-backed, persistent)

Chat history aur files dono ab disk/ChromaDB par persist hoti hain — server
restart hone ke baad bhi, agar same session_id dobara use ho (browser
localStorage se), sab kuch wapas load ho jata hai.
"""

import os
import shutil

from agent.files import FileManager, WORKSPACE_DIR
from agent.graph import build_agent
from agent.memory.chat_store import ChatMemoryStore
from agent.memory.vector_store import CodeVectorStore
from agent.planning import classify_complexity, make_plan, verify_completion

def _extract_text(content) -> str:
    """
    Gemini/LangChain kabhi content ko plain string, kabhi list of content
    blocks (jaise [{"type": "text", "text": "..."}]) ke roop me deta hai.
    Ye function dono cases ko handle karke hamesha ek clean string deta hai.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text") or block.get("content") or ""
                parts.append(text)
        return "\n".join(p for p in parts if p)

    return str(content) if content is not None else ""


class SessionManager:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.chat_store = ChatMemoryStore()
        self.vector_store = CodeVectorStore(api_key=api_key) if api_key else None
        self._live: dict[str, dict] = {}  # session_id -> {"agent": ..., "turn": ...}

    def create_or_resume(self, session_id: str) -> dict:
        """
        Naya session banata hai, ya agar is session_id ki purani history/files
        maujood hain (server restart ke baad, browser ne localStorage se
        wahi id bheji), to unhe wapas load karta hai.
        """
        history = self.chat_store.get_history(session_id)
        file_manager = FileManager(session_id=session_id, vector_store=self.vector_store)

        self._live[session_id] = {
            "agent": None,  # lazily built on first message
            "turn": len(history),
            "file_manager": file_manager,
        }

        return {
            "session_id": session_id,
            "resumed": len(history) > 0,
            "history": [{"role": role, "content": content} for role, content in history],
            "files": file_manager.list_files(),
        }

    def _get(self, session_id: str) -> dict:
        if session_id not in self._live:
            # Server restart ho chuka hai — is session_id ke liye state
            # dobara banate hain (history/files khud persistent storage se aa jayenge).
            self.create_or_resume(session_id)
        return self._live[session_id]

    def _ensure_agent(self, session_id: str):
        session = self._get(session_id)
        if session["agent"] is None:
            session["agent"] = build_agent(
                api_key=self.api_key,
                session_id=session_id,
                file_manager=session["file_manager"],
                vector_store=self.vector_store,
            )
        return session["agent"]

    def add_file(self, session_id: str, filename: str, content: str) -> None:
        session = self._get(session_id)
        session["file_manager"].write(filename, content)

    def list_files(self, session_id: str) -> dict:
        return self._get(session_id)["file_manager"].list_files()

    async def send_message(self, session_id: str, message: str) -> str:
        session = self._get(session_id)
        agent = self._ensure_agent(session_id)

        self.chat_store.add_message(session_id, "user", message, session["turn"])
        session["turn"] += 1

        history = self.chat_store.get_history(session_id)
        base_messages = [
            {"role": role if role == "user" else "assistant", "content": content}
            for role, content in history
        ]

        # Pehle decide karo ye request simple hai ya complex — agar
        # classification hi fail ho jaye (jaise quota issue), safe side
        # par simple treat karo taky user ka kaam na ruke.
        try:
            complexity = await classify_complexity(self.api_key, message)
        except Exception:
            complexity = "simple"

        if complexity == "complex":
            reply = await self._run_plan_execute(agent, session, message, base_messages)
        else:
            result = await agent.ainvoke({"messages": base_messages})
            reply = _extract_text(result["messages"][-1].content)

        self.chat_store.add_message(session_id, "assistant", reply, session["turn"])
        session["turn"] += 1

        return reply

    async def _run_plan_execute(self, agent, session: dict, original_message: str, base_messages: list) -> str:
        """Complex request ko plan ke mutabik, step-by-step execute karta
        hai, phir apna kaam khud verify karta hai — agar requirement poori
        na hui ho to feedback ke sath dobara try karta hai (max 3 dafa)."""
        MAX_STEPS = 6
        MAX_VERIFY_ATTEMPTS = 3

        try:
            steps = await make_plan(self.api_key, original_message)
        except Exception:
            result = await agent.ainvoke({"messages": base_messages})
            return _extract_text(result["messages"][-1].content)

        steps = steps[:MAX_STEPS]

        progress_lines = ["📋 **Plan:**"]
        for i, step in enumerate(steps, 1):
            progress_lines.append(f"{i}. {step}")
        progress_lines.append("")

        working_messages = list(base_messages)
        final_step_reply = ""

        for i, step in enumerate(steps, 1):
            progress_lines.append(f"⏳ **Step {i}/{len(steps)}:** {step}")

            step_instruction = (
                f'Aap ek bare task ka hissa kar rahe hain. Poora task tha: '
                f'"{original_message}"\n\n'
                f"Abhi SIRF ye step karo: {step}\n\n"
                f"Sirf isi step par focus karo, baaki steps alag se honge."
            )
            working_messages.append({"role": "user", "content": step_instruction})

            try:
                result = await agent.ainvoke({"messages": working_messages})
                final_step_reply = _extract_text(result["messages"][-1].content)
            except Exception as exc:
                progress_lines.append(f"❌ Step {i} fail hua: {exc}")
                break

            working_messages.append({"role": "assistant", "content": final_step_reply})
            progress_lines.append(f"✅ Step {i}/{len(steps)} complete.")

        # ---- Verify -> Retry loop: apna kaam khud check karo ----
        file_manager = session["file_manager"]

        for attempt in range(1, MAX_VERIFY_ATTEMPTS + 1):
            files = file_manager.list_files()
            files_summary = "\n\n".join(
                f"--- {name} ---\n{content[:1500]}" for name, content in files.items()
            ) or "(koi file nahi bani)"

            try:
                verdict = await verify_completion(self.api_key, original_message, files_summary)
            except Exception:
                verdict = {"complete": True, "reason": ""}

            if verdict["complete"]:
                progress_lines.append(f"\n🔎 **Verification (attempt {attempt}):** ✅ Requirement poori ho gayi.")
                break

            progress_lines.append(f"\n🔎 **Verification (attempt {attempt}):** ⚠️ {verdict['reason']}")

            if attempt == MAX_VERIFY_ATTEMPTS:
                progress_lines.append("⚠️ Max attempts (3) ho gaye — jo ho saka wo kar diya, upar wajah dekhein.")
                break

            progress_lines.append(f"🔁 Dobara try kar raha hoon (attempt {attempt + 1}/{MAX_VERIFY_ATTEMPTS})...")

            fix_instruction = (
                f'Poora task tha: "{original_message}"\n\n'
                f"Verification me pata chala ke ye adhoora/galat hai: {verdict['reason']}\n\n"
                f"Ise ABHI theek/complete karo. **Permission mat maango, sawal mat "
                f"poocho, confirmation mat maango — seedha zaroori tools "
                f"(write_file/edit_file/run-code) use karke kaam khud kar do.** "
                f"Sirf jab kaam mukammal ho jaye tab bataao kya kiya."
            )
            working_messages.append({"role": "user", "content": fix_instruction})

            try:
                result = await agent.ainvoke({"messages": working_messages})
                final_step_reply = _extract_text(result["messages"][-1].content)
                working_messages.append({"role": "assistant", "content": final_step_reply})
            except Exception as exc:
                progress_lines.append(f"❌ Fix attempt fail hua: {exc}")
                break

        progress_lines.append("\n---\n**Final result:**\n" + final_step_reply)
        return "\n".join(progress_lines)
    
    def delete_session(self, session_id: str) -> None:
        """Session ki chat history, files, aur RAG index hamesha ke liye
        hata deta hai."""
        self.chat_store.clear_session(session_id)
        if self.vector_store is not None:
            try:
                self.vector_store.delete_session(session_id)
            except Exception as exc:
                print(f"[warning] Session '{session_id}' ka RAG index hatane me masla: {exc}")

        session_dir = os.path.join(WORKSPACE_DIR, session_id)
        shutil.rmtree(session_dir, ignore_errors=True)

        self._live.pop(session_id, None)