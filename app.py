import os
import socket
import zipfile
import io
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file
from downloader.audio_downloader import AudioDownloader
from database import init_db, get_db, is_duplicate
from config import DOWNLOAD_PATH

app = Flask(__name__)
progress = {"value":0}

# Ensure database is initialized at startup
init_db()

def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    url = request.form.get("url")
    playlists = request.form.get("playlists") == "on"
    max_songs = request.form.get("max_songs")
    print("Received download request:", url, "Playlists:", playlists, "Max songs:", max_songs)
    # Check for duplicates
    if is_duplicate(url):
        return jsonify({"status":"duplicate", "message":"This URL has already been downloaded"}), 400

    def cb(p):
        progress["value"] = p

    d = AudioDownloader(progress_callback=cb, playlists=playlists, max_songs=int(max_songs) if max_songs else 100)
    print("Downloading...", playlists, url)
    playlist_name, results = d.download(url)

    con = get_db()
    cur = con.cursor()
    for title, filename in results:
        # Use INSERT OR IGNORE to avoid UNIQUE constraint errors when the same
        # playlist URL is associated with multiple files.
        cur.execute("INSERT OR IGNORE INTO downloads(title,filename,url,folder, zip_file) VALUES(?,?,?,?,?)",(title,filename,url,playlist_name, d.zip_file_path))
    con.commit()
    con.close()

    return jsonify({"status":"done", "playlist": playlist_name})

@app.route("/progress")
def get_progress():
    return jsonify(progress)

@app.route("/downloads")
def downloads():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM downloads")
    rows = cur.fetchall()
    con.close()
    return render_template("downloads.html", rows=rows)

@app.route("/file/<path:filename>")
def file(filename):
    import os.path
    from urllib.parse import unquote

    # Decode URL-encoded characters
    filename = unquote(filename)

    # Prevent directory traversal attacks
    safe_path = os.path.normpath(filename)
    if safe_path.startswith("..") or os.path.isabs(safe_path):
        return "Forbidden", 403

    full_path = os.path.abspath(os.path.join(DOWNLOAD_PATH, safe_path))
    
    # Verify the path is still within DOWNLOAD_PATH
    if not full_path.startswith(os.path.abspath(DOWNLOAD_PATH)):
        return "Forbidden", 403
    
    if not os.path.exists(full_path):
        return "Not found", 404

    return send_file(full_path, as_attachment=True)

@app.route("/download-playlist/<folder_name>")
def download_playlist(folder_name):
    from urllib.parse import unquote
    
    # Decode folder name
    folder_name = unquote(folder_name)
    
    # Prevent directory traversal
    if ".." in folder_name or folder_name.startswith("/"):
        return "Forbidden", 403
    
    playlist_path = os.path.abspath(os.path.join(DOWNLOAD_PATH, folder_name))
    
    # Verify path is within DOWNLOAD_PATH
    if not playlist_path.startswith(os.path.abspath(DOWNLOAD_PATH)):
        return "Forbidden", 403
    
    if not os.path.isdir(playlist_path):
        return "Not found", 404
    
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT zip_file FROM downloads WHERE folder=?", (folder_name,))
    results = cur.fetchone()
    
    if not results:
        return "No files found for this playlist", 404
    
    if results[0]:
        zip_path = results[0]
        if os.path.exists(zip_path):
            print(f"Serving existing ZIP file for playlist: {folder_name}")
            return send_file(zip_path, mimetype='application/zip', as_attachment=True, download_name=f"{folder_name}.zip")

    # Create ZIP in memory
    zip_buffer = AudioDownloader.get_zip_file_path(folder_name)
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        print(f"Creating ZIP file for playlist: {folder_name}")
        for file in os.listdir(playlist_path):
            print(f"Adding file to ZIP: {file}")
            file_path = os.path.join(playlist_path, file)
            if os.path.isfile(file_path) and file.lower().endswith('.mp3'):
                # Include folder name in the ZIP archive path
                arcname = os.path.join(folder_name, file)
                zip_file.write(file_path, arcname=arcname)
    
    con.execute("UPDATE downloads SET zip_file=? WHERE folder=?", (zip_buffer, folder_name))
    con.commit()
    con.close()
    #zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name=f"{folder_name}.zip")


if __name__ == "__main__":
    init_db()
    local_ip = get_local_ip()
    print(f"\n{'='*50}")
    print(f"Server started successfully!")
    print(f"Local IP: {local_ip}")
    print(f"Access at: http://{local_ip}:5000")
    print(f"{'='*50}\n")
    app.run(host="0.0.0.0", debug=True)
