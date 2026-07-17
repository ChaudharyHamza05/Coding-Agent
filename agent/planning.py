"""
Planning
========
Complex, multi-step requests ko chhote steps me todta hai, aur decide
karta hai ke koi request 'simple' hai ya 'complex' (plan ki zaroorat hai).
"""

import json
from agent.language import LANGUAGE_INSTRUCTIONS, detect_language
from agent.llm_provider import get_chat_model

_CLASSIFY_PROMPT = """Tum ek classifier ho. User ki coding request dekh kar
decide karo ke ye 'simple' hai ya 'complex':

- 'simple': ek chota, single-purpose task (jaise "ek function likho jo X kare",
  "is bug ko fix karo", "ye explain karo", chota sawal).
- 'complex': multi-part task jisme kai steps/files/features shamil hon
  (jaise "poori app banao jisme X, Y, Z ho", "ye system design karo").

Sirf ek lafz jawab do: 'simple' ya 'complex'. Kuch aur mat likho.

User ki request: {message}
"""

_PLAN_PROMPT = """Tum ek planning assistant ho. User ki request ko 3 se 6
chote, clear, sequential steps me todo. Har step ek concrete coding action
hona chahiye (jaise "X naam ki file banao jisme Y ho").

**CRITICAL: {language_instruction}**

Sirf JSON list return karo, kuch aur nahi (step ka text ek string ke roop
me, correct language me likha hua). Format:
["step 1 text", "step 2 text", ...]

User ki request: {message}
"""


def _get_llm(api_key: str = ""):
    # api_key param ab zaroori nahi (get_chat_model khud .env se provider
    # decide kar leta hai) — sirf backward-compatibility ke liye rakha hai.
    return get_chat_model(temperature=0)


async def classify_complexity(api_key: str, message: str) -> str:
    """Returns 'simple' ya 'complex'."""
    llm = _get_llm(api_key)
    response = await llm.ainvoke(_CLASSIFY_PROMPT.format(message=message))
    text = response.content if isinstance(response.content, str) else str(response.content)
    return "complex" if "complex" in text.lower() else "simple"


async def make_plan(api_key: str, message: str) -> list[str]:
    """User ki request ko steps ki list me todta hai — usi language me
    jis me user ne likha ho."""
    llm = _get_llm(api_key)
    language = detect_language(message)
    instruction = LANGUAGE_INSTRUCTIONS[language]

    response = await llm.ainvoke(_PLAN_PROMPT.format(message=message, language_instruction=instruction))
    text = response.content if isinstance(response.content, str) else str(response.content)

    # Model kabhi kabhi ```json fences ke sath deta hai, unhe saaf karte hain.
    cleaned = text.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        steps = json.loads(cleaned)
        if isinstance(steps, list) and all(isinstance(s, str) for s in steps):
            return steps
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: agar JSON parse na ho, to poori request ko ek hi step maan lo.
    return [message]

_VERIFY_PROMPT = """Tum ek quality-checker ho. User ki original request aur
ab tak ka kaam (files + unka content) dekh kar decide karo ke requirement
POORI tarah se puri hui hai ya kuch reh gaya hai/galat hai.

**CRITICAL: {language_instruction}**

Sirf JSON object return karo, kuch aur nahi (koi ```json fence nahi). Format:
{{"complete": true, "reason": ""}}
ya
{{"complete": false, "reason": "yahan chhota sa jumla ke kya missing/galat hai"}}

Original request: {message}

Ab tak ki files:
{files_summary}
"""


async def verify_completion(api_key: str, message: str, files_summary: str) -> dict:
    """Check karta hai ke ab tak ka kaam original request ko poora
    satisfy karta hai ya nahi."""
    llm = _get_llm(api_key)
    language = detect_language(message)
    instruction = LANGUAGE_INSTRUCTIONS[language]

    response = await llm.ainvoke(
        _VERIFY_PROMPT.format(message=message, files_summary=files_summary, language_instruction=instruction)
    )
    text = response.content if isinstance(response.content, str) else str(response.content)

    cleaned = text.strip().strip("`")
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, dict) and "complete" in result:
            return {"complete": bool(result["complete"]), "reason": result.get("reason", "")}
    except (json.JSONDecodeError, ValueError):
        pass

    # Parse fail ho to complete maan lete hain — taaky infinite loop na bane.
    return {"complete": True, "reason": ""}