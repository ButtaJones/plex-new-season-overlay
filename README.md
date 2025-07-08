# Plex New Season Overlay

Automatically overlay a "New Season" banner on Plex show posters when a new season (with 2+ seasons total) is added within the last 20 days.

---

## 📌 What It Does

- Scans your Plex library for shows with 2 or more seasons
- Detects if a **new season** (episode 1) was added in the last 20 days
- Adds a **custom "New Season" overlay** to the show’s poster (not the episode!)
- Saves a backup of each modified poster in `/preview_posters/`
- Logs changes in `overlaid_log.json`
- Automatically skips already-processed shows
- Can be reverted with a cleanup script (optional, not included in repo)

---

## 🧰 Requirements

- Python 3.7+
- A Plex server (you’ll need your **PLEX URL** and **PLEX TOKEN**)
- Dependencies:

```bash
pip install -r requirements.txt
```

---

## ⚙️ Setup & Usage

1. Clone this repo:

```bash
git clone https://github.com/buttajones/plex-new-season-overlay.git
cd plex-new-season-overlay
```

2. Open `overlay_season_preview.py` and update:

```python
PLEX_URL = 'http://localhost:32400'
PLEX_TOKEN = 'YOUR_PLEX_TOKEN_HERE'
```

3. Replace the default `new_season.png` with your own overlay if desired

4. Run the script:

```bash
python overlay_season_preview.py
```

5. Posters will be updated in Plex and preview images will be saved to `preview_posters/`

---

## 🧼 Undo / Cleanup

You can manually reset posters inside Plex or restore them from the `preview_posters` folder. A future update may include an automatic cleanup option after 20 days.

---

## 💡 Notes

- This is a **standalone** Python script. No Kometa/YAML needed.
- Works with both PlexPass and non-PlexPass accounts.
- Uses `plexapi` and `Pillow`
- Fully open-source — PRs and contributions welcome!

---

## ☕ Donate

Like this project? Want to support future features?

### 💳 Options:
- [Buy Me a Coffee](https://www.buymeacoffee.com/) — great for Canadians, no PayPal required
- [Ko-fi](https://ko-fi.com/) — works internationally
- Crypto (BTC/ETH accepted — addresses coming soon)
- 🇨🇦 Interac e-transfer (Canadians only — contact via GitHub email)

> Prefer non-PayPal support? These platforms let you accept donations without relying on PayPal's high fees or restrictions.

---

## 📸 Example

| Before | After |
|--------|-------|
| ![Before Poster](preview_posters/Bear_before.png) | ![After Poster](preview_posters/Bear_after.png) |

---

## 📄 License

MIT License — free for personal and commercial use.

---

## 👤 Author

**Butta Jones**  
GitHub: [@buttajones](https://github.com/buttajones)
