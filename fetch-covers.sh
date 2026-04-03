#!/usr/bin/env bash
# fetch-covers.sh — Downloads and resizes book cover thumbnails from Open Library
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUMMARIES_DIR="$SCRIPT_DIR/summaries"
COVERS_DIR="$SUMMARIES_DIR/covers"

mkdir -p "$COVERS_DIR"

# Check dependencies
for cmd in curl jq sips; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: $cmd is required but not installed." >&2
    exit 1
  fi
done

fetched=0
skipped=0
failed=0

for f in "$SUMMARIES_DIR"/*_summary.html; do
  [ -f "$f" ] || continue
  filename="$(basename "$f")"
  stem="${filename%_summary.html}"
  cover_path="$COVERS_DIR/${stem}.jpg"

  # Skip if cover already exists
  if [ -f "$cover_path" ]; then
    echo "SKIP: $stem (cover exists)"
    skipped=$((skipped + 1))
    continue
  fi

  # Extract title and author from the summary HTML
  title="$(grep -m1 '<h1>' "$f" | sed 's/<[^>]*>//g' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"
  author="$(grep -m1 'class="author"' "$f" | sed 's/<[^>]*>//g' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//' || true)"

  if [ -z "$title" ]; then
    echo "FAIL: $stem (could not extract title)"
    failed=$((failed + 1))
    continue
  fi

  echo "Fetching cover for: $title by $author"

  # URL-encode the search terms
  encoded_title="$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$title'''))")"
  encoded_author="$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$author'''))")"

  # Search Open Library (try title+author, then title only, then general query)
  cover_id=""
  for search_url in \
    "https://openlibrary.org/search.json?title=${encoded_title}&author=${encoded_author}&limit=1&fields=cover_i" \
    "https://openlibrary.org/search.json?title=${encoded_title}&limit=1&fields=cover_i" \
    "https://openlibrary.org/search.json?q=${encoded_title}+${encoded_author}&limit=1&fields=cover_i"; do

    response="$(curl -sL --max-time 15 "$search_url" || true)"
    [ -z "$response" ] && continue
    cover_id="$(echo "$response" | jq -r '.docs[0].cover_i // empty')"
    [ -n "$cover_id" ] && break
    sleep 1
  done

  if [ -z "$cover_id" ]; then
    echo "FAIL: $stem (no cover found on Open Library)"
    failed=$((failed + 1))
    continue
  fi

  # Download the medium-size cover
  cover_url="https://covers.openlibrary.org/b/id/${cover_id}-M.jpg"
  tmp_file="$COVERS_DIR/${stem}_tmp.jpg"

  if ! curl -sL --max-time 15 -o "$tmp_file" "$cover_url"; then
    echo "FAIL: $stem (download failed)"
    rm -f "$tmp_file"
    failed=$((failed + 1))
    continue
  fi

  # Verify we got an actual image (not a 1x1 placeholder or error page)
  file_size="$(wc -c < "$tmp_file" | tr -d ' ')"
  if [ "$file_size" -lt 1000 ]; then
    echo "FAIL: $stem (downloaded file too small — likely placeholder)"
    rm -f "$tmp_file"
    failed=$((failed + 1))
    continue
  fi

  # Resize to 120px wide using sips (preserves aspect ratio)
  sips --resampleWidth 120 "$tmp_file" --out "$cover_path" &>/dev/null

  rm -f "$tmp_file"
  actual_size="$(wc -c < "$cover_path" | tr -d ' ')"
  echo "  OK: saved ${stem}.jpg ($(( actual_size / 1024 ))KB)"
  fetched=$((fetched + 1))

  # Be polite to the API
  sleep 1
done

echo ""
echo "Done: $fetched fetched, $skipped skipped, $failed failed."
