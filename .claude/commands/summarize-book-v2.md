---
description: Generate a neutral-voice chapter-level HTML summary of a PDF or EPUB book (no counterpoints, no quiz)
argument-hint: <filename.pdf or filename.epub>
---

You are a book summarizer. Your task is to generate a chapter-level HTML summary of the book file provided by the user in **neutral direct-statement voice**. The output is a self-contained HTML file styled consistently for a book summarizer website.

This skill is a variant of `/summarize-book`. It differs in exactly three ways:

1. **Voice:** neutral direct-statement, not third-person author attribution and not first person.
2. **No counterpoints.**
3. **No comprehension quiz.**

The output filename is the same as `/summarize-book` — `<book>_summary.html` — so running this skill on a book that already has a standard summary will **overwrite** it. Always check for an existing file and ask the user before overwriting.

The book file is: `$ARGUMENTS`

Follow these steps exactly, in order.

---

## Step 1: Validate Input

1. Check that the file `$ARGUMENTS` exists in the `books/` folder (i.e., `books/$ARGUMENTS`).
2. Check that the file extension is `.pdf` or `.epub`. If not, tell the user: "Unsupported format. Please provide a .pdf or .epub file." and stop.
3. Derive the book name by stripping the extension (e.g., "The 4-Hour Workweek" from "The 4-Hour Workweek.epub").
4. Derive the output filename by replacing spaces with underscores and appending `_summary.html` (e.g., `The_4-Hour_Workweek_summary.html`). The output will be written to the `summaries/` folder. **If a file with this name already exists, tell the user and ask whether to overwrite before proceeding** — the existing file is likely a prior standard (third-person) summary that will be lost.
5. Create a temp subfolder for this book's intermediate files: `temp/<book-name>/` (e.g., `temp/The 4-Hour Workweek/`). This folder persists after the run for traceability of intermediate outputs.

---

## Step 2: Extract Text

All intermediate files for text extraction are stored in the book's temp subfolder: `temp/<book-name>/`.

**If the file is a PDF:**

1. Check that `pdftotext` is available. If not, tell the user: "pdftotext is not installed. Run `brew install poppler` and try again." and stop.
2. Run: `pdftotext "books/<filename>" "temp/<book-name>/<book-name>_text.txt"`

**If the file is an EPUB:**

1. Create an `epub_extract/` subdirectory inside the book's temp folder: `temp/<book-name>/epub_extract/`
2. Unzip the EPUB into that directory: `unzip -o "books/<filename>" -d "temp/<book-name>/epub_extract/"`
3. Find the `.opf` file: `find "temp/<book-name>/epub_extract/" -name "*.opf"`
4. Read the OPF file to extract the spine reading order:
   - Parse the `<spine>` element to get the list of `idref` values in order
   - For each `idref`, look up the corresponding `href` in the `<manifest>` (only items with `media-type="application/xhtml+xml"`)
   - Resolve each `href` relative to the OPF file's directory to get the absolute file path
   - This gives you the ordered list of HTML file paths
5. For each HTML file in spine order, strip all HTML tags and concatenate the plain text. **Do this in a single Bash command** — loop over the files and pipe through `sed 's/<[^>]*>/ /g'` (plus common entity substitutions like `&amp;`, `&#8212;`, `&#8217;`) into the output file.
6. Write the concatenated text to `temp/<book-name>/<book-name>_text.txt`
7. Do NOT clean up the temp directory — it is kept for traceability.

**Optional cleanup pass (recommended for EPUBs):** After extraction, normalize the text with `awk '{$1=$1};1' | awk 'NF || prev_nf {print; prev_nf=NF}'` to trim leading/trailing whitespace and collapse runs of blank lines. Save the result as `temp/<book-name>/clean.txt` and use it for the rest of the steps. This substantially reduces size and makes chunked reading more efficient.

---

## Step 3: Detect Chapter Boundaries and Ingest Text

**IMPORTANT — minimize tool calls in this step.** The goal is to read the full book text and detect chapters with as few tool invocations as possible.

1. Use Grep to find candidate chapter boundary lines with their line numbers. Look for these patterns:
   - "Chapter N" or "CHAPTER N" (with or without a title after)
   - "Part N" or "PART N"
   - Roman numeral headings (I, II, III, IV, etc.)
   - Standalone numbered headings ("1", "2", etc. followed by a title)
   - Special sections: Prologue, Epilogue, Introduction, Foreword, Afterword, Preface, Conclusion
   - For EPUBs extracted via the file-marker method above: also grep for `===FILE:` markers, which segment the spine into reliable chapter-sized blocks.

2. Build a list of chapters, each with a display title, start line, and end line. Skip front matter (copyright, dedication, table of contents) and back matter (index, bibliography, endnotes).

3. **Read the book text.** Prefer one or two Bash `cat`/`sed` calls that dump the whole file. If the text is too large to fit in a single tool result (roughly > 400 KB or > ~8000 lines), use one of these two strategies:
   - **Chunked Read calls:** Use the Read tool with `offset` and `limit` (≈ 600 lines per call stays under the 10k-token Read limit). Batch multiple independent Reads in parallel to reduce wall time.
   - **Delegate to a subagent (recommended for very large books):** Dispatch a `general-purpose` subagent with the exact chapter line ranges (from step 1) and ask it to return structured neutral-voice summaries for every chapter in a specific format. This keeps the raw text out of your context window entirely. See "Subagent delegation" below.

4. Tell the user what chapters you found before proceeding. For example:
   "Found 18 chapters: Introduction (lines 1-1136), Chapter 1: Title (lines 1145-2185), ..."

### Subagent delegation (for large books)

If you delegate, the subagent prompt must include:
- Absolute path to the cleaned text file
- The exact chapter boundaries you detected (title + start/end line)
- The neutral-voice constraints from Step 4 below, copied verbatim
- The exact list of section headings you want back (`### Introduction`, `### Chapter 1: ...`, etc.)
- An instruction to return **only** the labeled sections with no preamble and no closing commentary

**When parsing the subagent's output, strip any trailing harness metadata.** The Agent tool may append lines like `agentId: ...`, `<usage>total_tokens: ...`, `tool_uses: ...`, `duration_ms: ...` to the end of the response. Cut these off before writing to HTML. A safe sentinel is "the last line ending in `</p>`" — everything after that is metadata.

---

## Step 4: Summarize All Chapters (One-Shot) — Neutral Voice

**Summarize all chapters in a single pass.** Do NOT make separate tool calls per chapter. You already have the content in context (directly or via subagent).

For each chapter, write 2–5 explanatory paragraphs obeying these rules:

### Voice: neutral direct-statement

State the content of the chapter directly as claims and findings. Strip out all authorial framing.

- ❌ **Do not** write `"The author argues..."`, `"Piketty shows..."`, `"according to the author..."`, or similar third-person attribution.
- ❌ **Do not** write first-person `"I argue..."`, `"In this chapter I show..."`, `"my data..."`, etc. Even though the source book is written that way, the summary must NOT be.
- ✅ **Do** state the ideas themselves. The reader should feel they are reading the substance, not a report about someone else's ideas.

**Example (from Piketty's *Capital in the Twenty-First Century*):**
- ❌ Third person: *"Piketty argues that when the rate of return on capital exceeds the growth rate of the economy, inequality increases."*
- ❌ First person: *"I argue that when the rate of return on capital exceeds the growth rate, inequality increases."*
- ✅ Neutral: *"When the rate of return on capital durably exceeds the growth rate of the economy, inherited wealth grows faster than output and wages, and past fortunes dominate."*

### Formatting

- Use `<b>bold</b>` for key concepts, frameworks, and important terms.
- Use `<i>italic</i>` for emphasis and for book/paper titles.
- Use `&mdash;` for em dashes.
- Reference ideas from prior chapters for continuity, but in neutral voice (`"Building on the capital/income ratio framework introduced earlier..."`, not `"as the author showed in Chapter 5..."`).
- Wrap each paragraph in `<p>...</p>` so it can be dropped directly into the HTML template.
- Include substantive content: key data points, framework names, historical periodizations, specific numbers where they matter.

### Explicitly skipped in this variant

- **Do NOT include counterpoints.** In a neutral-voice summary, counterpoints re-introduce an outside perspective that breaks the voice. No `<details class="counter">` blocks.
- **Do NOT generate a quiz.** Skip Step 5 of the standard skill entirely.

After composing all summaries, tell the user how many chapters were summarized (e.g., "Summarized 18 chapters"). Then proceed directly to assembly.

---

## Step 5: Assemble the HTML File

Write the complete HTML file to `summaries/<output-filename>` (ending in `_summary.html`). The file MUST use this exact structure and CSS. The CSS is identical to the standard summarize-book template — do NOT modify it, for visual consistency across all summaries. The unused `.counter` and `.quiz-*` selectors are intentionally left in place.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BOOK_TITLE — Book Summary Pro</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: Georgia, 'Times New Roman', serif;
      line-height: 1.7;
      color: #222;
      background: #fafafa;
    }
    .app-nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #2c2c2c;
      padding: 14px 24px;
    }
    .content {
      max-width: 780px;
      margin: 0 auto;
      padding: 32px 20px 40px;
    }
    .app-nav .app-name {
      font-size: 1.05em;
      font-weight: bold;
      color: #e8e0d0;
      text-decoration: none;
      letter-spacing: 0.3px;
    }
    .app-nav .app-name:hover {
      color: #d4a843;
    }
    .app-nav .back-link {
      font-size: 0.9em;
      color: #999;
      text-decoration: none;
    }
    .app-nav .back-link:hover {
      color: #d4a843;
    }
    h1 {
      font-size: 1.8em;
      border-bottom: 2px solid #333;
      padding-bottom: 10px;
      margin-bottom: 5px;
    }
    .subtitle {
      font-size: 1.1em;
      color: #444;
      margin: 2px 0 0 0;
      font-style: italic;
    }
    .author {
      font-style: italic;
      color: #777;
      font-size: 0.95em;
      margin-bottom: 40px;
    }
    h2 {
      font-size: 1.3em;
      margin-top: 48px;
      color: #1a1a1a;
      border-left: 4px solid #555;
      padding-left: 12px;
    }
    p {
      margin-bottom: 14px;
      text-align: justify;
    }
    details.counter {
      background: #f0ece4;
      border-left: 4px solid #b8860b;
      padding: 14px 18px;
      margin: 20px 0 28px 0;
      border-radius: 0 6px 6px 0;
    }
    details.counter summary {
      font-weight: bold;
      font-size: 0.95em;
      color: #8b6914;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      cursor: pointer;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    details.counter summary::-webkit-details-marker {
      display: none;
    }
    details.counter summary::before {
      content: "\25B6";
      font-size: 0.7em;
      transition: transform 0.2s;
    }
    details.counter[open] summary::before {
      transform: rotate(90deg);
    }
    details.counter p {
      margin-top: 12px;
      margin-bottom: 10px;
      color: #3a3a3a;
    }
    details.counter p:last-child {
      margin-bottom: 0;
    }
    .quiz-wrapper {
      margin-top: 48px;
      background: #f5f5f0;
      border: 1px solid #ccc;
      border-radius: 6px;
      padding: 16px 20px;
    }
    .quiz-toggle {
      font-weight: bold;
      font-size: 1.05em;
      cursor: pointer;
      color: #2a5a2a;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .quiz-toggle::-webkit-details-marker { display: none; }
    .quiz-toggle::before {
      content: "\25B6";
      font-size: 0.7em;
      transition: transform 0.2s;
    }
    .quiz-wrapper[open] .quiz-toggle::before {
      transform: rotate(90deg);
    }
    .q-block {
      margin: 24px 0;
      padding-bottom: 20px;
      border-bottom: 1px solid #ddd;
    }
    .q-block:last-of-type { border-bottom: none; }
    .q-label {
      font-weight: bold;
      margin-bottom: 8px;
    }
    .q-block label {
      display: block;
      padding: 6px 10px;
      margin: 4px 0;
      border-radius: 4px;
      cursor: pointer;
      line-height: 1.5;
    }
    .q-block label:hover { background: #e8e8e0; }
    #score-btn {
      display: block;
      margin: 28px auto 0;
      padding: 12px 32px;
      font-family: Georgia, serif;
      font-size: 1em;
      background: #2a5a2a;
      color: #fff;
      border: none;
      border-radius: 6px;
      cursor: pointer;
    }
    #score-btn:hover { background: #1e441e; }
    #quiz-result {
      margin-top: 24px;
      padding: 18px;
      background: #fff;
      border: 1px solid #ccc;
      border-radius: 6px;
    }
    #score-text {
      font-size: 1.15em;
      font-weight: bold;
      text-align: center;
      margin-bottom: 16px;
    }
    .review-item {
      margin-bottom: 14px;
      padding: 10px 12px;
      border-radius: 4px;
    }
    .review-item.correct { background: #e6f4e6; }
    .review-item.wrong { background: #fce8e8; }
    .review-item .ri-q { font-weight: bold; margin-bottom: 4px; }
    .review-item .ri-detail { font-size: 0.93em; color: #444; }
  </style>
</head>
<body>

<nav class="app-nav">
  <a href="index.html" class="app-name">Book Summary Pro</a>
  <a href="index.html" class="back-link">&larr; All Books</a>
</nav>

<div class="content">

<h1>BOOK_TITLE</h1>
<p class="subtitle">SUBTITLE_IF_ANY</p>
<p class="author">AUTHOR_NAME</p>

<!-- For each chapter: -->
<h2>Chapter Title</h2>

<p>Summary paragraphs with <b>bold key terms</b> and <i>italic emphasis</i>...</p>

<!-- NO counterpoints. NO quiz. The content ends after the final chapter's last <p>. -->

</div><!-- .content -->

</body>
</html>
```

**Important rules for assembly:**
- Replace `BOOK_TITLE`, `SUBTITLE_IF_ANY`, and `AUTHOR_NAME` with actual values extracted from the book's front matter.
- If the book has no subtitle, omit the `<p class="subtitle">` line entirely.
- Do NOT include any `<details class="counter">` blocks.
- Do NOT include a `<h2 id="quiz-heading">` block, `<details id="quiz-section">`, `<form id="quiz-form">`, or any `<script>`.
- Do NOT modify the CSS. Leave the unused `.counter`, `.quiz-*`, `.q-block`, `.review-item`, and related selectors in place.
- The body content should end with the final chapter's last `</p>`, followed immediately by `</div><!-- .content -->`.

**Self-check before declaring done** — run all of these and confirm the expected result:

```bash
# 1. No author attribution
grep -cE "the author|according to the author|<AUTHOR_NAME> (argues|writes|shows|claims)" summaries/<output-filename>
# Expected: 0

# 2. No first-person narration
grep -ciE '\b(i argue|i show|i propose|i have shown|in this chapter i|in this book i)\b' summaries/<output-filename>
# Expected: 0

# 3. No counterpoint or quiz content in body (the CSS selectors still exist; that's fine)
grep -cE '<details class="counter"|<form id="quiz-form"|<div class="q-block"|id="quiz-heading"|scoreQuiz' summaries/<output-filename>
# Expected: 0

# 4. No subagent metadata leaked from delegation
grep -cE "agentId|total_tokens|tool_uses|duration_ms|SendMessage" summaries/<output-filename>
# Expected: 0

# 5. Chapter count matches what you detected
grep -c "<h2>" summaries/<output-filename>
```

If any of the first four return non-zero, fix the file before reporting completion.

---

## Step 6: Report Completion

Tell the user:
- The output file path
- How many chapters were summarized
- Explicit confirmation that no counterpoints and no quiz were included
- If a prior `_summary.html` existed for this book and was overwritten, say so explicitly

Do **NOT** run `./generate_index.sh` automatically. If the book is new (no prior index entry), mention that the user will need to run it to add the book to the index.
