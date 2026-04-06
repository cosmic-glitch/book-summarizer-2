#!/usr/bin/env python3
"""
generate_audio.py — Generate an MP3 audio summary using OpenAI TTS.

Usage:
  python generate_audio.py <stem>
  python generate_audio.py Factfulness
  python generate_audio.py The_Intelligent_Investor

Reads summaries/<stem>_summary.html, extracts readable text (skips nav and
quiz), and saves an MP3 to summaries/audio/<stem>.mp3.

Requirements:
  pip install openai
  export OPENAI_API_KEY=sk-...
"""

import html
import os
import re
import sys
from pathlib import Path


# ── OpenAI TTS settings ───────────────────────────────────────────────────────

MODEL = "tts-1-hd"   # higher quality; good for long-form listening
VOICE = "nova"       # clear, pleasant, works well for non-fiction narration
MAX_CHUNK = 4096     # OpenAI TTS character limit per request


# ── HTML parsing ──────────────────────────────────────────────────────────────

def _decode(text: str) -> str:
    """Strip inline HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def extract_segments(html_content: str) -> list[tuple[str, str]]:
    """
    Parse a book summary HTML file and return an ordered list of
    (type, text) pairs. Types: title, subtitle, author, chapter, para,
    counterpoint.

    Skips: <nav>, <style>, <script>, and everything from the quiz heading on.
    """
    # Remove blocks that should never be read aloud
    h = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL)
    h = re.sub(r"<script[^>]*>.*?</script>", "", h, flags=re.DOTALL)
    h = re.sub(r"<nav[^>]*>.*?</nav>", "", h, flags=re.DOTALL)

    # Truncate at the quiz heading — nothing after this is useful for audio
    quiz_start = re.search(r'<h2[^>]*id=["\']quiz-heading["\']', h)
    if quiz_start:
        h = h[: quiz_start.start()]

    segments = []

    # ── Book header ──────────────────────────────────────────────────────────
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.DOTALL)
    if m:
        segments.append(("title", _decode(m.group(1))))

    m = re.search(r'<p[^>]*class=["\']subtitle["\'][^>]*>(.*?)</p>', h, re.DOTALL)
    if m:
        segments.append(("subtitle", _decode(m.group(1))))

    m = re.search(r'<p[^>]*class=["\']author["\'][^>]*>(.*?)</p>', h, re.DOTALL)
    if m:
        segments.append(("author", _decode(m.group(1))))

    # ── Chapter content ──────────────────────────────────────────────────────
    # Find the content div and work through it section by section
    content_m = re.search(r'<div[^>]*class=["\']content["\'][^>]*>(.*)', h, re.DOTALL)
    if not content_m:
        return segments

    content = content_m.group(1)

    # Split on <h2> tags to get one block per chapter
    parts = re.split(r"(<h2[^>]*>.*?</h2>)", content, flags=re.DOTALL)

    for part in parts:
        # Chapter heading
        h2 = re.match(r"<h2[^>]*>(.*?)</h2>", part, re.DOTALL)
        if h2:
            segments.append(("chapter", _decode(h2.group(1))))
            continue

        # Find counterpoint blocks so we can handle them separately
        counter_matches = list(re.finditer(
            r'<details[^>]*class=["\']counter["\'][^>]*>.*?<summary>[^<]*</summary>(.*?)</details>',
            part, re.DOTALL
        ))
        counter_spans = [(m.start(), m.end(), m.group(1)) for m in counter_matches]

        # Paragraphs not inside a counterpoint block
        for pm in re.finditer(r"<p[^>]*>(.*?)</p>", part, re.DOTALL):
            ps, pe = pm.start(), pm.end()
            # Skip if inside a counterpoint
            if any(cs <= ps and pe <= ce for cs, ce, _ in counter_spans):
                continue
            # Skip author/subtitle paragraphs (already captured above)
            tag = pm.group(0)
            if 'class="author"' in tag or 'class="subtitle"' in tag:
                continue
            text = _decode(pm.group(1))
            if text:
                segments.append(("para", text))

        # Counterpoint paragraphs
        for _, _, inner in counter_spans:
            text = _decode(inner)
            if text:
                segments.append(("counterpoint", text))

    return segments


# ── Script assembly ───────────────────────────────────────────────────────────

def build_script(segments: list[tuple[str, str]]) -> str:
    """Convert segments into a natural speech script."""
    title    = next((t for k, t in segments if k == "title"),    "")
    subtitle = next((t for k, t in segments if k == "subtitle"), "")
    author   = next((t for k, t in segments if k == "author"),   "")

    lines = []

    # Opening
    if subtitle:
        lines.append(f"Summary of {title}: {subtitle}, by {author}.")
    else:
        lines.append(f"Summary of {title}, by {author}.")

    for kind, text in segments:
        if kind in ("title", "subtitle", "author"):
            continue
        elif kind == "chapter":
            lines.append(f"\n\n{text}.\n")
        elif kind == "para":
            lines.append(text)
        elif kind == "counterpoint":
            pass  # excluded from audio

    return "\n".join(lines)


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, max_chars: int = MAX_CHUNK) -> list[str]:
    """Split text into chunks at sentence boundaries, under max_chars each."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        slen = len(sentence)
        if current and current_len + 1 + slen > max_chars:
            chunks.append(" ".join(current))
            current = [sentence]
            current_len = slen
        else:
            current.append(sentence)
            current_len += (1 if current_len else 0) + slen

    if current:
        chunks.append(" ".join(current))

    return chunks


# ── Audio generation ──────────────────────────────────────────────────────────

def generate_audio(chunks: list[str], output_path: Path) -> None:
    """Call OpenAI TTS for each chunk and write concatenated MP3."""
    from openai import OpenAI
    client = OpenAI()

    print(f"  Generating audio: {len(chunks)} chunk(s), model={MODEL}, voice={VOICE}")
    with open(output_path, "wb") as f:
        for i, chunk in enumerate(chunks, 1):
            print(f"  Chunk {i}/{len(chunks)} ({len(chunk):,} chars)...")
            response = client.audio.speech.create(
                model=MODEL,
                voice=VOICE,
                input=chunk,
            )
            f.write(response.content)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python generate_audio.py <stem>")
        print("Example: python generate_audio.py Factfulness")
        sys.exit(1)

    stem = sys.argv[1]
    # Allow passing the full filename or stem
    stem = re.sub(r"_summary\.html$", "", stem)
    stem = re.sub(r"\.html$", "", stem)

    html_path = Path(f"summaries/{stem}_summary.html")
    audio_dir = Path("summaries/audio")
    output_path = audio_dir / f"{stem}.mp3"

    if not html_path.exists():
        print(f"Error: {html_path} not found")
        sys.exit(1)

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is not set")
        sys.exit(1)

    try:
        from openai import OpenAI  # noqa: F401
    except ImportError:
        print("Error: openai package not installed. Run: pip install openai")
        sys.exit(1)

    audio_dir.mkdir(exist_ok=True)

    print(f"Extracting text from {html_path}...")
    content = html_path.read_text(encoding="utf-8")
    segments = extract_segments(content)
    script = build_script(segments)
    print(f"Script: {len(script):,} characters")

    chunks = chunk_text(script)
    generate_audio(chunks, output_path)

    size_kb = output_path.stat().st_size // 1024
    print(f"Done! Saved {size_kb:,} KB → {output_path}")


if __name__ == "__main__":
    main()
