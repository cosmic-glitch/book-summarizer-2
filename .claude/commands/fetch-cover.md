---
description: Fetch a high-quality English book cover image from Open Library
argument-hint: <Book_Name stem (e.g. The_Intelligent_Investor) or "all" for all missing covers>
---

You are a book cover fetcher. Your task is to find and download high-quality, English-language book cover images. You have a superpower that most scripts don't: you can **visually inspect** each candidate cover to verify it's correct before saving it.

The argument is: `$ARGUMENTS`

Follow these steps exactly, in order.

## Step 0: Determine mode

- If the argument is `all`, go to **Batch Mode** below.
- Otherwise, treat the argument as a single book stem and continue to Step 1.

## Batch Mode

When the argument is `all`:

1. List all `*_summary.html` files in `summaries/`.
2. For each, derive the stem (strip `_summary.html`). Check if `summaries/covers/<stem>.jpg` exists.
3. Build a list of books missing covers.
4. Tell the user what you found (e.g., "Found 14 books. 11 have covers. 3 missing: X, Y, Z").
5. If none are missing, say "All books already have covers. Nothing to do." and stop.
6. For each missing cover, **in alphabetical order**, process it through Steps 1–4 below. After each book, report progress (e.g., "Fetched 1 of 3: X. Moving to next.").
7. At the end, report a summary: how many fetched, how many failed (and which ones).

**Unlike summarization, cover fetch failures are non-fatal in batch mode.** Log the failure and continue to the next book.

---

## Step 1: Validate input

1. The argument is a **stem** — the book name with spaces replaced by underscores (e.g., `The_Intelligent_Investor`). If it contains a file extension (`.pdf`, `.epub`), strip it and convert spaces to underscores.
2. Check that `summaries/<stem>_summary.html` exists. If not, stop with an error.
3. Check if `summaries/covers/<stem>.jpg` already exists. If it does, tell the user and stop (don't re-fetch).
4. Extract the book title from the `<h1>` tag and the author from the `class="author"` element in the summary HTML.

## Step 2: Search Open Library

Use `curl` to search the Open Library API. Make multiple search queries to maximize results:

```
https://openlibrary.org/search.json?title=<encoded_title>&author=<encoded_author>&limit=5&fields=cover_i,isbn,title,author_name,language
```

Also try a title-only search as a fallback:
```
https://openlibrary.org/search.json?title=<encoded_title>&limit=5&fields=cover_i,isbn,title,author_name,language
```

From the results, collect:
- All ISBNs across the top results (prefer ISBNs starting with `9780` or `0` as these are English-language publishers, but collect others too)
- All `cover_i` IDs

## Step 3: Download and visually inspect candidates

Try to download cover images one at a time. For each candidate:

1. Download it to a temp file using `curl`:
   - For ISBN-based: `https://covers.openlibrary.org/b/isbn/<isbn>-M.jpg`
   - For cover_i-based: `https://covers.openlibrary.org/b/id/<cover_id>-M.jpg`
2. Check the file size — skip if under 1KB (placeholder image).
3. **Read the image file** using the Read tool so you can visually inspect it.
4. Evaluate the image. Ask yourself:
   - Is this actually a book cover (not an audiobook/CD, a photo, or a placeholder)?
   - Is it in English? (Reject covers in other languages)
   - Does it look like a reasonable quality cover (not extremely dark, blurry, or cropped)?
   - Is the aspect ratio roughly that of a book (taller than wide)?
5. If the image passes all checks, **accept it** and move to Step 4.
6. If it fails, delete the temp file and try the next candidate.

**Try candidates in this order:**
1. First try up to 5 English-publisher ISBNs (starting with `9780` or `0`)
2. Then try up to 3 `cover_i` IDs from the search results
3. Then try up to 3 non-English ISBNs as a last resort

Add a `sleep 0.5` between API calls to be polite.

If no candidate passes visual inspection after trying all options, report failure to the user.

## Step 4: Resize and save

Once you have a good cover image:

1. Use `sips --resampleWidth 200` to resize it to 200px wide (preserving aspect ratio).
2. Save the final image to `summaries/covers/<stem>.jpg`.
3. Clean up any temp files.
4. Confirm success: "Saved cover for <title> to summaries/covers/<stem>.jpg"

## Important rules

- **Always visually inspect** every candidate cover by reading the image file. This is the whole point of using a skill instead of a script — you can see what you're downloading.
- **Prefer English covers.** Only accept non-English covers if absolutely nothing else is available, and note this to the user.
- **Be polite to the API.** Sleep 0.5s between cover download attempts.
- **Clean up temp files.** Don't leave partial downloads in the covers directory.
