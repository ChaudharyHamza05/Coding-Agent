"""
LLM Provider
============
Chat model ka provider decide karta hai — agar .env me OPENAI_API_KEY set
hai (kisi bhi OpenAI-compatible endpoint ke liye, jaise local proxy,
DeepSeek, waghera), to wahi use hota hai. Warna Gemini use hota hai
(GOOGLE_API_KEY se). Is se poori app me sirf EK jagah provider switch
karna padta hai — baaki sab jagah yehi function call hota hai.
"""

import os

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "")
OPENAI_MODEL_NAME = os.environ.get("MODEL_NAME", "")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")


def has_active_provider() -> bool:
    """Kya koi bhi LLM provider configured hai (Gemini ya OpenAI-compatible)."""
    return bool(OPENAI_API_KEY or GOOGLE_API_KEY)


def get_chat_model(temperature: float = 0.2):
    """Jo bhi provider .env me configured ho, us ka LangChain chat model
    return karta hai — OPENAI_API_KEY ko priority milti hai agar set ho."""
    if OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        kwargs = {
            "api_key": OPENAI_API_KEY,
            "model": OPENAI_MODEL_NAME or "gpt-4o-mini",
            "temperature": temperature,
        }
        if OPENAI_BASE_URL:
            kwargs["base_url"] = OPENAI_BASE_URL
        return ChatOpenAI(**kwargs)

    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(model=GEMINI_MODEL, google_api_key=GOOGLE_API_KEY, temperature=temperature)