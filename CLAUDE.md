# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A book summarizer that converts PDF and EPUB files into self-contained HTML summaries with chapter-level analysis, counterpoints, and comprehension quizzes. The summaries are hosted on Vercel with the deploy root set to `summaries/`.

## Key Commands

- `/summarize-book <filename>` — Summarize a single book from `books/` into `summaries/`
- `/summarize-all-pending` — Find books in `books/` without summaries and process them sequentially
- `./generate_index.sh` — Regenerate `summaries/index.html` from all existing summary files. Run this after adding new summaries.

## Architecture

- **`books/`** — Input PDFs and EPUBs (gitignored)
- **`summaries/`** — Output HTML files (Vercel deploy root). Contains `index.html` (auto-generated) and `*_summary.html` files
- **`temp/`** — Intermediate extraction files per book (gitignored, kept for traceability)
- **`.claude/commands/`** — Skill definitions that drive the summarization workflow
- **`generate_index.sh`** — Parses title/author/subtitle from each summary HTML to build the index page

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
