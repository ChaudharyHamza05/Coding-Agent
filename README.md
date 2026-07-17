# Coding Agent

Ek agentic coding assistant — web app jo user ki request par code likhta hai,
uploaded files parhta hai, un ke bare me sawalon ke jawab deta hai, aur
maang par code me tabdeeli karta hai (poori file ya sirf ek hissa).

Backend + Frontend **ek hi command se** chalte hain (alag se do servers
chalane ki zaroorat nahi). Chat history aur files dono **persistent**
hain — server restart hone ke baad bhi wapas mil jati hain.

## Project Structure

```
coding_agent/
├── app.py                        # FastAPI entrypoint — API + frontend dono yahin se serve hoti hain
├── agent/
│   ├── graph.py                    # LangGraph ReAct agent (Gemini LLM + tools + system prompt)
│   ├── tools.py                     # Agent tools: list_files, read_file, search_codebase,
│   │                                  #   write_file, edit_file, delete_file
│   ├── files.py                       # FileManager — disk par (workspace/<session_id>/) files
│   │                                    #   store karta hai, is liye restart ke baad bhi persist hoti hain
│   ├── session.py                        # Session lifecycle: naya session ya purana resume karna
│   └── memory/
│       ├── chunking.py                     # Code ko overlapping line-chunks me todta hai
│       ├── embeddings.py                     # Gemini embedding wrapper (RAG ke liye)
│       ├── vector_store.py                    # ChromaDB — semantic code search (RAG)
│       └── chat_store.py                       # ChromaDB — persistent chat history
├── static/
│   ├── index.html                     # Chat UI
│   ├── style.css                        # Styling
│   └── script.js                          # Frontend logic (chat, upload, session resume)
├── data/                                    # ChromaDB persistent storage (runtime me banta hai)
├── workspace/                                 # Har session ki actual files (runtime me banta hai)
├── requirements.txt
└── .env.example
```

## Kaise kaam karta hai (Memory + RAG)

- **Persistent chat history**: Har message ChromaDB me save hota hai
  (`agent/memory/chat_store.py`). Browser localStorage me apni `session_id`
  yaad rakhta hai — page reload ya server restart ke baad bhi wahi
  conversation wapas load ho jati hai.
- **Persistent files**: Upload ya create ki gayi files disk par
  `workspace/<session_id>/` me save hoti hain (`agent/files.py`) — restart
  se udd nahi jatin.
- **RAG (semantic code search)**: Jab bhi koi file likhi/edit hoti hai, ye
  automatically chunks me toot kar (`agent/memory/chunking.py`) Gemini
  embeddings ke sath ChromaDB me index ho jati hai
  (`agent/memory/vector_store.py`). Agent ke paas ek `search_codebase` tool
  hai jo bare codebase me se sirf relevant hissa dhoond leta hai, poori
  file parhne ki bajaye.

## Setup (pehli dafa)

1. Dependencies install karein:
   ```bash
   pip install -r requirements.txt
   ```

2. Free Gemini API key lein — [Google AI Studio](https://aistudio.google.com/apikey)
   par jayein, Google account se login karein, aur "Create API Key" par click karein.
   Koi credit card nahi chahiye.

3. `.env` file banayein (`.env.example` ko copy kar ke):
   ```bash
   cp .env.example .env
   ```
   Phir `.env` me apni API key daal dein:
   ```
   GOOGLE_API_KEY=aap_ki_asal_api_key_yahan
   ```

## Run karna (single command)

```bash
python app.py
```

Ye backend aur frontend dono ek hi process me chala dega. Browser me kholein:

```
http://localhost:8000
```

## Kaise use karein

- Seedha chat box me apni request likhein — jaise "Python me ek calculator bana do"
- File upload karne ke liye sidebar me **"+ file upload karein"** dabayein
- Upload ki gayi file ke bare me sawal poochein: "is file me kya bug hai?"
- Bare codebase me se kuch dhoondne ke liye: "authentication logic kahan hai?"
  (agent khud `search_codebase` use kar lega)
- Change mangwane ke liye: "is function ka naam change kar do" — agent khud
  decide karega ke sirf hissa update karna hai ya poori file
- **"+ naya session"** button se fresh chat shuru ho sakti hai (purani
  history/files alag rehti hain, delete nahi hotin)

## Notes

- Default chat model `gemini-2.5-flash` hai, embedding model
  `models/text-embedding-004` hai — dono free tier me available hain.
  `.env` me `GEMINI_MODEL` / `GEMINI_EMBEDDING_MODEL` se badal sakte hain.
- Agar kabhi "quota exceeded" ya "limit: 0" jaisa error aaye, to Google AI
  Studio me check karein ke model abhi bhi free tier me hai — kabhi kabhi
  Google purane models ko free tier se hata deta hai.
- Storage `data/` aur `workspace/` folders me hoti hai — inhe delete karne
  se sab sessions ki history/files saaf ho jayengi.
