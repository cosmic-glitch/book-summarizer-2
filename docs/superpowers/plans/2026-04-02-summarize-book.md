# summarize-book Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a Claude Code slash command `/summarize-book` that takes a PDF or EPUB file and generates a styled chapter-level HTML summary with counterpoints and a comprehension quiz.

**Architecture:** A single `.md` file defines the skill as a prompt-driven pipeline. Claude reads the prompt, extracts text from the book file, detects chapters, summarizes each sequentially, generates a quiz, and assembles everything into one self-contained HTML file matching summary2.html styling.

**Tech Stack:** Claude Code custom slash command (`.md`), `pdftotext` (poppler), `unzip`, Bash for text extraction

---

### File Structure

- **Create:** `.claude/commands/summarize-book.md` — The slash command skill file (the only deliverable)

This is a single-file project. The skill file is a markdown prompt that instructs Claude how to process a book. There is no application code, no tests, no dependencies to install.

---

### Task 1: Create the project-level .claude/commands directory

**Files:**
- Create: `.claude/commands/summarize-book.md`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p /Users/anuragved/code/book-summarizer-2/.claude/commands
```

- [ ] **Step 2: Write the skill file**

Create `.claude/commands/summarize-book.md` with the following exact content:

````markdown
---
description: Generate a chapter-level HTML summary of a PDF or EPUB book
argument-hint: <filename.pdf or filename.epub>
---

You are a book summarizer. Your task is to generate a chapter-level HTML summary of the book file provided by the user. The output is a self-contained HTML file styled consistently for a book summarizer website.

The book file is: `$ARGUMENTS`

Follow these steps exactly, in order.

---

## Step 1: Validate Input

1. Check that the file `$ARGUMENTS` exists in the current working directory.
2. Check that the file extension is `.pdf` or `.epub`. If not, tell the user: "Unsupported format. Please provide a .pdf or .epub file." and stop.
3. Derive the book name by stripping the extension (e.g., "The 4-Hour Workweek" from "The 4-Hour Workweek.epub").
4. Derive the output filename by replacing spaces with underscores and appending `_summary.html` (e.g., `The_4-Hour_Workweek_summary.html`).

---

## Step 2: Extract Text

**If the file is a PDF:**

1. Check that `pdftotext` is available. If not, tell the user: "pdftotext is not installed. Run `brew install poppler` and try again." and stop.
2. Run: `pdftotext "<filename>" "<book-name>_text.txt"`

**If the file is an EPUB:**

1. Create a temp directory: `mktemp -d` and save the path.
2. Unzip the EPUB into the temp directory: `unzip -o "<filename>" -d <tempdir>`
3. Find the `.opf` file: `find <tempdir> -name "*.opf"`
4. Read the OPF file to extract the spine reading order:
   - Parse the `<spine>` element to get the list of `idref` values in order
   - For each `idref`, look up the corresponding `href` in the `<manifest>` (only items with `media-type="application/xhtml+xml"`)
   - This gives you the ordered list of HTML file paths
5. For each HTML file in spine order, read it and strip all HTML tags (use `sed 's/<[^>]*>//g'` or similar), then concatenate the plain text
6. Write the concatenated text to `<book-name>_text.txt` in the working directory
7. Clean up the temp directory: `rm -rf <tempdir>`

---

## Step 3: Detect Chapter Boundaries

Scan the extracted text file for chapter/section boundaries. Look for lines matching these patterns:
- "Chapter N" or "CHAPTER N" (with or without a title after)
- "Part N" or "PART N"
- Roman numeral headings (I, II, III, IV, etc.)
- Standalone numbered headings ("1", "2", etc. followed by a title)
- Special sections: Prologue, Epilogue, Introduction, Foreword, Afterword, Preface, Conclusion

Use Grep to find candidate boundary lines with their line numbers. Then build a list of chapters, each with:
- A display title (e.g., "Chapter 3: The Art of Time Management")
- A start line number
- An end line number (the line before the next chapter starts, or end of file)

Skip front matter (copyright, dedication, table of contents) and back matter (index, bibliography, endnotes) — these are not chapters to summarize.

Tell the user what chapters you found before proceeding. For example:
"Found 14 chapters: Preface (lines 50-120), Chapter 1: Title (lines 121-450), ..."

---

## Step 4: Summarize Each Chapter Sequentially

Maintain a running list called **"Key Ideas So Far"** — a brief bullet list of the most important ideas encountered in prior chapters. Start it empty.

For each chapter, in order:

1. **Read** the chapter text from the extracted text file using the line ranges from Step 3.
2. **Summarize** the chapter in 2-5 explanatory paragraphs. Follow these rules:
   - Write in third person: "The author argues...", "Ferriss makes the case that...", "The chapter introduces..."
   - Use `<b>bold</b>` for key concepts, frameworks, and important terms
   - Use `<i>italic</i>` for emphasis, book titles, and nuanced qualifications
   - Use `&mdash;` for em dashes
   - Reference ideas from prior chapters where relevant for continuity (e.g., "Building on the elimination framework from Chapter 6...")
   - The summary should explain the author's ideas to someone who hasn't read the book
3. **Decide on counterpoints.** Include a counterpoint section when:
   - The author makes non-standard or controversial claims
   - There are credible alternative explanations the author doesn't address
   - The evidence cited is disputed or has been challenged
   - The author overgeneralizes or oversimplifies

   Skip counterpoints when the chapter is primarily descriptive, instructional, or covers well-established ideas. Aim for counterpoints on roughly 70-80% of chapters.

   When writing counterpoints:
   - Present credible alternative perspectives, not strawman objections
   - Reference specific researchers, theories, or evidence where possible
   - Use `<b>bold</b>` for key terms in counterpoints too
4. **Update Key Ideas So Far** — append 2-4 bullet points capturing this chapter's most important ideas.

After summarizing each chapter, tell the user you've completed it (e.g., "Completed Chapter 3 of 14"). Then proceed to the next.

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

Write the complete HTML file to `<output-filename>` in the working directory. The file must use this exact structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BOOK_TITLE — Chapter Summaries</title>
  <style>
    body {
      font-family: Georgia, 'Times New Roman', serif;
      max-width: 780px;
      margin: 40px auto;
      padding: 0 20px;
      line-height: 1.7;
      color: #222;
      background: #fafafa;
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

<h1>BOOK_TITLE</h1>
<p class="subtitle">SUBTITLE_IF_ANY</p>
<p class="author">AUTHOR_NAME</p>

<!-- Chapter sections go here -->
<!-- For each chapter: -->
<h2>Chapter N: Title</h2>
<p>Summary paragraphs...</p>

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
    // For each question, add an entry:
    // qN: { correct: "LETTER", explain: "Explanation text." },
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

</body>
</html>
```

**Important:** The `answers` object in the `<script>` must be populated with the actual quiz data from Step 5. Each entry is `qN: { correct: "LETTER", explain: "Explanation." }`.

If the book has no subtitle, omit the `<p class="subtitle">` line entirely.

---

## Step 7: Report Completion

Tell the user:
- The output file path
- How many chapters were summarized
- How many counterpoint sections were included
- How many quiz questions were generated
````

- [ ] **Step 3: Verify the skill file was created correctly**

```bash
ls -la /Users/anuragved/code/book-summarizer-2/.claude/commands/summarize-book.md
```

Expected: File exists, non-zero size.

---

### Task 2: Test with the EPUB book

- [ ] **Step 1: Invoke the skill**

Run `/summarize-book The 4-Hour Workweek.epub` in Claude Code from the `/Users/anuragved/code/book-summarizer-2` directory.

- [ ] **Step 2: Verify the output file was created**

```bash
ls -la /Users/anuragved/code/book-summarizer-2/The_4-Hour_Workweek_summary.html
```

Expected: File exists, likely 30-70 KB.

- [ ] **Step 3: Verify HTML structure**

Open the file in a browser and check:
- Title, subtitle, and author are correct
- All chapters have `<h2>` headings
- Summary paragraphs use bold/italic for key ideas
- Counterpoint sections are collapsible and styled with tan background/gold border
- Quiz is collapsible, all questions have 4 options, scoring works

- [ ] **Step 4: Verify visual consistency with summary2.html**

Open both `summary2.html` and the new summary side-by-side. The fonts, colors, spacing, heading styles, counterpoint boxes, and quiz styling should be identical.

---

### Task 3: Test with the PDF book

- [ ] **Step 1: Invoke the skill**

Run `/summarize-book Why Everyone (Else) Is a Hypocrite.pdf` in Claude Code from the `/Users/anuragved/code/book-summarizer-2` directory.

- [ ] **Step 2: Verify the output file was created**

```bash
ls -la "/Users/anuragved/code/book-summarizer-2/Why_Everyone_(Else)_Is_a_Hypocrite_summary.html"
```

Expected: File exists, likely 30-70 KB.

- [ ] **Step 3: Verify HTML structure and visual consistency**

Same checks as Task 2 Step 3 and Step 4. Additionally, compare the summary content against the existing `summary2.html` — the chapter structure and key ideas should be similar (though not identical, since this is a fresh generation).
