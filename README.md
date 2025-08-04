# Plex New Season Overlay

Automatically overlay a "New Season" banner on Plex show posters when a new season is added within the last 21 days. Features intelligent cleanup that automatically removes overlays when seasons are no longer "new" and smart processing that converts preview overlays to live overlays.

<img src="https://i.imgur.com/5efMo58.jpg" width="100" />     <img src="https://i.imgur.com/CmoZyQv.png" width="100" />

---

## 🎯 What It Does

- **Smart Detection**: Scans your Plex library for shows with 2+ seasons where the latest season aired within the last 21 days
- **Automatic Overlay**: Adds a custom "New Season" banner to both show and season posters
- **Preview Mode**: Generates preview images before making changes (toggle with `PREVIEW_MODE`)
- **Intelligent Cleanup**: Automatically removes overlays when seasons are no longer "new" (21+ days old)
- **Preview-to-Live Conversion**: Seamlessly converts preview overlays to live overlays when switching modes
- **Comprehensive Logging**: Tracks all changes in `overlaid_log.json` with timestamps and mode tracking
- **Skip Processing**: Automatically skips already-processed shows to avoid duplicates
- **Robust Error Handling**: Enhanced error handling with detailed logging and graceful fallbacks
- **Safe Filename Handling**: Sanitizes filenames to prevent filesystem issues

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
PREVIEW_MODE = False                      # Toggle preview/live mode
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
# Set PREVIEW_MODE = True in the script
python overlay_season_preview.py
```

**What happens:**
- Scans your library for eligible shows
- Creates preview images in `preview_posters/` folder
- Logs potential changes without modifying Plex
- Shows you exactly what will be changed

### Apply Changes (Live Mode)
```bash
# Set PREVIEW_MODE = False in the script
python overlay_season_preview.py
```

**What happens:**
- Applies overlays to show and season posters in Plex
- Converts existing preview overlays to live overlays
- Saves backup preview images in preview folder
- Updates `overlaid_log.json` with changes
- Skips already-processed shows

### Automatic Cleanup
The script now automatically handles cleanup by:
- Checking all previously overlaid shows
- Removing overlays from seasons older than 21 days
- Restoring original posters automatically
- Updating log file to reflect changes

---

## 🔧 Key Features & Improvements

### Smart Processing Logic
- **Eligibility Check**: Only processes shows with 2+ seasons where latest season aired within 21 days
- **Duplicate Prevention**: Skips shows that already have overlays applied
- **Preview-to-Live Conversion**: Automatically converts preview overlays to live when switching modes
- **Inaccessible Show Cleanup**: Removes log entries for shows that can no longer be accessed

### Enhanced Error Handling
- **Graceful Fallbacks**: Multiple methods for poster reset if primary method fails
- **Detailed Logging**: Comprehensive error reporting with stack traces
- **Safe File Operations**: Proper temp file cleanup and error recovery

### Improved File Management
- **Filename Sanitization**: Removes invalid characters from filenames
- **Temporary File Cleanup**: Automatically removes temp files after processing
- **Log File Validation**: Handles corrupted log files gracefully

---

## 📁 File Structure

```
plex-new-season-overlay/
├── overlay_season_preview.py     # Main script
├── new_season.png               # Your overlay image
├── requirements.txt             # Python dependencies
├── overlaid_log.json           # Processing log (auto-generated)
├── preview_posters/            # Preview & temp images (auto-generated)
│   ├── Show_Name_show.png
│   ├── Show_Name_season.png
│   └── temp_files...
└── README.md                   # This file
```

---

## 📊 Log File Format

The `overlaid_log.json` tracks each processed show:

```json
{
  "12345": {
    "title": "Example Show",
    "timestamp": "2025-01-15T14:30:00",
    "preview_only": false
  }
}
```

**Fields:**
- `title`: Show name
- `timestamp`: When overlay was applied
- `preview_only`: Whether it's a preview or live overlay

---

## 🧹 Maintenance & Troubleshooting

### Automatic Maintenance
The script handles maintenance automatically:
- Removes overlays from shows that no longer qualify
- Cleans up inaccessible show entries from the log
- Converts preview overlays to live overlays when mode changes

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

**Poster reset issues**
- The script uses multiple fallback methods for poster reset
- If posters don't reset, try restarting your Plex server
- Check Plex logs for additional error information

### Debug Mode
Add this to the script for detailed logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 🔧 Advanced Configuration

### Customizing Detection Rules

```python
# Change the "new season" timeframe (default: 21 days)
cutoff = now - timedelta(days=30)  # 30 days instead of 21

# Modify overlay size and position
new_width = int(width * 0.75)     # 75% instead of 85%
y = height - new_height - 50      # Add 50px margin from bottom
```

### Multiple Overlay Images

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

## 📊 Performance & Limitations

### Performance Notes
- **Speed**: Processes ~100 shows in 30-60 seconds
- **Resources**: Uses minimal CPU/memory
- **Network**: Downloads poster images (can be bandwidth-intensive)
- **Efficiency**: Skips already-processed shows to minimize redundant work

### Limitations
- Requires direct network access to Plex server
- Only works with shows that have air dates
- Overlay position is fixed (bottom-center)
- Depends on Plex API availability

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
- Real-time monitoring with file watchers
- Docker containerization
- Integration with other media management tools
- Custom overlay positioning options

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

### v2.1.0 (Current)
- ✅ Enhanced error handling and recovery
- ✅ Improved poster reset functionality with multiple fallback methods
- ✅ Added filename sanitization for cross-platform compatibility
- ✅ Automatic preview-to-live conversion
- ✅ Better inaccessible show cleanup
- ✅ Improved temporary file management
- ✅ Enhanced logging with detailed error reporting

### v2.0.0
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
