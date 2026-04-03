# Skill Design: summarize-book

**Date:** 2026-04-02
**Type:** Claude Code custom slash command
**Invocation:** `/summarize-book <filename>`

## Overview

A Claude Code skill that takes a PDF or EPUB book file and generates a chapter-level summary as a self-contained HTML file. The output matches the visual style of `summary2.html` so all summaries are visually consistent as part of a book summarizer website.

## Input

- A single argument: the book filename (relative to working directory)
- Supported formats: `.pdf`, `.epub`
- The skill validates the file exists and has a supported extension before proceeding

**Example invocations:**
```
/summarize-book The 4-Hour Workweek.epub
/summarize-book Why Everyone (Else) Is a Hypocrite.pdf
```

## Processing Pipeline

### Step 1: Text Extraction

**PDF:** Use `pdftotext` (from poppler) to extract full text to `<book-name>_text.txt` in the working directory.

**EPUB:** EPUB files are zip archives of HTML. Use `unzip` to extract `.htm`/`.xhtml` files, read the OPF manifest to determine correct reading order (spine), concatenate files in spine order, and strip HTML tags to produce plain text. Output to `<book-name>_text.txt`.

No additional tools beyond `pdftotext` and `unzip` are required.

### Step 2: Chapter Detection

Scan the extracted text file for chapter boundaries. Look for patterns including:
- "Chapter N", "CHAPTER N"
- "Part N", "PART N"
- Roman numeral headings
- Numbered headings
- Prologue, Epilogue, Introduction, Afterword, Foreword sections

Output a list of chapter/section titles with their line number ranges in the text file.

### Step 3: Sequential Chapter Summarization

Process chapters one at a time, in reading order. For each chapter:

1. **Read** the chapter text from the extracted file
2. **Summarize** in explanatory paragraphs using third-person voice ("the author argues...", "Kurzban makes the case that..."), with `<b>` and `<i>` for key ideas
3. **Reference prior chapters** where relevant for continuity (e.g., "Building on the modularity framework introduced in Chapter 2...")
4. **Decide on counterpoints** — include a counterpoint section when the author makes non-standard claims or when credible alternative explanations exist; skip when claims are well-established or purely descriptive. Target the same level of selectivity as summary2.html (counterpoints on ~70-80% of chapters)
5. **Maintain a running "key ideas so far" list** that grows as chapters are processed, giving each chapter access to the narrative thread without re-reading all prior full summaries

### Step 4: Quiz Generation

After all chapter summaries are complete, generate a comprehension quiz in a single pass:

- **Scale:** ~1-2 questions per chapter (e.g., 10-chapter book = ~12-15 questions, 20-chapter book = ~25-30)
- **Format:** Multiple choice, 4 options (a-d) per question
- **Scope:** Questions test ideas that appear in the summaries, not raw book details
- **Wrong options:** Plausible but clearly distinguishable from the correct answer
- **Explanations:** Each correct answer includes a brief explanation

### Step 5: HTML Assembly

Assemble all content into a single self-contained HTML file.

**Output filename:** `<book-name>_summary.html` in the working directory (spaces replaced with underscores).

**Structure and styling** must exactly match `summary2.html`:

#### Title Area
```html
<h1>Book Title</h1>
<p class="subtitle">Subtitle If Any</p>
<p class="author">Author Name</p>
```

#### Chapter Sections
```html
<h2>Chapter N: Title</h2>
<p>Summary paragraphs with <b>bold</b> and <i>italic</i> emphasis...</p>
```

#### Counterpoints (where warranted)
```html
<details class="counter">
  <summary>Counterpoints</summary>
  <p>Counterpoint content...</p>
</details>
```

#### Quiz
```html
<h2 id="quiz-heading">Comprehension Quiz</h2>
<details id="quiz-section" class="quiz-wrapper">
  <summary class="quiz-toggle">Take the Quiz</summary>
  <form id="quiz-form">
    <!-- Question blocks with radio inputs -->
    <button type="button" id="score-btn" onclick="scoreQuiz()">Score My Answers</button>
    <div id="quiz-result" style="display:none;">...</div>
  </form>
</details>
```

#### Embedded CSS

The exact CSS from `summary2.html` is embedded in every output file via a `<style>` tag. This includes styles for:
- Body, headings, paragraphs (Georgia serif, 780px max-width, #fafafa background)
- Subtitle and author
- Counterpoint `<details>` (tan #f0ece4, gold border #b8860b, rotatable triangle toggle)
- Quiz wrapper, question blocks, score button, result display
- Correct (#e6f4e6) and wrong (#fce8e8) answer highlighting

#### Embedded JavaScript

The quiz scoring JS is embedded via a `<script>` tag. It:
- Reads all radio inputs to check answers against a correct-answers map
- Calculates score as fraction, percentage, and grade
- Renders per-question review with correct/wrong indicators and explanations
- Scrolls to results on completion

## Output

- One HTML file: `<book-name>_summary.html`
- One intermediate text file: `<book-name>_text.txt`
- No git commits, no pushes, no other side effects

## Constraints

- The skill does not install packages — it relies on `pdftotext` (poppler) and `unzip` being available
- If `pdftotext` is not installed, the skill should instruct the user to run `brew install poppler`
- EPUB extraction uses only `unzip` and text processing (no calibre or pandoc required)
- All styling must be consistent across all generated summaries (same CSS in every file)
