# Plex New Season Overlay

Automatically overlay a "New Season" banner on Plex show posters when a new season is added within the last 20 days. Features intelligent cleanup that automatically removes overlays when seasons are no longer "new".

<img src="https://i.imgur.com/5efMo58.jpg" width="300" /><img src="https://i.imgur.com/CmoZyQv.png" width="300" />

---

## 🎯 What It Does

- **Smart Detection**: Scans your Plex library for shows with 2+ seasons where the latest season aired within the last 20 days
- **Automatic Overlay**: Adds a custom "New Season" banner to both show and season posters
- **Preview Mode**: Generates preview images before making changes (enabled by default)
- **Intelligent Cleanup**: Automatically removes overlays when seasons are no longer "new" (20+ days old)
- **Comprehensive Logging**: Tracks all changes in `overlaid_log.json` with timestamps
- **Skip Processing**: Automatically skips already-processed shows to avoid duplicates
- **Error Handling**: Robust error handling with detailed logging for troubleshooting

---

## 🧰 Requirements

- **Python 3.7+**
- **Plex Media Server** (PlexPass not required)
- **Network Access** to your Plex server
- **Write Permissions** in the script directory

### Dependencies
```bash
pip install -r requirements.txt
```

**Required Python packages:**
- `plexapi` - Plex API interface
- `Pillow` - Image processing
- `requests` - HTTP requests

---

## ⚙️ Setup & Configuration

### 1. Get Your Plex Token
1. Open Plex Web App
2. Play any media item
3. Open browser developer tools (F12)
4. Go to Network tab and look for requests containing `X-Plex-Token`
5. Copy the token value

### 2. Configure the Script
Open `overlay_season_preview.py` and update these settings:

```python
# === CONFIGURATION ===
PLEX_URL = 'http://192.168.1.100:32400'  # Your Plex server URL
PLEX_TOKEN = 'YOUR_PLEX_TOKEN_HERE'       # Your Plex token
OVERLAY_PATH = 'new_season.png'           # Path to your overlay image
LOG_FILE = 'overlaid_log.json'            # Log file location
PREVIEW_MODE = True                       # Enable preview mode (recommended)
CLEANUP_MODE = False                      # Enable cleanup mode
PREVIEW_FOLDER = 'preview_posters'        # Preview images folder
```

### 3. Add Your Overlay Image
Place your custom overlay image in the root folder and name it `new_season.png`

**Overlay Requirements:**
- **Format**: PNG with transparency support
- **Size**: Any size (will be automatically resized to 85% of poster width)
- **Position**: Will be placed at the bottom-center of posters

---

## 🚀 Usage

### First Run (Preview Mode)
```bash
python overlay_season_preview.py
```

**What happens:**
- Scans your library for eligible shows
- Creates preview images in `preview_posters/` folder
- Logs potential changes without modifying Plex
- Shows you exactly what will be changed

### Apply Changes (Live Mode)
```bash
# Edit script: set PREVIEW_MODE = False
python overlay_season_preview.py
```

**What happens:**
- Applies overlays to show and season posters in Plex
- Saves backup preview images
- Updates `overlaid_log.json` with changes
- Skips already-processed shows

### Cleanup Old Overlays
```bash
# Edit script: set CLEANUP_MODE = True
python overlay_season_preview.py
```

**What happens:**
- Checks all previously overlaid shows
- Removes overlays from seasons older than 20 days
- Restores original posters automatically
- Updates log file

---

## 📁 File Structure

```
plex-new-season-overlay/
├── overlay_season_preview.py     # Main script
├── new_season.png               # Your overlay image
├── requirements.txt             # Python dependencies
├── overlaid_log.json           # Processing log (auto-generated)
├── preview_posters/            # Preview images (auto-generated)
│   ├── Show_Name_show.png
│   ├── Show_Name_season.png
│   └── ...
└── README.md                   # This file
```

---

## 🔧 Advanced Configuration

### Customizing Detection Rules

```python
# Change the "new season" timeframe (default: 20 days)
cutoff = now - timedelta(days=30)  # 30 days instead of 20

# Modify overlay size and position
new_width = int(width * 0.75)     # 75% instead of 85%
y = height - new_height - 50      # Add 50px margin from bottom
```

### Multiple Overlay Images

You can create different overlays for different scenarios:

```python
# Use different overlays based on show type or season number
if 'Comedy' in show.genres:
    overlay_path = 'comedy_new_season.png'
elif latest_season.index > 5:
    overlay_path = 'veteran_show_overlay.png'
else:
    overlay_path = 'new_season.png'
```

---

## 🧹 Cleanup & Maintenance

### Automatic Cleanup
The script includes intelligent cleanup that:
- Runs when `CLEANUP_MODE = True`
- Checks all previously overlaid shows
- Removes overlays from seasons older than 20 days
- Restores original posters automatically

### Manual Cleanup
To manually remove overlays:
1. Go to your Plex web interface
2. Navigate to the show → Edit → Poster tab
3. Select "Reset to Default" or choose original poster
4. Save changes

### Log Management
The `overlaid_log.json` file tracks:
- Show title and rating key
- Timestamp of overlay application
- Preview vs live mode status

---

## 🐛 Troubleshooting

### Common Issues

**"No module named 'plexapi'"**
```bash
pip install plexapi Pillow requests
```

**"Connection refused" or "Unauthorized"**
- Verify your `PLEX_URL` is correct
- Check that your `PLEX_TOKEN` is valid
- Ensure Plex server is running and accessible

**"Overlay file not found"**
- Verify `new_season.png` exists in the script directory
- Check file permissions

**Overlays not appearing**
- Run in preview mode first to verify detection
- Check Plex cache (restart Plex server if needed)
- Verify shows meet criteria (2+ seasons, new season within 20 days)

### Debug Mode
Add this to the script for detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📊 Performance & Limitations

### Performance Notes
- **Speed**: Processes ~100 shows in 30-60 seconds
- **Resources**: Uses minimal CPU/memory
- **Network**: Downloads poster images (can be bandwidth-intensive)

### Limitations
- Requires direct network access to Plex server
- Only works with shows that have air dates
- Overlay position is fixed (bottom-center)
- No real-time monitoring (runs on-demand)

---

## 🤝 Contributing

Contributions are welcome! Here's how to help:

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature-name`
3. **Commit** your changes: `git commit -am 'Add feature'`
4. **Push** to the branch: `git push origin feature-name`
5. **Submit** a pull request

### Ideas for Contributions
- Web interface for configuration
- Multiple overlay templates
- Real-time monitoring
- Docker containerization
- Integration with other media management tools

---

## 📄 License

MIT License - free for personal and commercial use.

See [LICENSE](LICENSE) file for details.

---

## ☕ Support This Project

If this script saves you time and enhances your Plex experience, consider supporting future development:

### 💳 Donation Options
- **[Buy Me a Coffee](https://buymeacoffee.com/butta)** - Clean, PayPal-free option 
- **[Ko-fi](https://ko-fi.com/buttajones)** - Another trusted platform
- **Bitcoin**: `bc1qexampleaddresshere` (coming soon)
- **Ethereum**: `0xexampleaddresshere` (coming soon)
- **Interac e-Transfer** (Canadians): Contact via GitHub

> 🇨🇦 **Canadian-friendly**: These options work great for Canadian donors who want to avoid PayPal fees!

---

## 👤 Author

**Butta Jones**  
- GitHub: [@buttajones](https://github.com/buttajones)
- Twitter/X: [@buttajones](https://twitter.com/buttajones)
- Email: Available via GitHub profile

---

## 📝 Changelog

### v2.0.0 (Current)
- ✅ Added automatic cleanup functionality
- ✅ Improved poster reset mechanism
- ✅ Enhanced error handling and logging
- ✅ Better filename sanitization
- ✅ Preview mode improvements

### v1.0.0
- ✅ Initial release
- ✅ Basic overlay functionality
- ✅ Preview mode
- ✅ JSON logging

---

## 🙏 Acknowledgments

- **PlexAPI** developers for the excellent Python library
- **Plex** community for feedback and testing
- **Contributors** who helped improve this script

---

*Made with ❤️ for the Plex community*
