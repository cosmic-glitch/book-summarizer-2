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
      <span class=\"book-title\">${title}</span>"
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
  <title>Book Summary Pro</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: Georgia, 'Times New Roman', serif;
      line-height: 1.7;
      color: #222;
      background: #fafafa;
    }
    .app-nav {
      background: #2c2c2c;
      padding: 14px 24px;
    }
    .app-nav .app-name {
      display: block;
      font-size: 1.05em;
      font-weight: bold;
      color: #e8e0d0;
      text-decoration: none;
      letter-spacing: 0.3px;
    }
    .app-nav .app-name:hover {
      color: #d4a843;
    }
    .content {
      max-width: 960px;
      margin: 0 auto;
      padding: 24px 24px 40px;
    }
    .book-list {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 28px 20px;
    }
    @media (max-width: 800px) {
      .book-list { grid-template-columns: repeat(3, 1fr); }
    }
    @media (max-width: 540px) {
      .book-list { grid-template-columns: repeat(2, 1fr); }
    }
    .book-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-decoration: none;
      color: inherit;
      padding: 16px 8px;
      border-radius: 6px;
      transition: background 0.15s;
    }
    .book-card:hover {
      background: #f0ece4;
    }
    .book-cover {
      height: 220px;
      width: auto;
      max-width: 100%;
      object-fit: contain;
      border-radius: 3px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.18);
      margin-bottom: 12px;
    }
    .book-title {
      display: block;
      font-size: 0.92em;
      font-weight: bold;
      color: #1a1a1a;
      text-align: center;
      line-height: 1.3;
    }
    .count {
      font-size: 0.9em;
      color: #999;
      margin-top: 32px;
      text-align: center;
    }
  </style>
</head>
<body>

<nav class="app-nav">
  <span class="app-name">Book Summary Pro</span>
</nav>


<div class="content">
  <div class="book-list">
${entries}
  </div>

  <p class="count">${count} books summarized</p>
</div>

</body>
</html>
HTMLEOF

echo "Generated $OUTPUT with $count book(s)."
