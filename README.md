<p align="right">
  🇬🇧 English | <a href="README_zh.md">🇨🇳 简体中文</a>
</p>

<div align="center">
  <a href="https://github.com/HaipingShi/ytdlp-lh/releases/latest">
    <img src="logo.png" alt="独轮车 Logo" width="120" height="120">
  </a>

  <h1>独轮车 DL Cart</h1>

  <p><strong>A Full-Featured Video Downloader — Powered by yt-dlp</strong></p>

  <p>
    <a href="https://github.com/HaipingShi/ytdlp-lh/releases/latest">
      <img src="https://img.shields.io/github/v/release/HaipingShi/ytdlp-lh?style=flat-square&color=%23007ACC" alt="Latest Release">
    </a>
    <a href="https://github.com/HaipingShi/ytdlp-lh/actions">
      <img src="https://img.shields.io/github/actions/workflow/status/HaipingShi/ytdlp-lh/build.yml?style=flat-square" alt="Build Status">
    </a>
    <a href="https://github.com/HaipingShi/ytdlp-lh/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/HaipingShi/ytdlp-lh?style=flat-square&color=%234CAF50" alt="License">
    </a>
    <img src="https://img.shields.io/badge/Windows-10%2F11-blue?style=flat-square&logo=windows" alt="Windows">
    <img src="https://img.shields.io/badge/Python-3.8%2B-yellow?style=flat-square&logo=python" alt="Python">
  </p>

  <p>
    <a href="https://github.com/HaipingShi/ytdlp-lh/releases/latest"><strong>📥 Download EXE (Windows, no install needed)</strong></a>
  </p>
</div>

---

> **What is this?** A standalone video downloader called **独轮车 (DL Cart)** that integrates the full power of [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org/) into a single double-clickable `.exe`. No Python, no FFmpeg, no command line — just paste a URL and download.

---

## What It Can Do

Everything yt-dlp can do, accessible through a clean GUI:

### Core Download Engine

- **1000+ sites supported** — YouTube, Bilibili, Twitter/X, TikTok, Douyin, Vimeo, and many more (same as yt-dlp)
- **Best quality by default** — Automatically selects the best available video + audio streams and merges them
- **Quality presets** — 4K, 1080p, 720p, 480p, or audio-only, one click to switch
- **Custom format string** — Advanced users can enter any yt-dlp format string directly
- **Speed limiting** — Cap download bandwidth (KB/s), useful on shared connections

### Subtitles & Metadata

- **10+ subtitle languages** — English, Chinese (Simplified / Traditional), Japanese, Korean, Spanish, French, German, Russian, auto-detect
- **Auto-generated subtitles** — Download machine-generated subtitles where available
- **Thumbnail embedding** — Automatically embeds video thumbnails into downloaded files
- **Metadata tagging** — Writes title, uploader, and other metadata via FFmpeg

### Download Management

- **Concurrent downloads** — Up to 10 simultaneous downloads (configurable)
- **Queue system** — Add multiple URLs, they download in order as slots free up
- **Cancel & retry** — Cancel in-progress downloads cleanly; retry failed ones with one click
- **Persistent history** — Last 200 downloads saved to disk, survives app restart
- **Right-click actions** — Cancel / Retry / Open File / Open Folder / Delete from list

### Real-Time Monitoring

- **Visual progress bar** — Unicode block bar `████░░░░ 45%` updates in real time
- **Speed & ETA** — Live download speed and estimated time remaining
- **File size tracking** — Shows total and downloaded bytes
- **Color-coded status** — Green = done, Yellow = downloading, Red = failed

### System Integration

- **Bundled FFmpeg** — ffmpeg.exe is packed inside the EXE, zero external dependencies
- **Windows notifications** — Toast notification pops up when a download finishes
- **Dark / Light theme** — Switch in settings, dark mode by default
- **Proxy support** — Configure HTTP/SOCKS proxy for restricted networks

---

## 🔒 Windows SmartScreen Warning

When you run the EXE for the first time, Windows may show:

> *"Windows protected your PC"*

This is a **false positive** — the app is built from [public source code](https://github.com/HaipingShi/ytdlp-lh) by GitHub Actions. It happens because the EXE is not code-signed.

**How to bypass:**

1. Click **"More info"**
2. Click **"Run anyway"**

If you prefer not to bypass it, you can [build the EXE yourself from source](#building-from-source) or [run directly with Python](#running-from-source).

---

## Download & Install

### Windows EXE (Recommended)

1. Go to **[Latest Release](https://github.com/HaipingShi/ytdlp-lh/releases/latest)**
2. Download `DLCart.exe`
3. Double-click to run — no installer, no dependencies

The EXE already includes yt-dlp + FFmpeg. It just works.

### Running from Source

Requirements: Python 3.8+, Windows / macOS / Linux.

```bash
git clone https://github.com/HaipingShi/ytdlp-lh.git
cd ytdlp-lh
pip install yt-dlp
python ytdlp_gui.py
```

> FFmpeg should be installed separately if running from source. On Windows, place `ffmpeg.exe` next to `ytdlp_gui.py`.

### Building from Source

```bash
pip install pyinstaller

# Windows (bundles ffmpeg.exe if present in current dir)
pyinstaller --onefile --windowed --collect-all yt_dlp ^
  --add-binary "ffmpeg.exe;." --add-binary "ffprobe.exe;." ^
  --name DLCart ytdlp_gui.py
```

---

## Quick Start

1. **Double-click** `DLCart.exe`
2. **Paste** any video URL into the input box (Ctrl+V)
3. **Pick quality** — leave "Best" for maximum quality
4. **Click Download**
5. Done — click **"Open File"** in the right-click menu to play it

### Keyboard & Mouse Shortcuts

| Action | How |
| ------ | --- |
| Paste URL | Ctrl+V in URL field, or right-click → Paste |
| Cancel download | Right-click row → Cancel |
| Retry failed | Right-click row → Retry |
| Open downloaded file | Right-click row → Open File |
| Open download folder | Right-click row → Open Folder |
| Clear URL | Click the Clear button |

---

## Settings

Open via the ⚙️ button. All settings persist across sessions.

| Setting | Description | Default |
| ------- | ----------- | ------- |
| Download Directory | Where files are saved | `~/Downloads` |
| Max Concurrent | Parallel download slots (1–10) | 3 |
| Speed Limit | KB/s cap, 0 = unlimited | 0 |
| Theme | Dark or Light | Dark |

Settings are stored at `~/.dlcart/settings.json`.

---

## Supported Sites

This application supports **every site that yt-dlp supports** — over 1000 and counting. Here are some popular ones:

| Site | Site | Site |
| ---- | ---- | ---- |
| YouTube | Bilibili | Twitter/X |
| TikTok / Douyin | Vimeo | Dailymotion |
| Facebook | Instagram | Reddit |
| SoundCloud | Niconico | Twitch |
| Pinterest | Tumblr | Many more... |

Full list: [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## Project Structure

```
ytdlp-lh/
├── ytdlp_gui.py          # Entire application in a single file
├── requirements.txt      # Python dependencies
├── .github/workflows/
│   └── build.yml         # CI: build EXE + publish to GitHub Releases
├── docs/                 # Documentation & plans
└── README.md
```

---

## Troubleshooting

<details>
<summary><strong>Windows says "protected your PC"</strong></summary>

This is SmartScreen blocking an unsigned app. Click **"More info"** → **"Run anyway"**. See the [Security Notice](#-windows-smartscreen-warning) section above for details and alternatives.
</details>

<details>
<summary><strong>Video downloads but has no audio</strong></summary>

This means video and audio streams were not merged. Make sure FFmpeg is available. If using the EXE, FFmpeg is bundled and this shouldn't happen. If running from source, install FFmpeg.
</details>

<details>
<summary><strong>"Unsupported URL" error</strong></summary>

- Check your internet connection
- Make sure the URL works in a browser
- The site might require login, be region-locked, or not be supported by yt-dlp yet
</details>

<details>
<summary><strong>Downloads are slow</strong></summary>

- Try setting a speed limit (Settings → Speed Limit) — some servers throttle aggressive connections
- Select a lower quality to reduce file size
- Your ISP might be throttling video traffic — try a VPN
</details>

<details>
<summary><strong>App won't start</strong></summary>

**EXE version:**

- Requires Windows 10 1809+
- Right-click → Properties → check "Unblock" if downloaded from the internet
- Try Run as Administrator

**Python version:**

- Ensure Python 3.8+: `python --version`
- Install deps: `pip install yt-dlp`
- Check `dlcart.log` for error details
</details>

---

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

Bug reports and feature requests welcome at [Issues](https://github.com/HaipingShi/ytdlp-lh/issues).

---

## License

MIT License — see [LICENSE](LICENSE).

---

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — The download engine that makes everything possible
- [FFmpeg](https://ffmpeg.org/) — Stream merging, metadata, and thumbnail embedding
- [Python](https://www.python.org/) + [Tkinter](https://docs.python.org/3/library/tkinter.html) — Application runtime and GUI

---

<div align="center">
  <p><strong>Star ⭐ this repo if you find it useful!</strong></p>
</div>
