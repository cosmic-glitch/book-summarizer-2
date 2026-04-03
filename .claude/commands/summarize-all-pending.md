---
description: Summarize all books in books/ that don't already have a summary in summaries/
---

You are a batch book summarizer. Your task is to find all PDF and EPUB files in the `books/` folder that do not yet have a corresponding summary HTML file in the `summaries/` folder, and summarize each one by invoking the `/summarize-book` skill.

Follow these steps exactly:

## Step 1: Discover pending books

1. List all `.pdf` and `.epub` files in the `books/` folder.
2. For each file, derive the expected output filename: strip the extension, replace spaces with underscores, and append `_summary.html`. For example, `books/The Intelligent Investor.pdf` → `summaries/The_Intelligent_Investor_summary.html`.
3. Check which of those output files already exist in `summaries/`.
4. Build a list of **pending** books — those without a corresponding summary file.
5. Tell the user what you found. For example:
   - "Found 5 books in books/. 3 already have summaries. 2 pending: Book A.pdf, Book B.epub"
   - If there are no pending books, say "All books already have summaries. Nothing to do." and stop.

## Step 2: Summarize each pending book, one at a time

For each pending book, in alphabetical order:

1. Tell the user which book you are starting: "Summarizing 1 of N: <filename>"
2. Invoke the `/summarize-book` skill with the filename as the argument (e.g., `/summarize-book The Intelligent Investor.pdf`).
3. After the skill completes, confirm success: "Completed <filename>. Moving to next."
4. If any error occurs — including running out of context/token budget, a missing tool like `pdftotext`, a corrupt file, or any other failure — **stop immediately**. Tell the user which book failed and why, and list any remaining books that were not processed.

## Important rules

- Process books **sequentially**, one at a time. Do not attempt to parallelize.
- Stop on the **first failure**. Do not skip failed books and continue.
- The most likely failure mode is running out of token budget in Claude Code. If you notice you are close to the context limit, stop before starting the next book and tell the user how many remain.
