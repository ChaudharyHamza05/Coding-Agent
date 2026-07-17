"""
MCP Tools
=========
'mcp-server-code-runner' MCP server se tools load karta hai — ye asal
me code ko chala kar result deta hai (30+ languages support karta hai:
Python, JS, Java, C++, etc.). Ye server 'npx' se launch hota hai (Node.js
zaroori hai) aur us language ka interpreter/compiler PATH me hona chahiye
jis me code chalana ho.

Tools app startup par ek hi baar load ho kar cache ho jate hain.
"""

import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient

_mcp_client = MultiServerMCPClient(
    {
        "code_runner": {
            "command": "npx",
            "args": ["-y", "mcp-server-code-runner@latest"],
            "transport": "stdio",
        }
    }
)

_cached_tools = None


def get_mcp_tools():
    """MCP tools load karke cache karta hai. Agar MCP server start na ho
    paye (Node.js missing, ya koi aur masla), to khali list return karta
    hai — baaki agent normal kaam karta rahega, sirf code-execution tool
    available nahi hoga."""
    global _cached_tools
    if _cached_tools is not None:
        return _cached_tools

    try:
        _cached_tools = asyncio.run(_mcp_client.get_tools())
        print(f"[info] MCP Code Runner se {len(_cached_tools)} tools load hue.")
    except Exception as exc:
        print(f"[warning] Code Runner MCP server load nahi ho saka: {exc}")
        print("[warning] Check karein: Node.js installed hai? 'node --version' chalayein.")
        _cached_tools = []

    return _cached_tools