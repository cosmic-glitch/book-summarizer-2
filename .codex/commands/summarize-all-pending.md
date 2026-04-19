---
description: Summarize all books in books/ that don't already have a summary in summaries/
argument-hint: [max_books] — optional maximum number of books to summarize this session (e.g. 3)
---

You are a batch book summarizer. Your task is to find all PDF and EPUB files in the `books/` folder that do not yet have a corresponding summary HTML file in the `summaries/` folder, and summarize each one by invoking the corresponding Codex workflow.

The argument is: `$ARGUMENTS`

If `$ARGUMENTS` is a positive integer, treat it as **MAX** — the maximum number of books to process this session. If it is empty, zero, or not a valid positive integer, treat MAX as unlimited.

Follow these steps exactly:

## Step 1: Discover pending books

1. List all `.pdf` and `.epub` files in the `books/` folder.
2. For each file, derive the expected output filename: strip the extension, replace spaces with underscores, and append `_summary.html`. For example, `books/The Intelligent Investor.pdf` → `summaries/The_Intelligent_Investor_summary.html`.
3. Check which of those output files already exist in `summaries/`.
4. Build a list of **pending** books (alphabetical order) — those without a corresponding summary file.
5. If MAX is set, truncate the pending list to the first MAX books.
6. Tell the user what you found. For example:
   - "Found 5 books in books/. 3 already have summaries. 2 pending: Book A.pdf, Book B.epub"
   - If MAX is set and truncated the list: "Found 20 pending. Processing first 3 of 20 this session (limit set)."
   - If there are no pending books, say "All books already have summaries. Nothing to do." and stop.

## Step 2: Summarize each pending book, one at a time

For each pending book, in alphabetical order:

1. Tell the user which book you are starting: "Summarizing 1 of N: <filename>"
2. Use the **Bash tool** to spawn an isolated Codex subprocess that will summarize the book in its own context window. Run the following command (with a timeout of 600000 milliseconds):

   ```
   codex exec -m gpt-5.4 -C "$PWD" --dangerously-bypass-approvals-and-sandbox --color never - <<EOF
   Read .codex/commands/summarize-book.md and execute it with $ARGUMENTS set to "<filename>".
   EOF
   ```

   Replace `<filename>` with the actual book filename (e.g., `The Intelligent Investor.pdf`). Each subprocess gets a **fresh context window**, so large books do not exhaust the parent session's context.

3. Check the exit code of the subprocess. Exit code 0 means success.
4. After a successful summarization, fetch the book's cover image by spawning another isolated subprocess:

   ```
   codex exec -m gpt-5.4 -C "$PWD" --dangerously-bypass-approvals-and-sandbox --color never - <<EOF
   Read .codex/commands/fetch-cover.md and execute it with $ARGUMENTS set to "<stem>".
   EOF
   ```

   Replace `<stem>` with the book's stem name (filename without extension, spaces replaced with underscores — e.g., `The Intelligent Investor.pdf` → `The_Intelligent_Investor`). If the cover fetch fails, log a warning but **do not stop** — cover failures are non-fatal.

5. After success, confirm: "Completed <filename>. Moving to next."
6. If the summarization subprocess fails (non-zero exit code), **stop immediately**. Tell the user which book failed, include the last ~20 lines of output for diagnosis, and list any remaining books that were not processed.

## Step 3: Regenerate the index

After all pending books have been successfully summarized, run:

```
./generate_index.sh
```

This updates `summaries/index.html` to include all newly generated summaries. Only run this step if at least one book was successfully summarized.

## Important rules

- Each book is summarized in its own **isolated subprocess** via `codex exec -m gpt-5.4`. This prevents large books from filling up the parent session's context window. Do NOT invoke `.claude/commands/*` or `claude -p` from Codex — always use the Codex subprocess approach.
- The summarization for each book must stay entirely inside that `gpt-5.4` subprocess. Do NOT call external model APIs, do NOT use SDK-based inference, and do NOT spawn nested model subprocesses to continue summarization work under a different model.
- Process books **sequentially**, one at a time. Do not attempt to parallelize.
- Stop on the **first failure**. Do not skip failed books and continue.
