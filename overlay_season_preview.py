import os
import json
import re
import time
import sys
from datetime import datetime, timedelta
from plexapi.server import PlexServer
from PIL import Image
import io
import requests

# === CONFIGURATION ===
PLEX_URL = 'http://192.168.1.23:32400'  # Your Plex server URL
PLEX_TOKEN = 'Cw-KSqhstD32ywNyvBKJ'       # Your Plex token
OVERLAY_PATH = 'new_season.png'          # Your overlay file
LOG_FILE = 'overlaid_log.json'
BACKUP_FOLDER = 'poster_backups'         # NEW: Folder to store original posters
PREVIEW_MODE = False                     # Set to False to apply overlays or revert
PREVIEW_FOLDER = 'preview_posters'
RUN_SCHEDULE_HOURS = 0                   # Set to 0 to run only once.

# === SETUP ===
now = datetime.now()
cutoff = now - timedelta(days=10)

# Create necessary folders
for folder in [PREVIEW_FOLDER, BACKUP_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

if not os.path.exists(OVERLAY_PATH):
    print(f"Error: Overlay file '{OVERLAY_PATH}' not found!")
    exit(1)

def load_log_data():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f: return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read log file '{LOG_FILE}': {e}")
            return {}
    return {}

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename).strip()

def save_log(data_to_save):
    try:
        with open(LOG_FILE, 'w') as f: json.dump(data_to_save, f, indent=2)
        print("Log saved.")
    except IOError as e: print(f"Error saving log file: {e}")

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
    """Fallback function to reset a poster to its Plex default."""
    print(f"  -> Attempting generic reset for: {item.title}")
    try:
        item.edit(**{'thumb.locked': 0})
        item.refresh()
        print(f"  ✅ Poster unlocked and refreshed for {item.title}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to perform generic reset for {item.title}: {e}")
    return False

# NEW: Backup function
def backup_poster(item):
    """Downloads the current poster for an item and saves it to the backup folder."""
    try:
        poster_url = f"{PLEX_URL}{item.thumb}?X-Plex-Token={PLEX_TOKEN}"
        response = requests.get(poster_url)
        if response.status_code == 200:
            backup_path = os.path.join(BACKUP_FOLDER, f"{item.ratingKey}.png")
            with open(backup_path, 'wb') as f:
                f.write(response.content)
            print(f"  ✅ Backed up poster for '{item.title}' to {backup_path}")
            return backup_path
    except Exception as e:
        print(f"  ⚠️  Failed to back up poster for '{item.title}': {e}")
    return None

# NEW: Revert from backup function
def revert_from_backup(item, backup_path):
    """Reverts a poster by uploading the saved backup file."""
    if not backup_path or not os.path.exists(backup_path):
        print(f"  ⚠️  Backup file not found for '{item.title}'. Falling back to reset.")
        return reset_poster(item)

    try:
        item.uploadPoster(filepath=backup_path)
        print(f"  ✅ Reverted poster for '{item.title}' from backup file.")
        os.remove(backup_path) # Clean up the backup file
        return True
    except Exception as e:
        print(f"  ❌ Error reverting poster for '{item.title}' from backup: {e}")
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
        print(f"Error checking eligibility for {show.title}: {e}")
        return False

def process_show_overlay(show, overlaid_data):
    """Backs up, applies overlay, and logs a show."""
    try:
        print(f"Processing: {show.title}")
        rating_key = str(show.ratingKey)
        
        # In live mode, only proceed if not already overlaid
        if not PREVIEW_MODE and rating_key in overlaid_data:
            print("  -> Already overlaid, skipping.")
            return False

        # Backup original posters before doing anything
        show_backup_path = None
        season_backup_path = None
        if not PREVIEW_MODE:
            show_backup_path = backup_poster(show)
            if not show_backup_path:
                print(f"  ❌ Cannot proceed without show poster backup. Skipping.")
                return False

        # Get latest season
        latest_season = max(show.seasons(), key=lambda s: s.index or -1)
        if not PREVIEW_MODE and latest_season.thumb:
            season_backup_path = backup_poster(latest_season)

        # Apply overlay to show poster
        original_poster_img = Image.open(io.BytesIO(requests.get(f"{PLEX_URL}{show.thumb}?X-Plex-Token={PLEX_TOKEN}").content))
        overlay_img = Image.open(OVERLAY_PATH)
        new_show_poster_img = apply_overlay(original_poster_img, overlay_img)

        # Apply overlay to season poster
        new_season_poster_img = None
        if latest_season.thumb:
            original_season_img = Image.open(io.BytesIO(requests.get(f"{PLEX_URL}{latest_season.thumb}?X-Plex-Token={PLEX_TOKEN}").content))
            new_season_poster_img = apply_overlay(original_season_img, overlay_img)

        if PREVIEW_MODE:
            # Save previews
            safe_title = sanitize_filename(show.title)
            new_show_poster_img.save(os.path.join(PREVIEW_FOLDER, f"{safe_title}_show.png"))
            if new_season_poster_img:
                new_season_poster_img.save(os.path.join(PREVIEW_FOLDER, f"{safe_title}_season.png"))
            print("  -> Preview generated.")
            
        else:
            # Upload new posters and log the backup paths
            temp_dir = os.path.join(PREVIEW_FOLDER, 'temp')
            if not os.path.exists(temp_dir): os.makedirs(temp_dir)

            # Upload show poster
            temp_show_path = os.path.join(temp_dir, f"{rating_key}_show.png")
            new_show_poster_img.save(temp_show_path)
            show.uploadPoster(filepath=temp_show_path)
            print(f"  -> Show poster uploaded.")

            # Upload season poster
            if new_season_poster_img:
                temp_season_path = os.path.join(temp_dir, f"{latest_season.ratingKey}_season.png")
                new_season_poster_img.save(temp_season_path)
                try:
                    latest_season.uploadPoster(filepath=temp_season_path)
                    print(f"  -> Season {latest_season.index} poster uploaded.")
                except Exception as e:
                    print(f"  ⚠️  WARNING: Failed to upload SEASON poster: {e}")
                finally:
                    if os.path.exists(temp_season_path): os.remove(temp_season_path)

            if os.path.exists(temp_show_path): os.remove(temp_show_path)
            
            overlaid_data[rating_key] = {
                "title": show.title, "timestamp": now.isoformat(),
                "show_backup_path": show_backup_path,
                "season_backup_path": season_backup_path
            }
        
        return True
    except Exception as e:
        print(f"❌ FAILED to process '{show.title}': {e}")
        import traceback
        traceback.print_exc()
        return False

def remove_show_overlay(show, log_entry):
    """Reverts a show's posters using backup files."""
    try:
        print(f"Reverting: {show.title}")
        if PREVIEW_MODE:
            print("  -> [Preview] Would revert from backup.")
            return True

        # Revert show and season posters
        revert_from_backup(show, log_entry.get("show_backup_path"))
        
        if log_entry.get("season_backup_path"):
            latest_season = max(show.seasons(), key=lambda s: s.index or -1)
            revert_from_backup(latest_season, log_entry.get("season_backup_path"))
            
        return True
    except Exception as e:
        print(f"❌ FAILED to revert '{show.title}': {e}")
        return False

def run_update(plex):
    """Main process to check for and apply/remove overlays."""
    global now, cutoff; now, cutoff = datetime.now(), datetime.now() - timedelta(days=10)
    print(f"\n--- Starting Run: {now.strftime('%Y-%m-%d %H:%M:%S')} ---")
    if PREVIEW_MODE: print("--- RUNNING IN PREVIEW MODE ---")

    overlaid_data = load_log_data()
    
    # 1. Identify all shows that SHOULD have an overlay right now
    print("🔍 Scanning library for shows needing overlays...")
    should_have_overlays = {str(show.ratingKey) for sec in plex.library.sections() if sec.type == 'show' for show in sec.all() if should_have_overlay(show)}
    print(f"Found {len(should_have_overlays)} shows that qualify for an overlay.")

    # 2. Add overlays to qualifying shows that don't have one
    shows_to_process = [key for key in should_have_overlays if key not in overlaid_data]
    if shows_to_process: print(f"\nApplying overlays to {len(shows_to_process)} new shows...")
    processed_count = 0
    for key in shows_to_process:
        try:
            show = plex.fetchItem(f"/library/metadata/{key}")
            if process_show_overlay(show, overlaid_data):
                processed_count += 1
        except Exception as e:
            print(f"❌ Error fetching show {key} to apply overlay: {e}")

    # 3. Remove overlays from shows that no longer qualify
    shows_to_remove = [key for key in overlaid_data if key not in should_have_overlays]
    if shows_to_remove: print(f"\nRemoving overlays from {len(shows_to_remove)} old shows...")
    removed_count = 0
    for key in shows_to_remove:
        try:
            show = plex.fetchItem(f"/library/metadata/{key}")
            if remove_show_overlay(show, overlaid_data[key]):
                del overlaid_data[key] # Remove from log after successful revert
                removed_count += 1
        except Exception as e:
            print(f"❌ Error fetching show {key} to remove overlay. Removing from log.", e)
            del overlaid_data[key] # Remove stale entry

    # 4. Save final state
    save_log(overlaid_data)
    print("\n--- Run Complete ---")
    print(f"  Added: {processed_count} | Removed: {removed_count} | Total Overlaid: {len(overlaid_data)}")


def revert_all(plex):
    """Force-reverts all posters listed in the log file."""
    print("--- Starting Revert All Process ---")
    if PREVIEW_MODE:
        print("❌ Cannot run revert in PREVIEW_MODE. Set to False and run again.")
        return

    overlaid_data = load_log_data()
    if not overlaid_data:
        print("Log file is empty. Nothing to revert.")
        return

    reverted_count = 0
    # Iterate over a copy so we can delete from the original
    for key, log_entry in list(overlaid_data.items()):
        try:
            show = plex.fetchItem(f"/library/metadata/{key}")
            if remove_show_overlay(show, log_entry):
                del overlaid_data[key]
                reverted_count += 1
        except Exception as e:
            print(f"❌ Error fetching '{log_entry.get('title', key)}' to revert. Removing from log.", e)
            del overlaid_data[key] # Remove stale entry

    save_log(overlaid_data)
    print(f"\n--- Revert Complete: {reverted_count} shows reverted. ---")


if __name__ == "__main__":
    try:
        plex = PlexServer(PLEX_URL, PLEX_TOKEN, timeout=60)
        plex.clients()
        print("✅ Successfully connected to Plex server.")
    except Exception as e:
        print(f"❌ Could not connect to Plex server: {e}"); exit(1)

    if '--revert-all' in sys.argv:
        revert_all(plex)
    elif RUN_SCHEDULE_HOURS > 0:
        print(f"Script started. Will run every {RUN_SCHEDULE_HOURS} hours.")
        while True:
            run_update(plex)
            next_run = datetime.now() + timedelta(hours=RUN_SCHEDULE_HOURS)
            print(f"\n--- Sleeping until {next_run.strftime('%Y-%m-%d %H:%M:%S')} ---")
            time.sleep(RUN_SCHEDULE_HOURS * 3600)
    else:
        run_update(plex)

    print("\nScript finished.")
