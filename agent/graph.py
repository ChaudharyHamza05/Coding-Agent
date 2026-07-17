"""
LangGraph agent setup. Ye Gemini model ko tools ke sath jorta hai aur
ek ReAct-style agent (Think -> Act -> Observe -> Repeat) bana kar deta hai.
"""

import os
from agent.mcp_tools import get_mcp_tools
from langgraph.prebuilt import create_react_agent
from agent.llm_provider import get_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from agent.language import LANGUAGE_INSTRUCTIONS, detect_language
from agent.files import FileManager
from agent.memory.vector_store import CodeVectorStore
from agent.tools import create_tools

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_PROMPT = """Tum ek expert AI coding agent ho. Tumhara kaam hai user ki
requirements ke mutabik programming code likhna, uploaded code files parhna,
un ke bare me sawalon ke jawab dena, aur maang par code me changes karna.

**SAB SE ZAROORI RULE — LANGUAGE MATCHING (kabhi mat bhoolna):**
Har response se pehle, sirf USER KE SAB SE AAKHRI (latest) message ki
language/script check karo — pichle messages ki language ignore karo,
sirf abhi ka wala dekho:
- Agar latest message pure English me hai → jawab 100% English me do,
  ek bhi Urdu/Hindi lafz mat mix karo.
- Agar latest message Roman Urdu me hai (jaise "kya hal hai") → jawab
  Roman Urdu me do.
- Agar latest message Urdu script me hai (اردو) → jawab Urdu script me do.
- Agar user language switch kare (pehle Urdu me baat ki, ab English me
  poocha), to turant naye message ki language follow karo — purani
  language par mat atke raho.
Ye rule sirf explanation/commentary par lagu hota hai — code ke andar
variable names, keywords, comments hamesha standard English/programming
convention me hi rahenge.

Kaam karne ka tareeqa:
1. Agar user kisi file ke bare me pooche ya us me change chahe, pehle list_files
   aur phir read_file se us file ka current content dekh lo — kabhi guess mat karo.
2. Agar codebase bara hai ya specific logic dhoondni ho (jaise "authentication
   kahan hai"), to poori file read_file se parhne ki bajaye search_codebase
   use karo — ye semantically relevant hissa turant dhoond deta hai.
3. Agar user chahta hai ke sirf ek chota hissa (function, line, ya block) change ho,
   to edit_file tool use karo taky poori file dobara likhne ki zaroorat na pare.
4. Agar user chahta hai ke poori file dobara likhi jaye, ya nayi file banani ho,
   to write_file use karo.
5. **Agar ye clear na ho ke user poori updated file chahta hai ya sirf changed
   hissa, to code likhne se pehle ek chota sa clarifying sawal pooch lo.**
6. Jab code likho, to clean, working, aur achi tarah commented code do.
6.5. Naya code likhne ya kisi file me change karne ke baad, agar
   'run-code' (ya isi jaisa naam wala) MCP tool available ho, to usay
   use karke code ko asal me chala kar verify karo, jawab dene se
   pehle. Agar error aaye, khud fix karo aur dobara test karo (max
   2-3 koshishein), phir sahi/working code hi user ko dikhao.
   **CRITICAL: Apne FINAL jawab me tool ka RAW output (stdout/stderr)
   bhi hamesha ek alag fenced block me dikhao — sirf apne alfaz me
   summary mat do. User ko pata chalna chahiye ke code asal me chala
   gaya tha aur uska exact result kya tha.**
7. **CRITICAL: File tool (write_file/edit_file) use karne ke baad, apne FINAL
   chat reply me bhi hamesha poora code ek fenced code block
   (```python ... ```) ke andar dikhao. Sirf "file ban gayi" ya "code likh
   diya" jaisa summary kabhi mat do — user ko code turant chat me dikhna
   chahiye, file store me chhupa hua nahi rehna chahiye.**
8. Agar user sirf sawal poochay (explanation, debugging help, concept), to zaroori
   nahi ke koi tool call karo — bas seedha jawab do, sirf tab tools use karo jab
   kisi file ko parhna, likhna, edit ya search karna ho.
"""


def build_agent(
    api_key: str,
    session_id: str,
    file_manager: FileManager,
    vector_store: CodeVectorStore,
    model_name: str = DEFAULT_MODEL,
):
    """
    api_key: Google AI Studio se mila hua free Gemini API key
    session_id: current user session ki unique id
    file_manager: is session ki disk-backed files ka manager
    vector_store: is session ki RAG (semantic search) index
    """
    llm = get_chat_model(temperature=0.2)

    local_tools = create_tools(file_manager=file_manager, vector_store=vector_store, session_id=session_id)
    mcp_tools = get_mcp_tools()

    def dynamic_prompt(state):
        """Har turn par latest user message ki language dekh kar ek naya,
        taaza system message banata hai — is se language-matching kabhi
        'bhoolti' nahi, chahe conversation kitni bhi lambi ho."""
        messages = state["messages"]

        latest_text = ""
        for msg in reversed(messages):
            role = getattr(msg, "type", None)
            if role in ("human", "user") or (isinstance(msg, dict) and msg.get("role") == "user"):
                latest_text = msg.content if hasattr(msg, "content") else msg.get("content", "")
                break

        language = detect_language(latest_text)
        instruction = LANGUAGE_INSTRUCTIONS[language]

        full_prompt = f"{SYSTEM_PROMPT}\n\n**ABHI KE LIYE LANGUAGE RULE:** {instruction}"
        return [SystemMessage(content=full_prompt)] + list(messages)

    agent = create_react_agent(
        model=llm,
        tools=local_tools + mcp_tools,
        prompt=dynamic_prompt,
    )
    return agent
