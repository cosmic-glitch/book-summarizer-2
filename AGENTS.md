# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

A book summarizer that converts PDF and EPUB files into self-contained HTML summaries with chapter-level analysis, counterpoints, and comprehension quizzes. The summaries are hosted on Vercel with the deploy root set to `summaries/`.

## Key Commands

- `/summarize-book <filename>` — Summarize a single book from `books/` into `summaries/`
- `/summarize-all-pending [max_books]` — Find books in `books/` without summaries and process them sequentially (also fetches covers). Optional numeric argument caps the number of books processed in one session (e.g. `/summarize-all-pending 5`).
- `/fetch-cover <stem>` — Fetch a cover image for a book from Open Library (e.g., `/fetch-cover The_Intelligent_Investor`). Pass `all` to fetch all missing covers. Uses visual inspection to ensure covers are English, high-quality, and actually book covers.
- `./generate_index.sh` — Regenerate `summaries/index.html` from all existing summary files. Run this after adding new summaries.
- `python generate_audio.py <stem>` — Generate an MP3 audio version of a summary using OpenAI TTS (e.g. `python generate_audio.py Factfulness`). Defaults to `gpt-4o-mini-tts` with energetic audiobook narration instructions. Pass `--legacy` to use `tts-1-hd` instead. Requires `OPENAI_API_KEY` (stored in `.env`).
- `python patch_audio.py` — Inject sticky audio players into summary HTML files that have a corresponding MP3 in `summaries/audio/`. Idempotent — safe to re-run after adding new audio files. Also run `./generate_index.sh` afterward so the index shows audio badges.

## Architecture

- **`books/`** — Input PDFs and EPUBs (gitignored)
- **`summaries/`** — Output HTML files (Vercel deploy root). Contains `index.html` (auto-generated) and `*_summary.html` files
- **`temp/`** — Intermediate extraction files per book (gitignored, kept for traceability)
- **`.claude/commands/`** — Canonical workflow specifications for the summarization commands
- **`generate_index.sh`** — Parses title/author/subtitle from each summary HTML to build the index page
- **`generate_audio.py`** — Generates MP3 audio summaries via OpenAI TTS. Output goes to `summaries/audio/<stem>.mp3`
- **`.env`** — Local secrets (gitignored). Contains `OPENAI_API_KEY`

## Codex Interoperability

- The files in **`.claude/commands/`** are the canonical workflow specs for `/summarize-book`, `/summarize-all-pending`, and `/fetch-cover`.
- In Codex, these names are repository workflow names, not native Codex slash commands.
- When a user requests one of these workflows in Codex, open and follow the matching file in `.claude/commands/`.
- Map the user-supplied argument string to `$ARGUMENTS` exactly as the canonical workflow file expects.
- Do not duplicate, rewrite, or fork the canonical `.claude/commands/*.md` files during normal use.
- If a canonical workflow step says to run `claude -p`, Codex must treat that as a fresh-session `codex exec` subprocess that follows the same canonical workflow file semantics.
- For `/summarize-all-pending`, keep the parent Codex session responsible for pending-book discovery, alphabetical ordering, stop-on-first-failure behavior, non-fatal cover failures, and final index regeneration.
- For each per-book summarization subprocess in `/summarize-all-pending`, use `codex exec` to start a fresh Codex session that is instructed to read `.claude/commands/summarize-book.md`, treat the target filename as `$ARGUMENTS`, and execute that workflow without modifying the workflow file itself.
- For each cover subprocess in `/summarize-all-pending`, use `codex exec` to start a fresh Codex session that is instructed to read `.claude/commands/fetch-cover.md`, treat the target stem as `$ARGUMENTS`, and execute that workflow without modifying the workflow file itself.
- The `codex exec` substitution must preserve the existing batch semantics from the canonical file: isolated per-book execution, sequential processing, stop on first summarization failure, cover fetch failures are non-fatal, and `./generate_index.sh` runs only if at least one book was summarized successfully.
- When Codex executes `/summarize-book`, the fidelity rules below are mandatory and supplement the canonical `.claude` workflow without modifying it.

## Codex Summary Fidelity

- These rules apply only to Codex runs of `/summarize-book`.
- Use the extracted book text as the source of truth.
- Preserve and emphasize the book's important original vocabulary whenever it is central to the author's argument.
- Do not paraphrase away coined terms, named concepts, frameworks, slogans, analogies, or other distinctive phrases that the book relies on.
- When a chapter or section has recurring key terms, keep those exact terms visible in the summary and quiz.
- Prefer summaries that sound recognizably tied to the original book's language over summaries that sound generically "clean."
- Before finalizing, do a short self-check: have the most important original terms and phrases been retained, rather than replaced with broader abstractions?

## How Summarization Works

1. **Extract text**: PDFs use `pdftotext` (requires `poppler`). EPUBs are unzipped, OPF spine is parsed for reading order, HTML tags are stripped.
2. **Detect chapters**: Grep for patterns like "CHAPTER N", "Part N", roman numerals, Prologue/Epilogue etc.
3. **Summarize**: All chapters summarized in a single pass after ingesting full text. Counterpoints included for ~70-80% of chapters.
4. **Quiz**: 1-2 multiple-choice questions per chapter with explanations.
5. **Assemble HTML**: Single self-contained file with embedded CSS and JavaScript. The CSS template is defined in the summarize-book skill and must not be modified — it ensures visual consistency across all summaries.

## Conventions

- Output filenames: spaces replaced with underscores, appended with `_summary.html` (e.g., `The Intelligent Investor.pdf` → `The_Intelligent_Investor_summary.html`)
- Temp files go in `temp/<book name>/` with the extracted text at `temp/<book name>/<book name>_text.txt`
- Books are processed sequentially, never in parallel. Processing stops on first failure.
