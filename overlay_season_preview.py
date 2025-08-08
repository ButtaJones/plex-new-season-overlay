import os
import json
import re
import time
import sys
import tempfile
from datetime import datetime, timedelta
from plexapi.server import PlexServer
from PIL import Image
import io
import requests

# === CONFIGURATION ===
PLEX_URL = 'http://192.168.1.23:32400'  # Your Plex server URL
PLEX_TOKEN = 'YOUR_PLEX_TOKEN_HERE'       # Your Plex token
OVERLAY_PATH = 'new_season.png'  # your overlay file
LOG_FILE = 'overlaid_log.json'
PREVIEW_MODE = False # Set to False to run revert or apply overlays live
PREVIEW_FOLDER = 'preview_posters'
RUN_SCHEDULE_HOURS = 24  # Hours to wait between runs. Set to 0 to run only once.

# === SETUP ===
now = datetime.now()
cutoff = now - timedelta(days=10)

if not os.path.exists(PREVIEW_FOLDER):
    os.makedirs(PREVIEW_FOLDER)

if not os.path.exists(OVERLAY_PATH):
    print(f"Error: Overlay file '{OVERLAY_PATH}' not found!")
    exit(1)

def load_log_data():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read log file '{LOG_FILE}': {e}")
            return {}
    else:
        return {}

def sanitize_filename(filename):
    """Remove or replace characters that are invalid in filenames"""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = filename.strip()
    return filename

def save_log(data_to_save):
    try:
        with open(LOG_FILE, 'w') as f:
            json.dump(data_to_save, f, indent=2)
        print(f"Log saved to: {LOG_FILE}")
    except IOError as e:
        print(f"Error saving log file: {e}")

def apply_overlay(base_img, overlay_img):
    base_img = base_img.convert("RGBA")
    overlay_img = overlay_img.convert("RGBA")
    width, height = base_img.size
    new_width = int(width * 0.75)
    new_height = int(overlay_img.height * (new_width / overlay_img.width))
    resized_overlay = overlay_img.resize((new_width, new_height), Image.LANCZOS)
    x = int((width - new_width) / 2)
    y = height - new_height
    base_img.paste(resized_overlay, (x, y), resized_overlay)
    return base_img

def reset_poster(item):
    """Fallback function to reset a poster to its default."""
    print(f"  -> Attempting generic reset for: {item.title}")
    try:
        item.edit(**{'thumb.locked': 0})
        item.refresh()
        print(f"  ✅ Poster unlocked and refreshed for {item.title}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to perform generic reset for {item.title}: {e}")
    return False

def revert_to_original_poster(item, original_url):
    """Reverts a poster to a specific previously saved poster URL."""
    try:
        if not original_url:
            print(f"  ⚠️  Could not find original poster URL for '{item.title}'. Falling back to reset.")
            return reset_poster(item)

        for poster in item.posters():
            if poster.key == original_url:
                item.setPoster(poster)
                print(f"  ✅ Reverted poster for '{item.title}' to original.")
                return True

        print(f"  ⚠️  Could not find specific poster URL in Plex for '{item.title}'. Falling back to reset.")
        return reset_poster(item)
    except Exception as e:
        print(f"  ❌ Error reverting poster for '{item.title}': {e}. Falling back to reset.")
        return reset_poster(item)

def should_have_overlay(show):
    try:
        if len(show.seasons()) < 2: return False
        valid_seasons = [s for s in show.seasons() if s.index is not None]
        if not valid_seasons: return False
        latest_season = max(valid_seasons, key=lambda s: s.index)
        episode1 = next((ep for ep in latest_season.episodes() if ep.index == 1), None)
        if not episode1 or not episode1.originallyAvailableAt: return False
        if episode1.originallyAvailableAt < cutoff: return False
        return True
    except Exception as e:
        print(f"Error checking overlay eligibility for {show.title}: {e}")
        return False

def process_show_overlay(show, overlaid_data):
    """Apply overlay to a show"""
    try:
        print(f"Processing: {show.title}")
        
        seasons = show.seasons()
        valid_seasons = [s for s in seasons if s.index is not None]
        latest_season = max(valid_seasons, key=lambda s: s.index)
        
        poster_url = f"{PLEX_URL}{show.thumb}?X-Plex-Token={PLEX_TOKEN}"
        response = requests.get(poster_url)
        if response.status_code != 200:
            print(f"Failed to download show poster for {show.title}")
            return False
        
        original_poster = Image.open(io.BytesIO(response.content))
        overlay_img = Image.open(OVERLAY_PATH)
        result = apply_overlay(original_poster, overlay_img)
        
        season_poster_result = None
        if latest_season.thumb:
            season_poster_url = f"{PLEX_URL}{latest_season.thumb}?X-Plex-Token={PLEX_TOKEN}"
            season_response = requests.get(season_poster_url)
            if season_response.status_code == 200:
                season_original_poster = Image.open(io.BytesIO(season_response.content))
                season_poster_result = apply_overlay(season_original_poster, overlay_img)

        safe_title = sanitize_filename(show.title)
        show_rating_key = str(show.ratingKey)

        if PREVIEW_MODE:
            preview_path = os.path.join(PREVIEW_FOLDER, f"{safe_title}_show.png")
            result.save(preview_path)
            print(f"Show preview saved: {preview_path}")
            if season_poster_result:
                season_preview_path = os.path.join(PREVIEW_FOLDER, f"{safe_title}_season.png")
                season_poster_result.save(season_preview_path)
                print(f"Season preview saved: {season_preview_path}")
            
            overlaid_data[show_rating_key] = { "title": show.title, "timestamp": now.isoformat(), "preview_only": True }
        else:
            original_show_poster_url = show.thumb
            original_season_poster_url = latest_season.thumb if latest_season else None

            temp_path = os.path.join(PREVIEW_FOLDER, f"temp_{safe_title}_show.png")
            result.save(temp_path)
            try:
                show.uploadPoster(filepath=temp_path)
                print(f"Show poster uploaded for: {show.title}")
                
                if season_poster_result:
                    season_temp_path = os.path.join(PREVIEW_FOLDER, f"temp_{safe_title}_season.png")
                    season_poster_result.save(season_temp_path)
                    try:
                        latest_season.uploadPoster(filepath=season_temp_path)
                        print(f"Season poster uploaded for: {show.title} - Season {latest_season.index}")
                    except Exception as season_e:
                        print(f"  ⚠️  WARNING: Failed to upload SEASON poster for '{show.title}': {season_e}")
                    finally:
                        if os.path.exists(season_temp_path):
                            os.remove(season_temp_path)
                
                overlaid_data[show_rating_key] = {
                    "title": show.title, "timestamp": now.isoformat(), "preview_only": False,
                    "original_show_poster_url": original_show_poster_url,
                    "original_season_poster_url": original_season_poster_url
                }
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        return True
    except Exception as e:
        print(f"Failed to process '{show.title}': {e}")
        import traceback
        traceback.print_exc()
        return False

def remove_show_overlay(show, overlaid_data):
    """Remove overlay by reverting to the original poster."""
    try:
        print(f"Removing overlay from: {show.title}")
        show_rating_key = str(show.ratingKey)
        log_entry = overlaid_data.get(show_rating_key)
        
        if PREVIEW_MODE:
            print(f"[Preview] Would remove overlay from: {show.title}")
        else:
            revert_to_original_poster(show, log_entry.get("original_show_poster_url") if log_entry else None)
            
            if log_entry and log_entry.get("original_season_poster_url"):
                seasons = show.seasons()
                valid_seasons = [s for s in seasons if s.index is not None]
                latest_season = max(valid_seasons, key=lambda s: s.index) if valid_seasons else None
                if latest_season:
                    revert_to_original_poster(latest_season, log_entry.get("original_season_poster_url"))

        if show_rating_key in overlaid_data:
            del overlaid_data[show_rating_key]
        return True
    except Exception as e:
        print(f"Failed to remove overlay from '{show.title}': {e}")
        return False

def revert_all_posters(plex):
    """Iterates through the log file and reverts all posters to their originals."""
    print("--- Starting Revert Process ---")
    if PREVIEW_MODE:
        print("Error: Cannot run revert in PREVIEW_MODE. Please set PREVIEW_MODE to False and run again.")
        return
        
    overlaid_data = load_log_data()
    if not overlaid_data:
        print("Log file is empty. Nothing to revert.")
        return

    reverted_count = 0
    
    # MODIFIED: Iterate over a list copy of the items to prevent RuntimeError.
    # This is the critical fix for the crash.
    for rating_key, data in list(overlaid_data.items()):
        try:
            show = plex.fetchItem(f"/library/metadata/{rating_key}")
            print(f"Reverting: {data.get('title', rating_key)}")
            
            if remove_show_overlay(show, overlaid_data):
                reverted_count += 1
        except Exception as e:
            print(f"Could not fetch item with key {rating_key} ('{data.get('title', 'Unknown')}'): {e}")
            print("  -> Removing stale entry from log.")
            if rating_key in overlaid_data:
                del overlaid_data[rating_key]

    save_log(overlaid_data)
    print(f"\n--- Revert Complete ---")
    print(f"  ✅ Reverted posters for {reverted_count} shows.")

def run_overlay_update(plex):
    """Runs the main overlay update logic."""
    global now, cutoff
    now = datetime.now()
    cutoff = now - timedelta(days=10)
    
    print(f"\n--- Starting run at {now.strftime('%Y-%m-%d %H:%M:%S')} ---")
    if PREVIEW_MODE: print("--- RUNNING IN PREVIEW MODE ---")

    overlaid_data = load_log_data()
    print("🔍 Scanning library for shows...")
    should_have_overlays = set()
    for section in plex.library.sections():
        if section.type == 'show':
            try:
                for show in section.all():
                    if should_have_overlay(show):
                        should_have_overlays.add(str(show.ratingKey))
            except Exception as e:
                print(f"⚠️  Could not process section '{section.title}': {e}")

    print(f"Found {len(should_have_overlays)} shows that should have overlays.")
    processed_count, removed_count = 0, 0
    
    for section in plex.library.sections():
        if section.type == 'show':
            try:
                for show in section.all():
                    rating_key = str(show.ratingKey)
                    if rating_key in should_have_overlays:
                        if rating_key not in overlaid_data or (overlaid_data[rating_key].get("preview_only", False) and not PREVIEW_MODE):
                            if process_show_overlay(show, overlaid_data):
                                processed_count += 1
            except Exception as e:
                print(f"⚠️  Could not process section '{section.title}' for additions: {e}")

    shows_to_remove = []
    for rating_key in list(overlaid_data.keys()):
        if rating_key not in should_have_overlays:
            try:
                show = plex.fetchItem(f"/library/metadata/{rating_key}")
                shows_to_remove.append(show)
            except Exception as e:
                print(f"Failed to fetch show {rating_key}: {e}. Removing inaccessible entry from log.")
                del overlaid_data[rating_key]
                removed_count += 1

    if shows_to_remove: print(f"Removing overlays from {len(shows_to_remove)} shows...")
    for show in shows_to_remove:
        if remove_show_overlay(show, overlaid_data):
            removed_count += 1

    save_log(overlaid_data)
    print(f"\n✅ Processing complete!")
    print(f"  Added/Updated overlays: {processed_count}")
    print(f"  Removed overlays: {removed_count}")
    print(f"  Total shows with overlays: {len(overlaid_data)}")

# === MAIN EXECUTION BLOCK ===
if __name__ == "__main__":
    try:
        plex = PlexServer(PLEX_URL, PLEX_TOKEN, timeout=60)
        plex.clients()
        print("✅ Successfully connected to Plex server.")
    except Exception as e:
        print(f"❌ Could not connect to Plex server: {e}")
        exit(1)

    if '--revert-all' in sys.argv:
        revert_all_posters(plex)
        print("\nScript finished.")
    elif RUN_SCHEDULE_HOURS > 0:
        print(f"Script started. Will run every {RUN_SCHEDULE_HOURS} hours.")
        while True:
            try:
                run_overlay_update(plex)
            except Exception as e:
                print(f"\n🔥🔥🔥 An unexpected error occurred in the main loop: {e}")
                import traceback
                traceback.print_exc()

            next_run_time = datetime.now() + timedelta(hours=RUN_SCHEDULE_HOURS)
            print(f"\n--- Run finished. Sleeping for {RUN_SCHEDULE_HOURS} hours. ---")
            print(f"--- Next run scheduled for: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
            time.sleep(RUN_SCHEDULE_HOURS * 60 * 60)
    else:
        print("Script configured to run only once.")
        run_overlay_update(plex)
        print("\nScript finished.")
