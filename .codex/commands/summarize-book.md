---
description: Generate a chapter-level HTML summary of a PDF or EPUB book
argument-hint: <filename.pdf or filename.epub>
---

You are a book summarizer. Your task is to generate a chapter-level HTML summary of the book file provided by the user. The output is a self-contained HTML file styled consistently for a book summarizer website.

The book file is: `$ARGUMENTS`

Model constraint: this workflow must be executed entirely inside the current Codex subprocess and must use that subprocess's model only. In this repository, that means `gpt-5.4` only when invoked from `.codex/commands/summarize-all-pending.md` or equivalent `codex exec -m gpt-5.4 ...` commands.

Do not call the OpenAI API, do not use `curl` or any other HTTP client to reach model endpoints, do not use SDKs for model inference, and do not spawn any nested `codex exec` process for summarization. If you believe the book is too large or the current context is insufficient, stop and report that limitation instead of switching models.

Follow these steps exactly, in order.

---

## Step 1: Validate Input

1. Check that the file `$ARGUMENTS` exists in the `books/` folder (i.e., `books/$ARGUMENTS`).
2. Check that the file extension is `.pdf` or `.epub`. If not, tell the user: "Unsupported format. Please provide a .pdf or .epub file." and stop.
3. Derive the book name by stripping the extension (e.g., "The 4-Hour Workweek" from "The 4-Hour Workweek.epub").
4. Derive the output filename by replacing spaces with underscores and appending `_summary.html` (e.g., `The_4-Hour_Workweek_summary.html`). The output will be written to the `summaries/` folder.
5. Create a temp subfolder for this book's intermediate files: `temp/<book-name>/` (e.g., `temp/The 4-Hour Workweek/`). This folder persists after the run for traceability of intermediate outputs.
6. If `summaries/<output-filename>` already exists, do NOT treat it as source material and do NOT merely validate or lightly patch it. You must regenerate the summary from `books/$ARGUMENTS` and overwrite the existing output file with a fresh result derived from the current run.

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
5. For each HTML file in spine order, strip all HTML tags and concatenate the plain text. **Do this in a single Bash command** — e.g., loop over the files and pipe through `sed 's/<[^>]*>//g'` into the output file. Avoid multiple tool calls for this step.
6. Write the concatenated text to `temp/<book-name>/<book-name>_text.txt`
7. Do NOT clean up the temp directory — it is kept for traceability.

---

## Step 3: Detect Chapter Boundaries and Ingest Text

**IMPORTANT — minimize tool calls in this step.** The goal is to read the full book text and detect chapters with as few tool invocations as possible.

1. Use Grep to find candidate chapter boundary lines with their line numbers. Look for these patterns:
   - "Chapter N" or "CHAPTER N" (with or without a title after)
   - "Part N" or "PART N"
   - Roman numeral headings (I, II, III, IV, etc.)
   - Standalone numbered headings ("1", "2", etc. followed by a title)
   - Special sections: Prologue, Epilogue, Introduction, Foreword, Afterword, Preface, Conclusion

2. Build a list of chapters, each with a display title, start line, and end line. Skip front matter (copyright, dedication, table of contents) and back matter (index, bibliography, endnotes).

3. **Read the full book text using Bash** (e.g., `cat -n "temp/<book-name>/<book-name>_text.txt"`) to load the entire content in one call. Bash output supports much larger payloads than the Read tool. If the file is extremely large (>8000 lines), use two Bash calls to read it in halves. Avoid using the Read tool in a loop for dozens of small chunks — that is the primary bottleneck to avoid.

4. Tell the user what chapters you found before proceeding. For example:
   "Found 14 chapters: Preface (lines 50-120), Chapter 1: Title (lines 121-450), ..."

---

## Step 4: Summarize All Chapters (One-Shot)

**Summarize all chapters in a single pass.** Do NOT make separate tool calls per chapter. After ingesting the full text in Step 3, you have all the content in context — write all summaries at once.

For each chapter, in order:

1. **Summarize** the chapter in 2-5 explanatory paragraphs. Follow these rules:
   - Write in third person: "The author argues...", "The chapter introduces..."
   - Use `<b>bold</b>` for key concepts, frameworks, and important terms
   - Use `<i>italic</i>` for emphasis, book titles, and nuanced qualifications
   - Use `&mdash;` for em dashes
   - Reference ideas from prior chapters where relevant for continuity (e.g., "Building on the elimination framework from Chapter 6...")
   - The summary should explain the author's ideas to someone who hasn't read the book
2. **Decide on counterpoints.** Include a counterpoint section when:
   - The author makes non-standard or controversial claims
   - There are credible alternative explanations the author doesn't address
   - The evidence cited is disputed or has been challenged
   - The author overgeneralizes or oversimplifies

   Skip counterpoints when the chapter is primarily descriptive, instructional, or covers well-established ideas. Aim for counterpoints on roughly 70-80% of chapters.

   When writing counterpoints:
   - Present credible alternative perspectives, not strawman objections
   - Reference specific researchers, theories, or evidence where possible
   - Use `<b>bold</b>` for key terms in counterpoints too

After composing all summaries, tell the user how many chapters were summarized (e.g., "Summarized 14 chapters"). Then proceed to the quiz.

---

## Step 5: Generate the Quiz

After all chapters are summarized, generate a comprehension quiz:

1. **Number of questions:** ~1-2 per chapter (e.g., a 10-chapter book gets 12-15 questions, a 20-chapter book gets 25-30).
2. **Format:** Multiple choice with 4 options (a, b, c, d).
3. **Content:** Test the most important takeaways from the summaries you wrote — NOT raw book details that aren't in the summaries.
4. **Wrong options:** Should be plausible but clearly wrong if you've read the summary.
5. **Explanations:** Each question needs a brief explanation of why the correct answer is correct.

For each question, record:
- The question text
- Four options (a-d)
- Which option is correct
- A one-sentence explanation

---

## Step 6: Assemble the HTML File

Write the complete HTML file to `summaries/<output-filename>` (e.g., `summaries/The_4-Hour_Workweek_summary.html`). The file MUST use this exact structure and CSS. Do not modify the styles — they ensure visual consistency across all book summaries.

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

<!-- Counterpoint (only where warranted): -->
<details class="counter">
  <summary>Counterpoints</summary>
  <p>Counterpoint content...</p>
</details>

<!-- After all chapters, the quiz: -->
<h2 id="quiz-heading">Comprehension Quiz</h2>

<details id="quiz-section" class="quiz-wrapper">
  <summary class="quiz-toggle">Take the Quiz</summary>

  <form id="quiz-form">

    <!-- For each question: -->
    <div class="q-block">
      <p class="q-label">N. Question text?</p>
      <label><input type="radio" name="qN" value="a"> Option A</label>
      <label><input type="radio" name="qN" value="b"> Option B</label>
      <label><input type="radio" name="qN" value="c"> Option C</label>
      <label><input type="radio" name="qN" value="d"> Option D</label>
    </div>

    <button type="button" id="score-btn" onclick="scoreQuiz()">Score My Answers</button>

    <div id="quiz-result" style="display:none;">
      <p id="score-text"></p>
      <div id="answer-review"></div>
    </div>

  </form>
</details>

<script>
(function() {
  const answers = {
    // Populate with actual quiz data:
    // q1: { correct: "b", explain: "Explanation text." },
    // q2: { correct: "a", explain: "Explanation text." },
  };

  window.scoreQuiz = function() {
    const form = document.getElementById("quiz-form");
    let correct = 0;
    const total = Object.keys(answers).length;
    let reviewHTML = "";

    for (let i = 1; i <= total; i++) {
      const key = "q" + i;
      const selected = form.elements[key] ? form.elements[key].value : "";
      const isCorrect = selected === answers[key].correct;
      if (isCorrect) correct++;

      const status = !selected ? "wrong" : (isCorrect ? "correct" : "wrong");
      const icon = isCorrect ? "\u2705" : "\u274C";
      const yourAnswer = selected ? selected.toUpperCase() : "No answer";
      const correctAnswer = answers[key].correct.toUpperCase();

      reviewHTML += '<div class="review-item ' + status + '">';
      reviewHTML += '<div class="ri-q">' + icon + " Question " + i + "</div>";
      reviewHTML += '<div class="ri-detail">';
      if (!isCorrect) {
        reviewHTML += "Your answer: " + yourAnswer + " &mdash; Correct answer: " + correctAnswer + "<br>";
      }
      reviewHTML += answers[key].explain;
      reviewHTML += "</div></div>";
    }

    const pct = Math.round((correct / total) * 100);
    let grade;
    if (pct === 100) grade = "Perfect score!";
    else if (pct >= 80) grade = "Great understanding!";
    else if (pct >= 60) grade = "Good, but review the summaries above for the ones you missed.";
    else grade = "Consider re-reading the summaries above and trying again.";

    document.getElementById("score-text").textContent = correct + " / " + total + " (" + pct + "%) \u2014 " + grade;
    document.getElementById("answer-review").innerHTML = reviewHTML;
    document.getElementById("quiz-result").style.display = "block";
    document.getElementById("quiz-result").scrollIntoView({ behavior: "smooth", block: "start" });
  };
})();
</script>

</div><!-- .content -->

</body>
</html>
```

**Important rules for assembly:**
- The `answers` object in the `<script>` MUST be populated with the actual quiz data from Step 5. Each entry is `qN: { correct: "LETTER", explain: "Explanation." }`.
- If the book has no subtitle, omit the `<p class="subtitle">` line entirely.
- Replace `BOOK_TITLE`, `SUBTITLE_IF_ANY`, and `AUTHOR_NAME` with actual values extracted from the book's front matter.
- The radio input `name` attributes must be sequential: `q1`, `q2`, `q3`, etc.
- Do NOT modify the CSS. It must remain identical across all summaries for visual consistency.

---

## Step 7: Report Completion

Tell the user:
- The output file path
- How many chapters were summarized
- How many counterpoint sections were included
- How many quiz questions were generated
