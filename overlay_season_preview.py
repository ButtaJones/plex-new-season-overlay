import os
import json
import requests
from datetime import datetime, timedelta
from PIL import Image
from plexapi.server import PlexServer
from io import BytesIO

PLEX_URL = 'http://localhost:32400'
PLEX_TOKEN = 'YOUR_PLEX_TOKEN_HERE'
OVERLAY_FILE = 'new_season.png'
LOG_FILE = 'overlaid_log.json'
DAYS_WINDOW = 20
PREVIEW_DIR = 'preview_posters'

plex = PlexServer(PLEX_URL, PLEX_TOKEN)
overlay_img = Image.open(OVERLAY_FILE).convert("RGBA")
now = datetime.now()

if os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'r') as f:
        overlaid = json.load(f)
else:
    overlaid = {}

for show in plex.library.section('TV Shows').all():
    if len(show.seasons()) < 2:
        continue
    for season in show.seasons():
        episodes = season.episodes()
        if not episodes:
            continue
        ep1 = sorted(episodes, key=lambda e: e.index or 0)[0]
        added_at = ep1.addedAt
        if (now - added_at).days <= DAYS_WINDOW:
            if show.ratingKey in overlaid:
                continue
            print(f"Overlaying: {show.title}")
            try:
                poster_url = show.thumb
                img_url = f"{PLEX_URL}{poster_url}?X-Plex-Token={PLEX_TOKEN}"
                response = requests.get(img_url)
                poster_img = Image.open(BytesIO(response.content)).convert("RGBA")

                # Resize overlay based on poster width
                ow = poster_img.width
                scale_factor = 0.9
                overlay_scaled = overlay_img.resize(
                    (int(ow * scale_factor), int(overlay_img.height * (ow * scale_factor) / overlay_img.width)),
                    Image.LANCZOS
                )

                position = (int((poster_img.width - overlay_scaled.width) / 2),
                            poster_img.height - overlay_scaled.height)
                poster_img.paste(overlay_scaled, position, overlay_scaled)

                preview_path = os.path.join(PREVIEW_DIR, f"{show.title}.png")
                poster_img.save(preview_path)

                show.uploadPoster(filepath=preview_path)
                overlaid[show.ratingKey] = datetime.now().isoformat()
            except Exception as e:
                print(f"Failed to overlay {show.title}: {e}")

with open(LOG_FILE, 'w') as f:
    json.dump(overlaid, f, indent=2)
