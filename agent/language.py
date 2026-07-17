"""
Language Detection
==================
Har message ki language khud (deterministically) detect karta hai — LLM
par depend nahi karte ke wo lambi history me se sahi language yaad
rakhe. Ye result seedha system prompt me inject hota hai (agent/graph.py).
"""

import re

_URDU_SCRIPT_RE = re.compile(r"[\u0600-\u06FF]")

# Roman Urdu ke aam alfaz — agar in me se koi mile, to samjho Roman Urdu hai.
_ROMAN_URDU_MARKERS = {
    "hai", "hain", "ka", "ki", "ke", "ko", "mein", "me", "se", "aur", "kya",
    "kyun", "kyu", "nahi", "nahin", "ho", "raha", "rahi", "rahe", "kar",
    "karo", "kro", "krna", "karna", "tha", "thi", "the", "aap", "ap", "hum",
    "tum", "mujhe", "mujy", "hamen", "unko", "iska", "uska", "sakta", "sakte",
    "chahiye", "chahta", "chahti", "wala", "wali", "bhai", "yaar", "acha",
    "theek", "thik", "bilkul", "abhi", "sirf", "phir",
}


def detect_language(text: str) -> str:
    """Returns 'urdu_script', 'roman_urdu', ya 'english'."""
    if _URDU_SCRIPT_RE.search(text):
        return "urdu_script"

    words = re.findall(r"[a-zA-Z']+", text.lower())
    marker_hits = sum(1 for w in words if w in _ROMAN_URDU_MARKERS)

    if marker_hits >= 1:
        return "roman_urdu"

    return "english"


LANGUAGE_INSTRUCTIONS = {
    "english": "User ka message English me hai. Apna PURA jawab sirf aur sirf English me do — ek bhi Urdu/Hindi lafz mat mix karo.",
    "roman_urdu": "User ka message Roman Urdu me hai. Apna PURA jawab Roman Urdu me do.",
    "urdu_script": "User ka message Urdu script me hai. Apna PURA jawab Urdu script me do.",
}