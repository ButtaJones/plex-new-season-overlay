import os
import json
import re
import tempfile
from datetime import datetime, timedelta
from plexapi.server import PlexServer
from PIL import Image
import io
import requests

# === CONFIGURATION ===
PLEX_URL = 'http://localhost:32400'
PLEX_TOKEN = 'YOUR_PLEX_TOKEN_HERE'
OVERLAY_PATH = 'new_season.png'  # your overlay file
LOG_FILE = 'overlaid_log.json'
PREVIEW_MODE = True
CLEANUP_MODE = False
PREVIEW_FOLDER = 'preview_posters'

# === SETUP ===
plex = PlexServer(PLEX_URL, PLEX_TOKEN)
now = datetime.now()
cutoff = now - timedelta(days=20)

if not os.path.exists(PREVIEW_FOLDER):
    os.makedirs(PREVIEW_FOLDER)

# Check if overlay file exists
if not os.path.exists(OVERLAY_PATH):
    print(f"Error: Overlay file '{OVERLAY_PATH}' not found!")
    exit(1)

# Load existing log data with error handling
if os.path.exists(LOG_FILE):
    try:
        with open(LOG_FILE, 'r') as f:
            overlaid_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not read log file '{LOG_FILE}': {e}")
        overlaid_data = {}
else:
    overlaid_data = {}

def sanitize_filename(filename):
    """Remove or replace characters that are invalid in filenames"""
    # Remove/replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = filename.strip()
    return filename

def save_log():
    try:
        with open(LOG_FILE, 'w') as f:
            json.dump(overlaid_data, f, indent=2)
        print(f"Log saved to: {LOG_FILE}")
    except IOError as e:
        print(f"Error saving log file: {e}")

def apply_overlay(base_img, overlay_img):
    base_img = base_img.convert("RGBA")
    overlay_img = overlay_img.convert("RGBA")
    width, height = base_img.size
    new_width = int(width * 0.85)
    new_height = int(overlay_img.height * (new_width / overlay_img.width))
    resized_overlay = overlay_img.resize((new_width, new_height), Image.LANCZOS)
    x = int((width - new_width) / 2)
    y = height - new_height
    base_img.paste(resized_overlay, (x, y), resized_overlay)
    return base_img

def reset_poster(item):
    """Reset poster to default/original by removing custom poster"""
    print(f"Resetting poster for: {item.title}")
    
    try:
        # First, try to get the original poster from available posters
        posters = item.posters()
        if posters:
            # Look for the original/default poster (usually the first one or one marked as selected)
            original_poster = None
            for poster in posters:
                # The original poster usually has a different URL pattern
                if 'metadata' in poster.key and 'thumb' in poster.key:
                    original_poster = poster
                    break
            
            if not original_poster:
                # If we can't find the original, just use the first available poster
                original_poster = posters[0]
            
            # Set the poster to the original one
            item.setPoster(original_poster)
            print(f"  ✅ Reverted to original poster")
            return True
            
    except Exception as e:
        print(f"  ❌ Failed to revert poster: {e}")
    
    # Fallback method: try to remove the custom poster entirely
    try:
        # Unlock the poster first
        item.edit(**{'thumb.locked': 0})
        # Try to remove custom poster by setting it to None
        item.edit(**{'thumb': None})
        item.refresh()
        print(f"  ✅ Removed custom poster")
        return True
    except Exception as e:
        print(f"  ❌ Failed to remove custom poster: {e}")
    
    print(f"  ⚠️  Could not reset poster for: {item.title}")
    return False

def cleanup_posters():
    print("🧹 Cleanup Mode Enabled")
    cleaned_count = 0
    
    for rating_key in list(overlaid_data.keys()):
        entry = overlaid_data[rating_key]
        
        try:
            # Get the show and check if the season is still "new"
            show = plex.fetchItem(f"/library/metadata/{rating_key}")
            
            # Get the latest season again
            seasons = show.seasons()
            if len(seasons) < 2:
                print(f"Show no longer has 2+ seasons, removing overlay: {show.title}")
                reset_poster(show)
                # Also reset the latest season poster if it exists
                if seasons:
                    latest_season = max([s for s in seasons if s.index is not None], key=lambda s: s.index)
                    reset_poster(latest_season)
                del overlaid_data[rating_key]
                cleaned_count += 1
                continue
            
            # Check if the latest season is still "new" (aired within last 20 days)
            valid_seasons = [s for s in seasons if s.index is not None]
            latest_season = max(valid_seasons, key=lambda s: s.index)
            episodes = latest_season.episodes()
            episode1 = next((ep for ep in episodes if ep.index == 1), None)
            
            if not episode1 or episode1.originallyAvailableAt is None:
                print(f"Cannot determine season age, removing overlay: {show.title}")
                reset_poster(show)
                reset_poster(latest_season)
                del overlaid_data[rating_key]
                cleaned_count += 1
                continue
            
            # If the season is now older than 20 days, remove overlay
            if episode1.originallyAvailableAt < cutoff:
                print(f"Season no longer new, removing overlay: {show.title}")
                reset_poster(show)
                reset_poster(latest_season)
                del overlaid_data[rating_key]
                cleaned_count += 1
            else:
                print(f"Season still new, keeping overlay: {show.title}")
                
        except Exception as e:
            print(f"Failed to process cleanup for {rating_key}: {e}")
            # Remove from log if we can't access the show anymore
            print(f"Removing inaccessible entry from log: {entry.get('title', 'Unknown')}")
            del overlaid_data[rating_key]
            cleaned_count += 1
    
    save_log()
    print(f"🧹 Cleanup complete! Removed {cleaned_count} overlays.")
    return

# === START ===
if CLEANUP_MODE:
    cleanup_posters()
    exit()

processed_count = 0
for section in plex.library.sections():
    if section.type != 'show':
        continue
    
    for show in section.all():
        try:
            # Skip if already processed in live mode
            if str(show.ratingKey) in overlaid_data:
                entry = overlaid_data[str(show.ratingKey)]
                # If we're in live mode and it was only previewed, allow processing
                if not PREVIEW_MODE and entry.get("preview_only", False):
                    print(f"Converting preview to live: {show.title}")
                else:
                    print(f"Skipping already processed: {show.title}")
                    continue
            
            # Must have at least 2 seasons
            seasons = show.seasons()
            if len(seasons) < 2:
                continue
            
            # Get latest season - filter out None indexes and sort
            valid_seasons = [s for s in seasons if s.index is not None]
            if not valid_seasons:
                continue
                
            latest_season = max(valid_seasons, key=lambda s: s.index)
            episodes = latest_season.episodes()
            episode1 = next((ep for ep in episodes if ep.index == 1), None)
            
            if not episode1:
                continue
            
            # Check if this is actually a NEW season (aired recently)
            if episode1.originallyAvailableAt is None:
                continue
                
            # Only overlay if the season originally aired within the last 20 days
            if episode1.originallyAvailableAt < cutoff:
                continue
            
            print(f"Processing: {show.title}")
            
            # Download original show poster
            poster_url = f"{PLEX_URL}{show.thumb}?X-Plex-Token={PLEX_TOKEN}"
            response = requests.get(poster_url)
            if response.status_code != 200:
                print(f"Failed to download show poster for {show.title}")
                continue
            
            original_poster = Image.open(io.BytesIO(response.content))
            overlay_img = Image.open(OVERLAY_PATH)
            result = apply_overlay(original_poster, overlay_img)
            
            # Also get the season poster if it exists
            season_poster_result = None
            if latest_season.thumb:
                season_poster_url = f"{PLEX_URL}{latest_season.thumb}?X-Plex-Token={PLEX_TOKEN}"
                season_response = requests.get(season_poster_url)
                if season_response.status_code == 200:
                    season_original_poster = Image.open(io.BytesIO(season_response.content))
                    season_poster_result = apply_overlay(season_original_poster, overlay_img)
            
            if PREVIEW_MODE:
                # Sanitize filename to avoid filesystem issues
                safe_title = sanitize_filename(show.title)
                preview_path = os.path.join(PREVIEW_FOLDER, f"{safe_title}_show.png")
                result.save(preview_path)
                print(f"Show preview saved: {preview_path}")
                
                # Save season preview too if we have it
                if season_poster_result:
                    season_preview_path = os.path.join(PREVIEW_FOLDER, f"{safe_title}_season.png")
                    season_poster_result.save(season_preview_path)
                    print(f"Season preview saved: {season_preview_path}")
                
                # Track in preview mode too
                overlaid_data[str(show.ratingKey)] = {
                    "title": show.title,
                    "timestamp": now.isoformat(),
                    "preview_only": True
                }
                save_log()  # Save immediately after adding data
            else:
                # Upload show poster
                safe_title = sanitize_filename(show.title)
                temp_path = os.path.join(PREVIEW_FOLDER, f"temp_{safe_title}_show.png")
                result.save(temp_path)
                
                try:
                    show.uploadPoster(filepath=temp_path)
                    print(f"Show poster uploaded for: {show.title}")
                    
                    # Upload season poster if we have it
                    if season_poster_result:
                        season_temp_path = os.path.join(PREVIEW_FOLDER, f"temp_{safe_title}_season.png")
                        season_poster_result.save(season_temp_path)
                        try:
                            latest_season.uploadPoster(filepath=season_temp_path)
                            print(f"Season poster uploaded for: {show.title} - Season {latest_season.index}")
                        finally:
                            if os.path.exists(season_temp_path):
                                os.remove(season_temp_path)
                    
                    overlaid_data[str(show.ratingKey)] = {
                        "title": show.title,
                        "timestamp": now.isoformat(),
                        "preview_only": False
                    }
                    save_log()  # Save immediately after adding data
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            
            processed_count += 1
            
        except Exception as e:
            print(f"Failed to process '{show.title}': {e}")
            import traceback
            traceback.print_exc()  # This will help debug any remaining issues

print(f"\n✅ Processing complete! Processed {processed_count} shows.")
if PREVIEW_MODE:
    print(f"Preview images saved to: {PREVIEW_FOLDER}")
    print(f"Log file: {LOG_FILE}")
else:
    print("Posters uploaded to Plex server.")
