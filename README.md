# Plex New Season Overlay

Automatically overlay a "New Season" banner on Plex show posters when a new season (with 2+ seasons total) is added within the last 20 days.

---

## 📌 What It Does

- Scans your Plex library for shows with 2 or more seasons
- Detects if a **new season** (episode 1) was added in the last 20 days
- Adds a **custom "New Season" overlay** to the show’s poster (not the episode!)
- Saves a **preview image** of each modified poster to the `preview_posters/` folder (for review/debugging)
- Logs which shows were changed in `overlaid_log.json`
- Automatically skips already-processed shows
- Can be reverted manually or with a future cleanup script

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

3. Place your custom overlay image in the root folder and name it:

```
new_season.png
```

4. Run the script:

```bash
python overlay_season_preview.py
```

5. What happens:
   - Posters will be updated inside Plex
   - A copy of each modified poster (with the overlay) will be saved in the `preview_posters/` folder
   - The script logs all changes in `overlaid_log.json` so it doesn't reprocess the same shows next time

---

## 🧼 Undo / Cleanup

This script does not permanently overwrite original posters in Plex, but there’s currently no automatic way to revert them.  
To undo changes, you can:
- Restore the default poster manually in Plex
- Use your own backups from `preview_posters/` to re-upload if needed

A future version may include a cleanup tool that removes overlays after 20 days.

---

## 💡 Notes

- This is a **standalone** Python script — **no Kometa/YAML required**
- Tested on both PlexPass and regular Plex setups
- Fully open-source — contributions are welcome!

---

## ☕ Donate

Like this project? Want to support future updates?

### 💳 Donation Options:
- [Buy Me a Coffee](https://www.buymeacoffee.com/) – clean, PayPal-free option (great for Canadians 🇨🇦)
- [Ko-fi](https://ko-fi.com/) – another trusted donation platform
- **Crypto** (Bitcoin or Ethereum — coming soon)
- **Interac e-transfer** (for Canadians — contact me via GitHub)

> Avoiding PayPal? These options let you support open-source creators without the hassle.

---

## 📄 License

MIT License — free for personal or commercial use.

---

## 👤 Author

**Butta Jones**  
GitHub: [@buttajones](https://github.com/buttajones)
