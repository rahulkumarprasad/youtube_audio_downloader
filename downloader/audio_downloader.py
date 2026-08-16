import os
import threading
import concurrent.futures
from yt_dlp import YoutubeDL
from config import DOWNLOAD_PATH, AUDIO_FORMAT, QUALITY
MAX_CONCURRENT_DOWNLOADS = 4
import zipfile


class AudioDownloader:
    def __init__(self, progress_callback=None, playlists=False, max_songs = 100, use_cookies=True, browser="chrome", cookie_file=None):
        self.progress_callback = progress_callback
        self.playlists = playlists
        self.max_songs = max_songs
        self.use_cookies = use_cookies
        self.browser = browser.lower() if browser else "chrome"
        self.cookie_file = cookie_file
        self._lock = threading.Lock()
        self._zip_lock = threading.Lock()
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        print(f"[AudioDownloader] Initialized with playlists={playlists}, use_cookies={use_cookies}, browser={self.browser}")
        self.zip_files_obj=None
        self.zip_file_path=None

    def set_zip_file_path(self, folder_name):
        self.zip_file_path = self.get_zip_file_path(folder_name)
        print(f"[AudioDownloader] ZIP file path set to: {self.zip_file_path}")

    @staticmethod
    def get_zip_file_path(folder_name):
        zip_folder = os.path.join(DOWNLOAD_PATH, "prepared_zip_files")
        os.makedirs(zip_folder, exist_ok=True)
        zip_path = os.path.join(zip_folder, folder_name + ".zip")
        return zip_path

    def close_zip_file(self):
        if self.zip_files_obj is not None:
            try:
                self.zip_files_obj.close()
            except Exception:
                pass
            finally:
                self.zip_files_obj = None

    def prepare_zip_file_at_first(self, folder_name, file_path):
        with self._zip_lock:
            if self.zip_files_obj is None:
                zip_path = self.get_zip_file_path(folder_name)
                self.zip_files_obj = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)
                print(f"[AudioDownloader] Created ZIP file at: {zip_path}")

            self.zip_files_obj.write(file_path, os.path.relpath(file_path, DOWNLOAD_PATH))
            print(f"[AudioDownloader] Added to ZIP: {file_path}")

    def _hook(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total and self.progress_callback:
                progress = int(downloaded/total*100)
                self.progress_callback(progress)
                print(f"[Download Progress] {progress}%")

    def download(self, url):
        print(f"\n[AudioDownloader.download] Starting download for URL: {url}")
        print(f"[AudioDownloader.download] Playlists mode: {self.playlists}")

        info = None
        is_playlist = False
        playlist_name = "downloads"

        # First pass: get info to determine if playlist and get playlist name
        try:
            print("[AudioDownloader.download] Extracting info from URL...")
            with YoutubeDL({"quiet": True, "no_warnings": True, "socket_timeout": 10,
                "skip_download": True,
                "extract_flat": "in_playlist",
            }) as ydl:
                info = ydl.extract_info(url, download=False)
                if isinstance(info, dict):
                    entries = info.get("entries")
                    is_playlist = isinstance(entries, list) and len(entries) > 0
                    if is_playlist:
                        original_title = info.get("title", "Playlist")
                        print(f"[AudioDownloader.download] Original playlist title: {original_title}")
                        playlist_name = original_title[:20]
                        playlist_name = "".join(c for c in playlist_name if c.isalnum() or c == '-').strip()
                        if len(playlist_name) < 3:
                            playlist_name = "Playlist"
                        print(f"[AudioDownloader.download] Sanitized playlist name: {playlist_name}")
                    else:
                        print("[AudioDownloader.download] Detected SINGLE VIDEO")
                else:
                    print("[AudioDownloader.download] Detected SINGLE VIDEO")
        except Exception as e:
            print(f"[AudioDownloader.download] WARNING: Error getting playlist info - {str(e)}")
            is_playlist = False
            playlist_name = "downloads"

        if info is None:
            print("[AudioDownloader.download] No metadata returned by yt-dlp; trying direct download fallback for the URL.")
            is_playlist = False
            playlist_name = "downloads"
            try:
                with YoutubeDL(ydl_opts) as ydl_direct:
                    direct_info = ydl_direct.extract_info(url, download=True)
                    if isinstance(direct_info, dict):
                        title = direct_info.get("title", "Unknown")
                        filename = ydl_direct.prepare_filename(direct_info).rsplit(".", 1)[0] + f".{AUDIO_FORMAT}"
                        relative_path = os.path.basename(filename)
                        print(f"[AudioDownloader.download] Direct fallback succeeded: {title}")
                        return playlist_name, [(title, relative_path)], []
            except Exception as e:
                print(f"[AudioDownloader.download] Direct fallback failed: {str(e)}")
                return playlist_name, [], [{"url": url, "reason": str(e)}]

        playlist_path = os.path.join(DOWNLOAD_PATH, playlist_name) if is_playlist else DOWNLOAD_PATH
        if is_playlist:
            os.makedirs(playlist_path, exist_ok=True)
            print(f"[AudioDownloader.download] Created folder: {playlist_path}")

        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": not self.playlists,
            "outtmpl": f"{playlist_path}/%(title)s.%(ext)s",
            "progress_hooks": [self._hook],
            'restrictfilenames': True,
            "ignoreerrors": True,
            "retries": 2,
            "socket_timeout": 15,
            "no_warnings": True,
            "quiet": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": AUDIO_FORMAT,
                "preferredquality": QUALITY,
            }],
        }

        if self.use_cookies:
            if self.cookie_file and os.path.exists(self.cookie_file):
                ydl_opts["cookiefile"] = self.cookie_file
                print(f"[AudioDownloader.download] Using cookie file: {self.cookie_file}")
            elif self.browser in ("chrome", "firefox"):
                ydl_opts["cookiesfrombrowser"] = (self.browser,)
                print(f"[AudioDownloader.download] Using browser cookies from: {self.browser}")
            else:
                print("[AudioDownloader.download] Cookie option selected, but no valid cookie source was provided.")

        print(f"[AudioDownloader.download] YDL options configured")

        # helper to download a single url into out_dir
        def _download_single(video_url, out_dir):
            print(f"[_download_single] Starting download for: {video_url}")
            single_opts = dict(ydl_opts)
            single_opts.update({
                "outtmpl": f"{out_dir}/%(title)s.%(ext)s",
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": True,
                "extract_flat": False,
            })
            try:
                with YoutubeDL(single_opts) as ydl_single:
                    print(f"[_download_single] Extracting info...")
                    info_single = ydl_single.extract_info(video_url, download=True)
                    if not isinstance(info_single, dict):
                        print(f"[_download_single] ✗ Skipping video - no metadata returned")
                        return None, None, "No metadata returned"

                    t = info_single.get("title", "Unknown")
                    fname = ydl_single.prepare_filename(info_single).rsplit(".", 1)[0] + f".{AUDIO_FORMAT}"
                    if not os.path.exists(fname):
                        print(f"[_download_single] ✗ Skipping video - file not created: {fname}")
                        return None, None, "File was not created"

                    print(f"[_download_single] ✓ Downloaded: {t}")
                    self.prepare_zip_file_at_first(playlist_name, fname)
                    return t, os.path.basename(fname), None
            except Exception as e:
                message = str(e)
                print(f"[_download_single] ✗ Skipping video - {message}")
                return None, None, message

        # If playlist, download items in parallel
        if is_playlist and self.playlists:
            print("[AudioDownloader.download] Processing as PLAYLIST with parallel downloads")
            try:
                entries = info.get('entries') if isinstance(info, dict) else []
                if not isinstance(entries, list):
                    entries = []

                urls = []
                for i, e in enumerate(entries):
                    if not isinstance(e, dict):
                        print(f"[AudioDownloader.download] Video {i}: Skipped (invalid entry)")
                        continue
                    video_id = e.get('id')
                    u = e.get('webpage_url') or e.get('url') or (
                        "https://www.youtube.com/watch?v=" + str(video_id) if video_id else None
                    )
                    if not u:
                        print(f"[AudioDownloader.download] Video {i}: Skipped (missing URL)")
                        continue
                    urls.append(u)
                    title = e.get('title') or 'Unknown'
                    print(f"[AudioDownloader.download] Video {i}: Added to queue - {str(title)[:50]}")
                    if self.max_songs <= len(urls):
                        print(f"[AudioDownloader.download] Reached max_songs limit: {self.max_songs}")
                        break

                total = len(urls)
                if total == 0:
                    print("[AudioDownloader.download] No valid playlist entries were found.")
                    return playlist_name, []

                print(f"[AudioDownloader.download] Total videos to download: {total}")
                results = []
                skipped = []
                completed = 0
                max_workers = min(MAX_CONCURRENT_DOWNLOADS, total) if total > 0 else 1
                print(f"[AudioDownloader.download] Using {max_workers} parallel workers")

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                    futures = [ex.submit(_download_single, u, playlist_path) for u in urls]
                    for fut in concurrent.futures.as_completed(futures):
                        try:
                            title, fname, reason = fut.result()
                            if title and fname:
                                rel = os.path.join(playlist_name, fname)
                                results.append((title, rel))
                                print(f"[AudioDownloader.download] Added to results: {title}")
                            elif reason:
                                skipped.append({"url": fut.args[0] if hasattr(fut, 'args') else None, "reason": reason})
                                print(f"[AudioDownloader.download] Skipped due to: {reason}")
                        except Exception as e:
                            print(f"[AudioDownloader.download] Error in future result: {str(e)}")
                        with self._lock:
                            completed += 1
                            if self.progress_callback and total:
                                progress = int(completed/total*100)
                                self.progress_callback(progress)
                                print(f"[AudioDownloader.download] Progress: {completed}/{total} ({progress}%)")

                print(f"[AudioDownloader.download] ✓ Playlist download complete. Total files: {len(results)}")
                self.set_zip_file_path(playlist_name)
                self.close_zip_file()
                return playlist_name, results, skipped
            except Exception as e:
                self.close_zip_file()
                print(f"[AudioDownloader] ZIP file closed due to error at: {self.zip_file_path}")
                print(f"[AudioDownloader.download] ERROR in playlist download: {str(e)}")
                return playlist_name, [], []

        # Single video (or playlist mode disabled) - fallback to single download
        else:
            print("[AudioDownloader.download] Processing as SINGLE VIDEO")
            try:
                with YoutubeDL(ydl_opts) as ydl:
                    print(f"[AudioDownloader.download] Extracting video info...")
                    info = ydl.extract_info(url, download=True)
                    title = info.get("title", "Unknown")
                    filename = ydl.prepare_filename(info).rsplit(".",1)[0] + f".{AUDIO_FORMAT}"
                    relative_path = os.path.basename(filename)
                    print(f"[AudioDownloader.download] ✓ Downloaded: {title}")
                    print(f"[AudioDownloader.download] Returning: playlist_name={playlist_name}, file={relative_path}")
                    return playlist_name, [(title, relative_path)], []
            except Exception as e:
                print(f"[AudioDownloader.download] ERROR downloading video: {str(e)}")
                return playlist_name, [], [{"url": url, "reason": str(e)}]