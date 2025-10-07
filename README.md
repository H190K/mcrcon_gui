# Minecraft RCON Control Panel

A dual-interface Python application for managing Minecraft servers via RCON. Includes both a classic Tkinter GUI and a modern WebView-based GUI. Developed by [h190k](https://github.com/h190k).

---

## Features
- Send RCON commands to Minecraft servers
- View server responses in real time
- Quick command buttons for common tasks
- Persistent connection settings
- Cross-platform (Windows, Linux, macOS)
- Two GUI options: Tkinter (classic) and WebView (modern)

---

## Getting Started

### Clone the Repository
You can clone this repo using:
```bash
git clone https://github.com/h190k/mcrcon_gui.git
```

---

## Scripts Overview

### 1. `rcon_gui_formc.py` (Tkinter GUI)

**How it works:**
- Uses Python's built-in Tkinter library for a lightweight, native desktop interface.
- Presents fields for server IP, port, password, and command entry.
- Console output area displays server responses.
- Quick command buttons for common Minecraft server actions (e.g., list, save, stop).
- Footer always displays author credit ("Designed by h190k").
- Window icon is set using Tkinter's icon functionality (if available).

**Benefits:**
- Fast startup, minimal dependencies.
- Works on systems without a modern browser engine.
- Simple, familiar look for users who prefer classic desktop apps.

---

### 2. `webviewmcrcongui.py` (WebView GUI)

**How it works:**
- Uses [pywebview](https://pywebview.flowrl.com/) to create a desktop window running a local HTML/JS interface.
- Modern, responsive UI with dark mode and rich controls.
- All server communication handled in Python backend; frontend communicates via JS bridge.
- Quick command buttons, command history, and real-time console output.
- Footer displays clickable author credit ("design by h190k") linking to your website.
- On Windows, sets the application icon using a workaround (Windows API) for a professional look.

**Benefits:**
- Sleek, modern interface with better UX and theming.
- Easier to extend with web technologies (HTML, CSS, JS).
- More visually appealing and user-friendly.

---

## Requirements
- Python 3.8+
- `mcrcon.exe` (included)
- For Tkinter GUI: No extra dependencies
- For WebView GUI: `pywebview` (`pip install pywebview`)

---

## Running the GUIs

#### Tkinter GUI
```bash
python rcon_gui_formc.py
```

#### WebView GUI
```bash
python webviewmcrcongui.py
```

---

## Configuration
- Edit `config.json` to set default server IP, port, and password.
- Place your `icon.ico` in the same directory for custom window icon.

---

## Author
Developed by [h190k](https://github.com/h190k)
**📧 Get in Touch:**
- 🐦 **Twitter/X**: [@h190k](https://twitter.com/h190k) - Follow for updates
- 📧 **Email**: [info@h190k.com](mailto:info@h190k.com) - For business inquiries
- 🌟 **Star** this repo if it helped you!

**💖 Support the Project:**
- Fork it and add your features
- Report bugs or suggest improvements
- Share it with friends who need a better downloader
- If you find my projects useful, consider supporting me with a donation.  
Your support helps me create more open-source tools and share them with the community.  

[![Donate on DeStream](https://img.shields.io/badge/Donate-DeStream-blue?style=for-the-badge)](https://destream.net/live/H190K/donate)  
[![Donate with NOWPayments](https://img.shields.io/badge/Donate-NOWPayments-purple?style=for-the-badge)](https://nowpayments.io/donation?api_key=J0QACAH-BTH4F4F-QDXM4ZS-RCA58BH)  


---

## License
See `LICENSE` for details.