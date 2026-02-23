YouTube Audio Downloader
=======================

What this project is
- A small Flask web app to download audio from YouTube (single videos or playlists) using yt-dlp.
- Stores metadata in a local SQLite database and serves downloaded files from the downloads/ folder.
- Provides a web UI (/, /downloads) and supports packaging playlists as ZIPs.

Key files
- app.py — Flask server and routes
- downloader/audio_downloader.py — download logic (yt-dlp hooks, ZIP creation)
- database.py — SQLite helpers (init_db, is_duplicate)
- config.py — paths and settings
- templates/*.html, static/progress.js — frontend
- run.sh (UNIX) and run.bat (Windows) — convenience start scripts
- requirements.txt — Python dependencies

Prerequisites
- Python 3.8+
- ffmpeg (required by yt-dlp to extract audio)
- Recommended: virtual environment

Install
- Windows (PowerShell/CMD):
  python -m venv .\.venv
  .\.venv\Scripts\activate
  pip install -r requirements.txt

- macOS / Linux:
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

Database migration (if needed)
- If the DB lacks the zip_file column, run:
  python update_database_table.py
  or modify init_db in database.py to include: zip_file TEXT DEFAULT NULL

How to start (scripts)
- Development (Flask built-in server):
  python app.py
  Visit: http://localhost:5000

- Production-like (recommended):
  Windows:
    run.bat
  macOS / Linux:
    ./run.sh
  Both scripts install deps (if needed) and launch waitress-serve on port 5000.

How to use
1. Open the web UI: http://localhost:5000
2. Paste a YouTube URL. Optionally enable "All playlists" and set "Maximum number of songs".
3. Click Download. Watch progress bar; finished files are at /downloads.

Useful endpoints
- /downloads — listing page
- /file/<path:filename> — download single file
- /download-playlist/<folder_name> — download playlist ZIP

Troubleshooting
- Ensure ffmpeg is installed and in PATH.
- If progress bar errors: check server logs; /start should always return JSON.
- DB errors about missing columns: run migration above.

License
- No license specified — treat as private project.