"""
Chunking
========
Bari code files ko chote, overlapping "chunks" me todta hai taky
vector store me embed kiya ja sake aur semantic search ke liye use ho sake.

Line-based chunking use karte hain (character-based ki bajaye) kyunke code
files ke liye line boundaries zyada maani-khaiz hoti hain — is se ek chunk
kabhi bhi kisi line ke beech me nahi katega.
"""

from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    start_line: int  # 1-indexed, inclusive
    end_line: int  # 1-indexed, inclusive
    chunk_index: int


def chunk_text(content: str, chunk_lines: int = 40, overlap_lines: int = 8) -> list[Chunk]:
    """
    content: file ka poora text
    chunk_lines: har chunk me kitni lines honi chahiyein
    overlap_lines: consecutive chunks ke darmiyan kitni lines overlap hongi
                   (taky context boundary pe na toote)

    Chote files (jo chunk_lines se kam hon) ek hi chunk ke roop me wapas
    aate hain — unhe todne ki zaroorat nahi.
    """
    lines = content.splitlines()
    total = len(lines)

    if total == 0:
        return []

    if total <= chunk_lines:
        return [Chunk(text=content, start_line=1, end_line=total, chunk_index=0)]

    chunks: list[Chunk] = []
    step = max(chunk_lines - overlap_lines, 1)
    start = 0
    index = 0

    while start < total:
        end = min(start + chunk_lines, total)
        chunk_lines_list = lines[start:end]
        chunks.append(
            Chunk(
                text="\n".join(chunk_lines_list),
                start_line=start + 1,
                end_line=end,
                chunk_index=index,
            )
        )
        index += 1
        if end == total:
            break
        start += step

    return chunks
