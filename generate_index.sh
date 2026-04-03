#!/usr/bin/env bash
# generate_index.sh — Generates summaries/index.html from all *_summary.html files in summaries/
set -euo pipefail

SUMMARIES_DIR="$(cd "$(dirname "$0")" && pwd)/summaries"
OUTPUT="$SUMMARIES_DIR/index.html"

# Build the book entries by parsing each summary HTML
entries=""
count=0
for f in "$SUMMARIES_DIR"/*_summary.html; do
  [ -f "$f" ] || continue
  count=$((count + 1))
  filename="$(basename "$f")"
  title="$(grep -m1 '<h1>' "$f" | sed 's/<[^>]*>//g' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')"
  author="$(grep -m1 'class="author"' "$f" | sed 's/<[^>]*>//g' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//' || true)"
  subtitle="$(grep -m1 'class="subtitle"' "$f" | sed 's/<[^>]*>//g' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//' || true)"

  # Check for cover image
  cover_stem="${filename%_summary.html}"
  cover_file="$SUMMARIES_DIR/covers/${cover_stem}.jpg"

  # Build the card HTML
  entry="    <a href=\"${filename}\" class=\"book-card\">"
  if [ -f "$cover_file" ]; then
    entry="$entry
      <img src=\"covers/${cover_stem}.jpg\" alt=\"\" class=\"book-cover\" loading=\"lazy\">"
  fi
  entry="$entry
      <div class=\"book-info\">
        <span class=\"book-title\">${title}</span>"
  if [ -n "$subtitle" ]; then
    entry="$entry
        <span class=\"book-subtitle\">${subtitle}</span>"
  fi
  entry="$entry
        <span class=\"book-author\">${author}</span>
      </div>"
  entry="$entry
    </a>"
  entries="$entries
$entry"
done

cat > "$OUTPUT" << HTMLEOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Book Summaries</title>
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
    .page-subtitle {
      font-size: 1.05em;
      color: #777;
      font-style: italic;
      margin-bottom: 36px;
    }
    .book-list {
      display: flex;
      flex-direction: column;
      gap: 0;
    }
    .book-card {
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 18px;
      text-decoration: none;
      color: inherit;
      padding: 20px 18px;
      border-bottom: 1px solid #ddd;
      transition: background 0.15s;
    }
    .book-cover {
      width: 60px;
      min-width: 60px;
      border-radius: 3px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.15);
    }
    .book-info {
      flex: 1;
    }
    .book-card:first-child {
      border-top: 1px solid #ddd;
    }
    .book-card:hover {
      background: #f0ece4;
    }
    .book-title {
      display: block;
      font-size: 1.15em;
      font-weight: bold;
      color: #1a1a1a;
      margin-bottom: 2px;
    }
    .book-subtitle {
      display: block;
      font-size: 0.95em;
      font-style: italic;
      color: #555;
      margin-bottom: 4px;
    }
    .book-author {
      display: block;
      font-size: 0.9em;
      color: #888;
    }
    .count {
      font-size: 0.9em;
      color: #999;
      margin-top: 32px;
    }
  </style>
</head>
<body>

<h1>Book Summaries</h1>
<p class="page-subtitle">Chapter-level summaries with counterpoints and comprehension quizzes</p>

<div class="book-list">
${entries}
</div>

<p class="count">${count} books summarized</p>

</body>
</html>
HTMLEOF

echo "Generated $OUTPUT with $count book(s)."
