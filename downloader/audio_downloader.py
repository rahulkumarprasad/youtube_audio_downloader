import os
import threading
import concurrent.futures
from yt_dlp import YoutubeDL
from config import DOWNLOAD_PATH, AUDIO_FORMAT, QUALITY
MAX_CONCURRENT_DOWNLOADS = 4
import zipfile


class AudioDownloader:
    def __init__(self, progress_callback=None, playlists=False, max_songs = 100):
        self.progress_callback = progress_callback
        self.playlists = playlists
        self.max_songs = max_songs
        self._lock = threading.Lock()
        os.makedirs(DOWNLOAD_PATH, exist_ok=True)
        print(f"[AudioDownloader] Initialized with playlists={playlists}")
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

    def prepare_zip_file_at_first(self, folder_name, file_path):
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

        # First pass: get info to determine if playlist and get playlist name
        try:
            print("[AudioDownloader.download] Extracting info from URL...")
            with YoutubeDL({"quiet": True, "no_warnings": True,"socket_timeout": 10,
                "skip_download": True,
                "extract_flat": "in_playlist",
            }) as ydl:
                info = ydl.extract_info(url, download=False)
                is_playlist = 'entries' in info
                playlist_name = None

                if is_playlist:
                    original_title = info.get("title", "Playlist")
                    print(f"[AudioDownloader.download] Original playlist title: {original_title}")
                    # Create short meaningful name (first 20 chars, alphanumeric + dash only)
                    playlist_name = original_title[:20]  # Take first 20 characters
                    playlist_name = "".join(c for c in playlist_name if c.isalnum() or c == '-').strip()  # Keep only alphanumeric and dash
                    # If too short, use default
                    if len(playlist_name) < 3:
                        playlist_name = "Playlist"
                    print(f"[AudioDownloader.download] Sanitized playlist name: {playlist_name}")
                else:
                    print("[AudioDownloader.download] Detected SINGLE VIDEO")
                    playlist_name = "downloads"
        except Exception as e:
            print(f"[AudioDownloader.download] WARNING: Error getting playlist info - {str(e)}")
            is_playlist = False
            playlist_name = "downloads"

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
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": AUDIO_FORMAT,
                "preferredquality": QUALITY,
            }],
        }
        print(f"[AudioDownloader.download] YDL options configured")

        # helper to download a single url into out_dir
        def _download_single(video_url, out_dir):
            print(f"[_download_single] Starting download for: {video_url}")
            single_opts = dict(ydl_opts)
            single_opts.update({"outtmpl": f"{out_dir}/%(title)s.%(ext)s", "quiet": True, "no_warnings": True})
            try:
                with YoutubeDL(single_opts) as ydl_single:
                    print(f"[_download_single] Extracting info...")
                    info_single = ydl_single.extract_info(video_url, download=True)
                    t = info_single.get("title", "Unknown")
                    fname = ydl_single.prepare_filename(info_single).rsplit(".", 1)[0] + f".{AUDIO_FORMAT}"
                    print(f"[_download_single] ✓ Downloaded: {t}")
                    self.prepare_zip_file_at_first(playlist_name, fname)
                    return t, os.path.basename(fname)
            except Exception as e:
                print(f"[_download_single] ✗ Skipping video - {str(e)}")
                return None, None

        # If playlist, download items in parallel
        if is_playlist and self.playlists:
            print("[AudioDownloader.download] Processing as PLAYLIST with parallel downloads")
            try:
                entries = info.get('entries') or []
                urls = []
                for i, e in enumerate(entries):
                    if not e:
                        print(f"[AudioDownloader.download] Video {i}: Skipped (unavailable)")
                        continue
                    u = e.get('webpage_url') or ("https://www.youtube.com/watch?v=" + str(e.get('id')))
                    urls.append(u)
                    print(f"[AudioDownloader.download] Video {i}: Added to queue - {e.get('title', 'Unknown')[0:50]}")
                    if self.max_songs <= len(urls):
                        print(f"[AudioDownloader.download] Reached max_songs limit: {self.max_songs}")
                        break

                total = len(urls)
                print(f"[AudioDownloader.download] Total videos to download: {total}")
                results = []
                completed = 0
                max_workers = min(MAX_CONCURRENT_DOWNLOADS, total) if total > 0 else 1
                print(f"[AudioDownloader.download] Using {max_workers} parallel workers")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                    futures = [ex.submit(_download_single, u, playlist_path) for u in urls]
                    for fut in concurrent.futures.as_completed(futures):
                        try:
                            title, fname = fut.result()
                            if title and fname:  # Skip if download failed
                                rel = os.path.join(playlist_name, fname)
                                results.append((title, rel))
                                print(f"[AudioDownloader.download] Added to results: {title}")
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
                self.zip_files_obj.close()
                return playlist_name, results
            except Exception as e:
                if self.zip_files_obj is not None:
                    self.zip_files_obj.close()
                    print(f"[AudioDownloader] ZIP file closed due to error at: {self.zip_file_path}")
                print(f"[AudioDownloader.download] ERROR in playlist download: {str(e)}")
                return playlist_name, []

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
                    return playlist_name, [(title, relative_path)]
            except Exception as e:
                print(f"[AudioDownloader.download] ERROR downloading video: {str(e)}")
                return playlist_name, []