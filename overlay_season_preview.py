import os
import json
import re
import time  # NEW: Import the time module
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
PREVIEW_MODE = True
PREVIEW_FOLDER = 'preview_posters'
RUN_SCHEDULE_HOURS = 24  # NEW: Hours to wait between runs. Set to 0 to run only once.

# === SETUP ===
# MODIFIED: Moved PlexServer connection to the main run function to allow for re-connection
now = datetime.now()
cutoff = now - timedelta(days=10)

if not os.path.exists(PREVIEW_FOLDER):
    os.makedirs(PREVIEW_FOLDER)

# Check if overlay file exists
if not os.path.exists(OVERLAY_PATH):
    print(f"Error: Overlay file '{OVERLAY_PATH}' not found!")
    exit(1)

# Load existing log data with error handling
# MODIFIED: This will be reloaded each run to stay fresh
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
    # Remove/replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = filename.strip()
    return filename

def save_log(data_to_save): # MODIFIED: Pass data to save
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

def should_have_overlay(show):
    """Check if a show should currently have an overlay"""
    try:
        # Must have at least 2 seasons
        seasons = show.seasons()
        if len(seasons) < 2:
            return False
        
        # Get latest season - filter out None indexes and sort
        valid_seasons = [s for s in seasons if s.index is not None]
        if not valid_seasons:
            return False
            
        latest_season = max(valid_seasons, key=lambda s: s.index)
        episodes = latest_season.episodes()
        episode1 = next((ep for ep in episodes if ep.index == 1), None)
        
        if not episode1:
            return False
        
        # Check if this is actually a NEW season (aired recently)
        if episode1.originallyAvailableAt is None:
            return False
            
        # Only overlay if the season originally aired within the last 20 days
        # MODIFIED: Use the global cutoff
        if episode1.originallyAvailableAt < cutoff:
            return False
            
        return True
        
    except Exception as e:
        print(f"Error checking overlay eligibility for {show.title}: {e}")
        return False

def process_show_overlay(show, overlaid_data): # MODIFIED: Pass overlaid_data
    """Apply overlay to a show"""
    try:
        print(f"Processing: {show.title}")
        
        # Get latest season
        seasons = show.seasons()
        valid_seasons = [s for s in seasons if s.index is not None]
        latest_season = max(valid_seasons, key=lambda s: s.index)
        
        # Download original show poster
        poster_url = f"{PLEX_URL}{show.thumb}?X-Plex-Token={PLEX_TOKEN}"
        response = requests.get(poster_url)
        if response.status_code != 200:
            print(f"Failed to download show poster for {show.title}")
            return False
        
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
            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        return True
        
    except Exception as e:
        print(f"Failed to process '{show.title}': {e}")
        import traceback
        traceback.print_exc()
        return False

def remove_show_overlay(show, overlaid_data): # MODIFIED: Pass overlaid_data
    """Remove overlay from a show"""
    try:
        print(f"Removing overlay from: {show.title}")
        
        # Get latest season
        seasons = show.seasons()
        valid_seasons = [s for s in seasons if s.index is not None]
        latest_season = max(valid_seasons, key=lambda s: s.index) if valid_seasons else None
        
        if PREVIEW_MODE:
            print(f"[Preview] Would remove overlay from: {show.title}")
        else:
            # Reset show poster
            reset_poster(show)
            
            # Reset season poster if it exists
            if latest_season:
                reset_poster(latest_season)
        
        # Remove from log
        if str(show.ratingKey) in overlaid_data:
            del overlaid_data[str(show.ratingKey)]
        
        return True
        
    except Exception as e:
        print(f"Failed to remove overlay from '{show.title}': {e}")
        return False

# === NEW: MAIN PROCESSING FUNCTION WRAPPER ===
def run_overlay_update():
    """
    Connects to Plex and runs the main overlay update logic.
    This function contains the core logic of the script.
    """
    global now, cutoff  # Ensure we update the global time variables each run
    
    # Update time-sensitive variables for this run
    now = datetime.now()
    cutoff = now - timedelta(days=10)
    
    print(f"\n--- Starting run at {now.strftime('%Y-%m-%d %H:%M:%S')} ---")
    if PREVIEW_MODE:
        print("--- RUNNING IN PREVIEW MODE ---")

    try:
        plex = PlexServer(PLEX_URL, PLEX_TOKEN, timeout=30)
        # Test connection
        plex.clients()
        print("✅ Successfully connected to Plex server.")
    except Exception as e:
        print(f"❌ Could not connect to Plex server: {e}")
        print("Skipping this run.")
        return

    # Load the latest log data at the start of the run
    overlaid_data = load_log_data()

    print("🔍 Scanning library for shows...")

    # Get all shows that should currently have overlays
    should_have_overlays = set()
    processed_count = 0
    removed_count = 0

    for section in plex.library.sections():
        if section.type != 'show':
            continue
        
        try:
            for show in section.all():
                if should_have_overlay(show):
                    should_have_overlays.add(str(show.ratingKey))
        except Exception as e:
            print(f"⚠️  Could not process section '{section.title}': {e}")


    print(f"Found {len(should_have_overlays)} shows that should have overlays.")

    # Process additions - shows that should have overlays but don't
    for section in plex.library.sections():
        if section.type != 'show':
            continue
        
        try:
            for show in section.all():
                rating_key = str(show.ratingKey)
                
                if rating_key in should_have_overlays:
                    # Check if it already has an overlay
                    if rating_key not in overlaid_data:
                        # Needs overlay
                        if process_show_overlay(show, overlaid_data):
                            processed_count += 1
                    elif overlaid_data[rating_key].get("preview_only", False) and not PREVIEW_MODE:
                        # Convert preview to live
                        print(f"Converting preview to live: {show.title}")
                        if process_show_overlay(show, overlaid_data):
                            processed_count += 1
        except Exception as e:
            print(f"⚠️  Could not process section '{section.title}' for additions: {e}")

    # Process removals - shows that have overlays but shouldn't
    shows_to_remove = []
    for rating_key in list(overlaid_data.keys()):
        if rating_key not in should_have_overlays:
            try:
                show = plex.fetchItem(f"/library/metadata/{rating_key}")
                shows_to_remove.append(show)
            except Exception as e:
                print(f"Failed to fetch show {rating_key}: {e}")
                # Remove from log if we can't access the show anymore
                entry = overlaid_data.get(rating_key, {})
                print(f"Removing inaccessible entry from log: {entry.get('title', 'Unknown')}")
                del overlaid_data[rating_key]
                removed_count += 1

    print(f"Removing overlays from {len(shows_to_remove)} shows...")
    for show in shows_to_remove:
        if remove_show_overlay(show, overlaid_data):
            removed_count += 1

    # Save the log file
    save_log(overlaid_data)

    print(f"\n✅ Processing complete!")
    print(f"  Added/Updated overlays: {processed_count}")
    print(f"  Removed overlays: {removed_count}")
    print(f"  Total shows with overlays: {len(overlaid_data)}")

    if PREVIEW_MODE:
        print(f"Preview images saved to: {PREVIEW_FOLDER}")
        print(f"Log file: {LOG_FILE}")
    else:
        print("Posters uploaded to Plex server.")

# === NEW: MAIN EXECUTION BLOCK ===
if __name__ == "__main__":
    if RUN_SCHEDULE_HOURS > 0:
        # Scheduled run
        print(f"Script started. Will run every {RUN_SCHEDULE_HOURS} hours.")
        while True:
            try:
                run_overlay_update()
            except Exception as e:
                print(f"\n🔥🔥🔥 An unexpected error occurred in the main loop: {e}")
                import traceback
                traceback.print_exc()

            next_run_time = datetime.now() + timedelta(hours=RUN_SCHEDULE_HOURS)
            print(f"\n--- Run finished. Sleeping for {RUN_SCHEDULE_HOURS} hours. ---")
            print(f"--- Next run scheduled for: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')} ---")
            time.sleep(RUN_SCHEDULE_HOURS * 60 * 60)
    else:
        # Run once
        print("Script configured to run only once.")
        run_overlay_update()
        print("\nScript finished.")
