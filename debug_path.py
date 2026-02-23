import os
from urllib.parse import unquote

# Test the URL decoding
encoded_url = "Hindi%20Bhakti%20Songs%20%20Devotional%20Songs/Jubin%20Nautiyal%EF%BC%9A%20Shri%20Krishna%20Govind%20Hare%20Murari%20%EF%BD%9C%20Raaj%20Aashoo,%20Murali%20A%20%EF%BD%9C%20Bhushan%20Kumar%20%EF%BD%9C%20T-Series.mp3"

decoded = unquote(encoded_url)
print("Decoded URL:")
print(repr(decoded))
print()

# Check which files exist
DOWNLOAD_PATH = "downloads"
safe_path = os.path.normpath(decoded)
full_path = os.path.join(DOWNLOAD_PATH, safe_path)

print(f"Safe path: {repr(safe_path)}")
print(f"Full path: {repr(full_path)}")
print(f"File exists: {os.path.exists(full_path)}")
print()

# List files in the folder
playlist_folder = os.path.join(DOWNLOAD_PATH, "Hindi Bhakti Songs  Devotional Songs")
if os.path.exists(playlist_folder):
    files = os.listdir(playlist_folder)
    print(f"Files in playlist folder (first 5):")
    for f in files[:5]:
        print(f"  {repr(f)}")
    print()
    
    # Check specifically for the target file
    for f in files:
        if "Shri Krishna" in f and "Govind" in f:
            print(f"Found matching file: {repr(f)}")
            test_path = os.path.join(playlist_folder, f)
            print(f"Full test path: {repr(test_path)}")
            print(f"Test file exists: {os.path.exists(test_path)}")
