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

Use `curl` to search the Open Library API. First search the works endpoint to get edition lists:

```
https://openlibrary.org/search.json?title=<encoded_title>&author=<encoded_author>&limit=5&fields=key,cover_i,isbn,title,author_name,language
```

Also try a title-only search as a fallback:
```
https://openlibrary.org/search.json?title=<encoded_title>&limit=5&fields=key,cover_i,isbn,title,author_name,language
```

From the top matching work, fetch its full editions list to find all cover IDs:
```
https://openlibrary.org/works/<work_key>/editions.json?limit=50
```

Collect all unique cover IDs from:
- `cover_i` fields across search results
- `covers` arrays in each edition (skip IDs that are `-1`)

Also collect ISBNs from editions (prefer `9780`/`0` prefixes for English editions).

## Step 3: Download ALL candidates, then pick the best

**Do not accept the first passing candidate. Download all viable candidates first, then compare.**

### 3a: Download all candidates

For each candidate cover ID or ISBN (up to ~10 total), download to a temp file:
- For cover ID: `https://covers.openlibrary.org/b/id/<cover_id>-L.jpg` (use `-L` for large)
- For ISBN: `https://covers.openlibrary.org/b/isbn/<isbn>-L.jpg`

Skip any file under 5KB (placeholder). Add a `sleep 0.5` between downloads to be polite.

### 3b: Visually inspect all downloaded candidates

Use the Read tool to view **every** downloaded image. For each, note:
- Is it in English?
- Is it a printed book cover (not audiobook/CD/cassette packaging)?
- Is it clean and high quality (not a scanned physical copy, not blurry, not too dark)?
- Is it a modern edition (prefer newer, more vibrant covers over archaic ones)?
- Is the aspect ratio roughly that of a book (taller than wide)?

### 3c: Pick the best one

After inspecting all candidates, choose the single best cover. Prefer:
1. Clean, official-looking publisher cover art
2. Modern/vibrant over old/archaic
3. Not a photograph of a physical book
4. Not an audiobook or other non-book-cover format

If no candidate passes minimum quality checks (English, actual book cover, not blurry), report failure to the user.

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
