# Minecraft RCON Control Panel

A dual-interface Python application for managing Minecraft servers via RCON. Includes both a classic Tkinter GUI and a modern WebView-based GUI. Developed by [h190k](https://github.com/h190k).

## Screenshot

### Tkinter Version
![Tk version image ](https://github.com/H190K/h190k.com-repo/blob/main/Screenshot%202025-10-07%20062558.png?raw=true)

### WebView Version
![Webview version image ](https://github.com/H190K/h190k.com-repo/blob/main/Screenshot%202025-10-07%20072535.png?raw=true)

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



**Benefits:**
- Sleek, modern interface with better UX and theming.
- Easier to extend with web technologies (HTML, CSS, JS).
- More visually appealing and user-friendly.

---

## Requirements
- Python 3.8+ - Download this if you want to fork it, tweak the code, or make it your own. You can download it from [python.org](https://www.python.org/downloads/).
- `mcrcon.exe` (included)
- For Tkinter GUI: No extra dependencies
- For WebView GUI: `pywebview` (`pip install pywebview(cef)` - Installs the CEF backend for better performance and features.)

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

---

## Author
Developed by [h190k](https://github.com/h190k)
**📧 Get in Touch:**
- 🐦 **Twitter/X**: [@h190k](https://twitter.com/h190k) - Follow for updates
- 📧 **Email**: [info@h190k.com](mailto:info@h190k.com) - For business inquiries
- 🌟 **Star** this repo if it helped you!

## 💖 Support the Project

Love this worker? Here's how you can help:

- 🍴 **Fork it** and add your own features
- 🐛 **Report bugs** or suggest improvements via [GitHub Issues](https://github.com/H190K/mcrcon_gui/issues)
- 📢 **Share it** with developers who You think might need this
- ⭐ **Star the repo** to show your support

If my projects make your life easier, consider buying me a coffee! Your support helps me create more open-source tools for the community.

<div align="center">

[![Support via DeStream](https://img.shields.io/badge/🍕_Feed_the_Developer-DeStream-FF6B6B?style=for-the-badge)](https://destream.net/live/H190K/donate)

[![Crypto Donations](https://img.shields.io/badge/Crypto_Donations-NOWPayments-9B59B6?style=for-the-badge&logo=bitcoin&logoColor=colored)](https://nowpayments.io/donation?api_key=J0QACAH-BTH4F4F-QDXM4ZS-RCA58BH)

</div>

---

<div align="center">

**Built with ❤️ by [H190K](https://github.com/H190K)**



</div>

---

## License
[See LICENSE for details.](LICENSE)