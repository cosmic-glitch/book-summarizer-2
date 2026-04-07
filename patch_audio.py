#!/usr/bin/env python3
"""
patch_audio.py — Inject sticky audio players into summary HTML files.

For each MP3 in summaries/audio/, finds the matching *_summary.html and
injects a sticky audio player bar with play/pause, ±30s skip, scrubber,
time display, and speed control. Idempotent: already-patched files are skipped.

Usage: python patch_audio.py
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent
AUDIO_DIR = REPO_ROOT / "summaries" / "audio"
SUMMARIES_DIR = REPO_ROOT / "summaries"
MARKER = "<!-- audio-player-injected -->"


def build_css():
    return """<style id="audio-player-style">
  .audio-bar {
    position: sticky;
    top: 0;
    z-index: 100;
    background: #2c2c2c;
    color: #e8e0d0;
    padding: 10px 24px;
    display: flex;
    align-items: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
  }
  .audio-controls {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    flex-wrap: wrap;
  }
  .audio-controls button {
    background: none;
    border: none;
    cursor: pointer;
    font-family: Georgia, serif;
    font-size: 0.9em;
    color: #e8e0d0;
    padding: 4px 8px;
    border-radius: 4px;
    transition: color 0.15s;
  }
  .audio-controls button:hover { color: #d4a843; }
  #audio-play-pause {
    color: #d4a843;
    font-size: 1.3em;
    min-width: 2em;
    text-align: center;
  }
  #audio-scrubber {
    flex: 1;
    min-width: 80px;
    accent-color: #d4a843;
    cursor: pointer;
  }
  #audio-time {
    font-size: 0.82em;
    white-space: nowrap;
    color: #b0a898;
    font-family: Georgia, serif;
  }
  #audio-speed {
    background: #3a3a3a;
    color: #e8e0d0;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 0.82em;
    cursor: pointer;
    font-family: Georgia, serif;
  }
</style>"""


def build_player_html(stem):
    return f"""{MARKER}
<div class="audio-bar" id="audio-bar">
  <audio id="book-audio" src="audio/{stem}.mp3" preload="metadata"></audio>
  <div class="audio-controls">
    <button id="audio-skip-back" title="Back 30 seconds">&#9198; 30s</button>
    <button id="audio-play-pause" title="Play">&#9654;</button>
    <button id="audio-skip-fwd" title="Forward 30 seconds">30s &#9197;</button>
    <input type="range" id="audio-scrubber" value="0" min="0" step="1">
    <span id="audio-time">0:00 / 0:00</span>
    <select id="audio-speed" title="Playback speed">
      <option value="0.75">0.75&times;</option>
      <option value="1" selected>1&times;</option>
      <option value="1.25">1.25&times;</option>
      <option value="1.5">1.5&times;</option>
      <option value="2">2&times;</option>
    </select>
  </div>
</div>"""


def build_js():
    return """<script id="audio-player-script">
(function() {
  var audio = document.getElementById('book-audio');
  var playBtn = document.getElementById('audio-play-pause');
  var scrubber = document.getElementById('audio-scrubber');
  var timeDisplay = document.getElementById('audio-time');
  var speedSel = document.getElementById('audio-speed');

  function fmtTime(s) {
    if (!isFinite(s) || isNaN(s)) return '0:00';
    var m = Math.floor(s / 60);
    var sec = Math.floor(s % 60);
    return m + ':' + (sec < 10 ? '0' : '') + sec;
  }

  audio.addEventListener('loadedmetadata', function() {
    scrubber.max = Math.floor(audio.duration);
    timeDisplay.textContent = '0:00 / ' + fmtTime(audio.duration);
  });

  audio.addEventListener('timeupdate', function() {
    if (!scrubber._seeking) {
      scrubber.value = Math.floor(audio.currentTime);
    }
    timeDisplay.textContent = fmtTime(audio.currentTime) + ' / ' + fmtTime(audio.duration);
  });

  audio.addEventListener('ended', function() {
    playBtn.textContent = '\u25b6';
  });

  playBtn.addEventListener('click', function() {
    if (audio.paused) {
      audio.play();
      playBtn.innerHTML = '&#9208;';
    } else {
      audio.pause();
      playBtn.innerHTML = '&#9654;';
    }
  });

  document.getElementById('audio-skip-back').addEventListener('click', function() {
    audio.currentTime = Math.max(0, audio.currentTime - 30);
  });

  document.getElementById('audio-skip-fwd').addEventListener('click', function() {
    audio.currentTime = Math.min(audio.duration || 0, audio.currentTime + 30);
  });

  scrubber.addEventListener('mousedown', function() { scrubber._seeking = true; });
  scrubber.addEventListener('touchstart', function() { scrubber._seeking = true; });
  scrubber.addEventListener('input', function() {
    timeDisplay.textContent = fmtTime(parseInt(scrubber.value)) + ' / ' + fmtTime(audio.duration);
  });
  scrubber.addEventListener('change', function() {
    audio.currentTime = parseInt(scrubber.value);
    scrubber._seeking = false;
  });

  speedSel.addEventListener('change', function() {
    audio.playbackRate = parseFloat(speedSel.value);
  });
})();
</script>"""


def patch_file(html_path, stem):
    html = html_path.read_text(encoding='utf-8')

    if MARKER in html:
        print(f"Skipped:  {html_path.name} (already patched)")
        return

    css = build_css()
    player = build_player_html(stem)
    js = build_js()

    if '</head>' not in html:
        print(f"Warning:  {html_path.name} — no </head> tag, skipping")
        return
    html = html.replace('</head>', css + '\n</head>', 1)

    if '</nav>' not in html:
        print(f"Warning:  {html_path.name} — no </nav> tag, skipping")
        return
    html = html.replace('</nav>', '</nav>\n' + player, 1)

    if '</body>' not in html:
        print(f"Warning:  {html_path.name} — no </body> tag, skipping")
        return
    html = html.replace('</body>', js + '\n</body>', 1)

    html_path.write_text(html, encoding='utf-8')
    print(f"Patched:  {html_path.name}")


def main():
    if not AUDIO_DIR.exists():
        print("No audio directory found at summaries/audio/")
        return

    mp3_files = sorted(AUDIO_DIR.glob("*.mp3"))
    if not mp3_files:
        print("No MP3 files found in summaries/audio/")
        return

    for mp3 in mp3_files:
        stem = mp3.stem
        html_path = SUMMARIES_DIR / f"{stem}_summary.html"
        if not html_path.exists():
            print(f"Warning:  No summary found for {stem}.mp3 (expected {html_path.name})")
            continue
        patch_file(html_path, stem)


if __name__ == '__main__':
    main()
