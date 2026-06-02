---
description: One-shot pipeline for a new book — find it on Library Genesis, download the EPUB, safety-scan it, summarize (v2 neutral voice), fetch the cover, rebuild the index, then commit & push
argument-hint: <book title> [author] — e.g. "Debt: The First 5000 Years" or "The Black Swan Nassim Taleb"
---

You are a book onboarding pipeline. Given a book title (and optionally an author), you find an EPUB on Library Genesis, download it, verify it is safe, summarize it in neutral voice, fetch a cover, regenerate the index, and commit & push — all in one run, stopping only if something fails or looks unsafe.

The argument is: `$ARGUMENTS`

This skill chains together existing skills: `/summarize-book-v2` for the summary and `/fetch-cover` for the cover. Invoke those **directly in this session** (via the normal skill mechanism) — do **not** spawn `claude -p` subprocesses or pass any permission-bypass flags.

> **Provenance note:** Library Genesis hosts copyrighted material without authorization. This pipeline is intended for personal, educational summarization of books the user is entitled to read. The downloaded EPUB stays in the gitignored `books/` folder and is never committed; only the generated summary, cover, and index are pushed.

The pipeline is **mostly autonomous** — the user invoked it precisely so they don't have to babysit each step. Proceed without per-step confirmation, with two exceptions:
- **Edition ambiguity** (Step 2): if there is no single clearly-best EPUB, use `AskUserQuestion` to let the user pick.
- **Safety flag** (Step 4): if the scan finds anything suspicious, STOP and report — never summarize or commit an unsafe file.

Follow these steps exactly, in order.

---

## Step 0: Parse input and check for duplicates

1. Split `$ARGUMENTS` into a **title** and an optional **author**. If the whole argument is just a title, that's fine.
2. Derive a **clean book name**: the canonical title in Title Case with normal spaces and no edition/site junk (e.g. no `{md5}`, no `libgen`, no `[retail]`). Example: `Debt: The First 5,000 Years` → clean name `Debt The First 5000 Years` (drop characters awkward in filenames like `:` and `,`). Keep it human-readable.
3. Derive the **stem** = clean name with spaces replaced by underscores (e.g. `Debt_The_First_5000_Years`).
4. Derive the **output summary path** = `summaries/<stem>_summary.html`.
5. **If `summaries/<stem>_summary.html` already exists**, tell the user this book already has a summary and stop (do not re-onboard).
6. Also check whether a matching `.epub`/`.pdf` already sits in `books/`. If a usable EPUB is already there, you may skip the search/download (Steps 1–3) and jump to Step 4 using that file.

---

## Step 1: Search Library Genesis

The goal is to locate candidate **EPUB** editions. Site layouts change and may sit behind Cloudflare, so be adaptive.

1. Build a search query from the title (and author, if given).
2. **Try `curl` first** (fast, no browser). Use a real browser User-Agent, follow redirects, and set a timeout:
   ```
   curl -sL -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" --max-time 30 \
     "https://libgen.bz/index.php?req=<URL-encoded query>"
   ```
   If `libgen.bz` is unreachable or blocked, try the sibling mirrors in order: `https://libgen.li/`, `https://libgen.gs/`, `https://libgen.is/` (same fork family, similar `index.php?req=` search and result-table layout).
3. **Inspect the returned HTML** to understand the actual result-table columns (typically Title, Author(s), Publisher, Year, Language, File size, Extension, and Mirror/download links). Do not assume a fixed structure — read what's there.
4. **If the page is JS-rendered or Cloudflare-challenged** so curl returns no usable results, fall back to the Playwright browser tools: navigate to the search URL, take a snapshot, and read the rendered results table. Use Playwright only to *discover* the listing and the resolved download URL — do the actual binary download with `curl` (Step 3).
5. Collect candidate rows, capturing for each: title, author, year, language, file size, extension, and the link to the book's detail/download page (often a `file.php?id=…` link and/or an md5).

---

## Step 2: Choose the best EPUB edition

From the candidates, select **one** EPUB to download:

1. **Filter** to `extension = epub` and `language = English` (or unspecified-but-clearly-English).
2. **Rank** the survivors, preferring:
   - the **most recent edition / publication year** (the user typically wants the latest English edition),
   - a sensible file size (roughly **0.3 MB–40 MB**; reject 0-byte or absurdly large entries),
   - the closest **title/author match** to what was requested,
   - a clean retail/publisher EPUB over an obvious scan or conversion.
3. **Decide:**
   - If there is a single clearly-best match, briefly tell the user what you picked (title · author · year · size) and proceed.
   - If several editions are plausibly "best," or the best match is weak/uncertain, use **`AskUserQuestion`** to let the user choose among the top 2–4 (show title · author · year · size for each).
4. If **no** acceptable EPUB exists (e.g. only PDFs, or only non-English), tell the user, suggest they try a different title/author phrasing, and stop. (Optionally offer to download a PDF instead — but only if the user confirms.)

---

## Step 3: Download the EPUB to `books/`

1. Open the chosen book's detail/download page and **resolve the actual file URL**. On the libgen.li/.bz fork this is usually reachable via a `GET`/download anchor or a `get.php?md5=<md5>` link; there may be several mirror options (direct, IPFS gateways such as a `cloudflare-ipfs.com/ipfs/…` link, etc.).
2. **Download with `curl`** to the clean target path, trying mirrors in order until one yields a valid file:
   ```
   curl -sL -A "Mozilla/5.0 …" --max-time 120 -o "books/<clean name>.epub" "<resolved download URL>"
   ```
   Save it as `books/<clean name>.epub` (the clean, human-readable name from Step 0 — **not** the libgen filename with md5/site tags).
3. **Verify it really is an EPUB** before trusting it:
   ```
   file "books/<clean name>.epub"                 # should report EPUB / Zip
   unzip -l "books/<clean name>.epub" | head       # should list mimetype + an .opf, not fail
   ```
   If the download is an HTML error page, a Cloudflare challenge, truncated, or not a valid zip, delete it and try the next mirror or next candidate. If nothing works, report failure and stop.
4. Be polite: `sleep` ~1s between mirror attempts; don't hammer the server.

---

## Step 4: Safety-scan the EPUB (malware / scripts)

An EPUB is a ZIP of HTML/CSS/images and can in principle smuggle scripts or disguised payloads. Run these checks and **STOP immediately if anything is flagged** — do not summarize or commit an unsafe file.

1. **Entry / extension audit** — list the archive and flag anything that is not benign book content:
   ```
   unzip -l "books/<clean name>.epub"
   ```
   Flag any `.js`, `.exe`, `.sh`, `.bat`, `.vbs`, `.scr`, `.dll`, `.jar`, `.php`, `.py`, `.htm`-with-scripts, path traversal (`../`), or absolute paths. A normal EPUB is only `.html`/`.xhtml`, `.css`, image files, `.opf`, `.ncx`, `mimetype`, and similar.
2. **Content scan** — extract to a temp dir and grep the markup:
   - `<script` tags
   - inline event handlers: `on(click|load|error|mouseover|focus)=`
   - `<iframe`, `<object`, `<embed`, `<applet>`
   - `javascript:` and `data:` URIs
   - suspicious external URLs (anything beyond ordinary citation links / standard EPUB & XML namespace declarations)
   - long embedded base64 blobs (e.g. `[A-Za-z0-9+/]{300,}`)
3. **Image sanity** — confirm files that claim to be images really are images (`file -b` on each), not disguised payloads.
4. **Verdict:**
   - **Clean** → report a one-line "safety: clean" summary and continue to Step 5.
   - **Suspicious** → STOP. Report exactly what was found and where, leave the file in `books/` for inspection (or offer to delete it), and do **not** proceed to summarization or commit.

---

## Step 5: Summarize with v2 (neutral voice)

Invoke the **`/summarize-book-v2`** skill directly in this session, passing the **exact EPUB filename** you saved in `books/` (e.g. `Debt The First 5000 Years.epub`).

- Use `/summarize-book-v2` (neutral direct-statement voice, no counterpoints, no quiz), **not** the standard `/summarize-book`.
- If summarization fails for any reason, **stop** and report what went wrong; do not continue to commit.
- On success, confirm the summary was written to `summaries/<stem>_summary.html`.

---

## Step 6: Fetch the cover

Invoke the **`/fetch-cover`** skill directly in this session, passing the **stem** (e.g. `Debt_The_First_5000_Years`).

- **Cover failures are non-fatal** — if it fails or finds no good cover, log a warning and continue.

---

## Step 7: Regenerate the index

```
./generate_index.sh
```

This rebuilds `summaries/index.html` to include the new summary (and its cover badge, if one was saved).

---

## Step 8: Commit & push

Stage **only** this book's artifacts — never `git add .` (the working tree may contain unrelated pre-existing untracked files like backups, `copy` duplicates, or `.playwright-mcp/`, which must not be swept in). The EPUB itself lives in the gitignored `books/` folder and will not be staged.

1. Stage exactly:
   ```
   git add summaries/<stem>_summary.html summaries/index.html
   git add summaries/covers/<stem>.jpg      # only if a cover was actually saved
   ```
2. Confirm with `git status --short` that only those files are staged.
3. Commit (adjust the body to say "summary" only if no cover was saved):
   ```
   git commit -m "Add <Title> summary and cover" \
     -m "Onboarded via libgen: v2 neutral-voice summary + cover; regenerated index." \
     -m "Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
   ```
4. Push to the current branch (this repo's convention is to commit directly to `main`, matching its history and the `/cp` skill):
   ```
   git push origin "$(git branch --show-current)"
   ```

---

## Step 9: Report

Give the user a concise final report:
- Which edition was downloaded (title · author · year · size) and to what path.
- Safety-scan result.
- Summary path and chapter count; confirmation it's v2 (no counterpoints, no quiz).
- Whether a cover was saved (or why not).
- The commit hash and that it was pushed.

---

## Important rules

- **Stop on the first hard failure** (no EPUB found, download invalid, safety flag, summarization failure). Cover-fetch failure is the only non-fatal step.
- **Never commit an unsafe or unverified file.** The safety scan gates everything downstream.
- **Selective git staging only** — explicitly avoid `git add .`.
- **Clean filenames** — strip libgen md5/site tags; save the EPUB under a human-readable name so the derived stem and summary filename are clean.
- **Be polite to Library Genesis** — real User-Agent, redirects, timeouts, and short sleeps between requests; try mirrors in order rather than retrying one aggressively.
- **No subprocesses, no permission bypass** — invoke `/summarize-book-v2` and `/fetch-cover` directly in this session.
