"""
YT-DLP GUI - Simple Windows Video Downloader
A user-friendly GUI for yt-dlp written in Tkinter
"""

import asyncio
import json
import logging
import os
import re
import sys
import tempfile
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from tkinter.font import Font
from typing import Dict, List, Optional, Any

import tkinter as tk
import yt_dlp as youtube_dl
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

# When running as a PyInstaller --onefile exe, bundled files are extracted
# to a temp dir exposed via sys._MEIPASS. Detect ffmpeg.exe there so
# yt_dlp can use it without the user installing anything.
def _find_bundled_ffmpeg() -> Optional[str]:
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass and os.path.isfile(os.path.join(meipass, 'ffmpeg.exe')):
        return meipass  # yt_dlp ffmpeg_location wants the directory
    return None

BUNDLED_FFMPEG_DIR = _find_bundled_ffmpeg()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ytdlp_gui.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default settings
DEFAULT_SETTINGS = {
    'download_dir': str(Path.home() / 'Downloads'),
    'max_concurrent': 3,
    'default_quality': 'best',
    'theme': 'dark'
}

# Quality presets with yt-dlp format strings
QUALITY_PRESETS = {
    'best': {
        'name': 'Best Quality',
        'format': 'bestvideo*+bestaudio/best',
        'description': 'Best available quality'
    },
    '4k': {
        'name': '4K',
        'format': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]/best',
        'description': '4K video quality'
    },
    '1080p': {
        'name': '1080p HD',
        'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        'description': 'Full HD quality'
    },
    '720p': {
        'name': '720p',
        'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'description': 'HD Ready quality'
    },
    '480p': {
        'name': '480p',
        'format': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
        'description': 'Standard quality'
    },
    'audio': {
        'name': 'Audio Only',
        'format': 'bestaudio/best',
        'description': 'Audio only (MP3)'
    }
}


# Add subtitle language options
SUBTITLE_LANGS = {
    'none': 'No Subtitles',
    'en': 'English',
    'zh': 'Chinese',
    'zh-Hans': 'Chinese (Simplified)',
    'zh-Hant': 'Chinese (Traditional)',
    'ja': 'Japanese',
    'ko': 'Korean',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'ru': 'Russian',
    'auto': 'Auto-detect'
}

class DownloadManager:
    """Manages yt-dlp downloads"""

    def __init__(self, error_callback=None):
        self.downloads: Dict[str, Dict[str, Any]] = {}
        self.active_downloads: set = set()
        self.settings: Dict[str, Any] = self.load_settings()
        self.queue: List[str] = []
        self.lock = threading.Lock()
        self._cancel_flags: Dict[str, threading.Event] = {}
        self.error_callback = error_callback  # Callback for error reporting

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file"""
        settings_path = Path.home() / '.ytdlp_gui' / 'settings.json'
        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
        return DEFAULT_SETTINGS.copy()

    def save_settings(self):
        """Save settings to JSON file"""
        settings_path = Path.home() / '.ytdlp_gui' / 'settings.json'
        settings_path.parent.mkdir(exist_ok=True)
        try:
            with open(settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def add_to_queue(self, url: str, quality: str = 'best', format_id: Optional[str] = None,
                       subtitles: str = 'none', subtitle_langs: List[str] = None) -> str:
        """Add download to queue"""
        download_id = str(hash(url + str(datetime.now().timestamp())))

        download = {
            'id': download_id,
            'url': url,
            'quality': quality,
            'format_id': format_id,
            'subtitles': subtitles,
            'subtitle_langs': subtitle_langs or ['en'],
            'status': 'queued',
            'title': '',
            'progress': 0,
            'speed': None,
            'eta': None,
            'file_path': None,
            'file_size': None,
            'error': None,
            'added_at': datetime.now(),
            'started_at': None,
            'completed_at': None
        }

        with self.lock:
            self.downloads[download_id] = download
            self.queue.append(download_id)

        logger.info(f"Added to queue: {download_id} - {url}")
        return download_id

    def process_queue(self):
        """Process download queue"""
        while self.queue and len(self.active_downloads) < self.settings['max_concurrent']:
            with self.lock:
                download_id = self.queue.pop(0)
                if download_id in self.downloads:
                    self.active_downloads.add(download_id)

            threading.Thread(
                target=self.download_video,
                args=(download_id,),
                daemon=True
            ).start()

    def download_video(self, download_id: str):
        """Download a video using yt-dlp"""
        download = self.downloads[download_id]
        cancel_flag = threading.Event()
        self._cancel_flags[download_id] = cancel_flag

        try:
            download['status'] = 'downloading'
            download['started_at'] = datetime.now()

            # Configure yt-dlp options
            options = self._get_download_options(download)

            # Create progress hook
            def progress_hook(d):
                if cancel_flag.is_set():
                    raise Exception("Download cancelled by user")
                if d['status'] == 'downloading':
                    download['progress'] = d.get('_percent_str', '0%').strip('%')
                    download['speed'] = d.get('_speed_str')
                    download['eta'] = d.get('_eta_str')
                    download['downloaded_bytes'] = d.get('downloaded_bytes', 0)

                    if 'total_bytes' in d:
                        download['file_size'] = d['total_bytes']
                    elif 'total_bytes_estimate' in d:
                        download['file_size'] = d['total_bytes_estimate']

                elif d['status'] == 'finished':
                    download['progress'] = 100
                    download['file_path'] = d['filename']
                    logger.info(f"Download finished: {download['title']}")

            options['progress_hooks'] = [progress_hook]

            def extract_info_hook(d):
                try:
                    download['title'] = d.get('title', 'Unknown')
                    logger.info(f"Extracted info: {download['title']}")
                except Exception as e:
                    logger.warning(f"Failed to extract info: {e}")
                    download['title'] = 'Unknown'

            options['postprocessor_hooks'] = [extract_info_hook]

            # Download
            with YoutubeDL(options) as ydl:
                try:
                    info = ydl.extract_info(download['url'], download=True)
                    download['title'] = info.get('title', 'Unknown')
                except DownloadError as e:
                    # yt-dlp specific download error
                    error_msg = str(e)
                    if "Unsupported URL" in error_msg:
                        raise Exception(f"Unsupported URL: {download['url']}. This site may not be supported by yt-dlp. Check supported sites at: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md")
                    elif "Unable to download webpage" in error_msg:
                        raise Exception(f"Network error: Unable to access {download['url']}. Please check your internet connection.")
                    elif "Video unavailable" in error_msg:
                        raise Exception(f"Video unavailable: The video at {download['url']} may be deleted, private, or blocked in your region.")
                    elif "Sign in" in error_msg or "login" in error_msg.lower():
                        raise Exception(f"Authentication required: This video requires login. You may need to use cookies from your browser.")
                    elif "ffmpeg" in error_msg.lower():
                        raise Exception(f"FFmpeg not found: FFmpeg is required for video processing. Please install FFmpeg and add it to PATH.")
                    else:
                        raise Exception(f"Download error: {error_msg}\n\nTry updating yt-dlp: pip install yt-dlp --upgrade")
                except Exception as e:
                    # Unknown error
                    raise Exception(f"Unexpected error: {str(e)}\n\nTry:\n1. Updating yt-dlp: pip install yt-dlp --upgrade\n2. Checking the video URL\n3. Verifying your internet connection")

            download['status'] = 'completed'
            download['completed_at'] = datetime.now()
            logger.info(f"Download completed: {download_id} - {download['title']}")

        except Exception as e:
            error_msg = str(e)
            if 'cancelled by user' in error_msg.lower():
                download['status'] = 'cancelled'
                logger.info(f"Download cancelled: {download_id}")
            else:
                download['status'] = 'failed'
                download['error'] = error_msg
                logger.error(f"Download failed: {download_id} - {e}")
                if self.error_callback:
                    self.error_callback(f'Download failed: {error_msg[:100]}...', error_msg)

        finally:
            with self.lock:
                self._cancel_flags.pop(download_id, None)
                self.active_downloads.discard(download_id)
            self.process_queue()

    def _get_download_options(self, download: dict) -> dict:
        """Configure yt-dlp options based on settings"""
        quality = download['quality']
        format_id = download['format_id']
        subtitles = download.get('subtitles', 'none')
        subtitle_langs = download.get('subtitle_langs', ['en'])

        # Use format_id if provided, otherwise use quality preset
        if format_id:
            format_string = format_id
        else:
            format_string = QUALITY_PRESETS[quality]['format']

        options = {
            'format': format_string,
            'outtmpl': str(Path(self.settings['download_dir']) / '%(title)s [%(id)s].%(ext)s'),
            'logger': logger,
            'progress': True,
            'noplaylist': True,
            **(({'ffmpeg_location': BUNDLED_FFMPEG_DIR}) if BUNDLED_FFMPEG_DIR else {}),
            'writethumbnail': True,
            'embedthumbnail': True,
            'postprocessors': [
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                }
            ],
            # Enable verbose logging to capture errors
            'verbose': True,
            # Handle errors with more details
            'ignoreerrors': False,
            # Set user agent to avoid blocking
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            # Write subtitles if requested
            'writesubtitles': subtitles != 'none',
            'writeautomaticsub': subtitles in ['auto', 'all'],
        }

        # Configure subtitle languages
        if subtitles != 'none':
            if subtitles == 'en':
                options['subtitleslangs'] = ['en']
            elif subtitles == 'zh':
                options['subtitleslangs'] = ['zh-Hans', 'zh-Hant', 'zh']
            elif subtitles == 'all':
                options['subtitleslangs'] = ['all']
            else:
                options['subtitleslangs'] = subtitle_langs

        return options

    def cancel_download(self, download_id: str):
        """Cancel a queued or active download."""
        if download_id not in self.downloads:
            return
        # Signal the progress hook to abort
        with self.lock:
            flag = self._cancel_flags.get(download_id)
        if flag:
            flag.set()
        # Remove from queue if not yet started
        with self.lock:
            if download_id in self.queue:
                self.queue.remove(download_id)
        self.downloads[download_id]['status'] = 'cancelled'
        logger.info(f"Download cancelled: {download_id}")

    def remove_download(self, download_id: str):
        """Remove a finished/cancelled/failed download from the list."""
        self.cancel_download(download_id)
        with self.lock:
            self.downloads.pop(download_id, None)

    def retry_download(self, download_id: str):
        """Re-queue a failed or cancelled download."""
        if download_id not in self.downloads:
            return
        # Cancel any active download first to avoid parallel downloads
        self.cancel_download(download_id)
        d = self.downloads[download_id].copy()
        with self.lock:
            self.downloads.pop(download_id, None)
        self.add_to_queue(d['url'], d['quality'], d.get('format_id'), d.get('subtitles', 'none'))


class YTDLPGUI(ttk.Frame):
    """Main GUI Application"""

    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.download_manager = DownloadManager(error_callback=self.on_download_error)
        self.current_theme = tk.StringVar(value=self.download_manager.settings.get('theme', 'dark'))
        self.ffmpeg_available = False

        # Apply theme
        self.apply_theme()

        # Setup UI
        self.setup_ui()

        # Check FFmpeg after UI is set up
        self.ffmpeg_available = self.check_ffmpeg()
        if not self.ffmpeg_available:
            self.master.after(500, self.show_ffmpeg_warning)

        # Start queue processor
        self.process_queue()

        # Track downloads
        self.update_ui()

    def apply_theme(self):
        """Apply dark or light theme"""
        theme = self.current_theme.get()
        if theme == 'dark':
            self.bg_color = '#2b2b2b'
            self.fg_color = '#ffffff'
            self.accent_color = '#007acc'
            self.button_fg = '#ffffff'
        else:
            self.bg_color = '#ffffff'
            self.fg_color = '#000000'
            self.accent_color = '#0066cc'
            self.button_fg = '#ffffff'

        self.master.configure(bg=self.bg_color)
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background=self.bg_color)
        style.configure('TLabel', background=self.bg_color, foreground=self.fg_color)
        style.configure('TButton', background=self.accent_color, foreground=self.button_fg)
        style.map('TButton', background=[('active', self.accent_color)])
        style.configure('TEntry', fieldbackground='#ffffff', foreground='#000000')
        style.configure('TCombobox', fieldbackground='#ffffff', foreground='#000000')
        style.configure('Treeview', background='#ffffff', foreground='#000000')
        style.configure('Treeview.Heading', background='#f0f0f0', foreground='#000000')

    def setup_ui(self):
        """Setup all UI components"""
        # Configure grid
        self.pack(fill='both', expand=True, padx=20, pady=20)
        self.configure(style='TFrame')

        # Application title
        title_font = Font(family='Segoe UI', size=24, weight='bold')
        title = ttk.Label(self, text='YT-DLP Downloader', font=title_font, style='TLabel')
        title.grid(row=0, column=0, columnspan=6, pady=(0, 20))

        # URL Section
        self.setup_url_section(1)

        # Quality Presets
        self.setup_quality_section(2)

        # Download Buttons
        self.setup_button_section(3)

        # Progress/Downloads Tree
        self.setup_downloads_section(4)

        # Statistics
        self.setup_stats_section(5)

        # Settings Button
        settings_btn = ttk.Button(self, text='⚙ Settings', command=self.open_settings)
        settings_btn.grid(row=6, column=5, pady=(10, 0), sticky='e')

        # Status Bar
        self.status_var = tk.StringVar(value='Ready')
        status_bar = ttk.Label(self, textvariable=self.status_var, style='TLabel')
        status_bar.grid(row=7, column=0, columnspan=6, pady=(10, 0), sticky='ew')

    def check_ffmpeg(self):
        """Check if FFmpeg is available (bundled or on PATH)"""
        if BUNDLED_FFMPEG_DIR:
            return True
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def show_ffmpeg_warning(self):
        """Show warning if FFmpeg is not installed"""
        if not hasattr(self, 'bg_color'):
            return

        dialog = tk.Toplevel(self.master)
        dialog.title('FFmpeg Not Found')
        dialog.geometry('500x300')
        dialog.configure(bg=self.bg_color)

        try:
            dialog.transient(self.master)
        except:
            pass

        ttk.Label(dialog, text='⚠️  FFmpeg Not Found!', font=('Segoe UI', 16, 'bold'),
                 background=self.bg_color, foreground='#ff6b6b').pack(pady=10)

        warning_text = """
FFmpeg is required for:
• Downloading videos with separate audio/video streams
• Format conversion
• Adding metadata
• Embedding thumbnails

Without FFmpeg, many downloads will fail!
"""
        ttk.Label(dialog, text=warning_text, background=self.bg_color,
                 foreground=self.fg_color, justify='left').pack(pady=10, padx=20)

        btn_frame = ttk.Frame(dialog, style='TFrame')
        btn_frame.pack(pady=10)

        def download_ffmpeg():
            import webbrowser
            webbrowser.open('https://www.ffmpeg.org/download.html')
            dialog.destroy()

        ttk.Button(btn_frame, text='Download FFmpeg', command=download_ffmpeg,
                   style='TButton').pack(side='left', padx=5)

        ttk.Button(btn_frame, text='Continue Anyway', command=dialog.destroy,
                   style='TButton').pack(side='left', padx=5)

    def setup_url_section(self, row):
        """Setup URL input section"""
        ttk.Label(self, text='Video URL:', style='TLabel').grid(row=row, column=0, sticky='w')

        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(self, textvariable=self.url_var, width=60)
        url_entry.grid(row=row, column=1, columnspan=4, sticky='ew')
        self.columnconfigure(1, weight=1)

        # Bind paste event to automatically strip and validate
        url_entry.bind('<Control-v>', lambda e: self.master.after(100, self.on_url_paste))

        # Create right-click context menu
        self.url_context_menu = tk.Menu(self, tearoff=0)
        self.url_context_menu.add_command(label='Paste', command=self.paste_from_clipboard)
        self.url_context_menu.add_command(label='Clear', command=self.clear_url)
        self.url_context_menu.add_separator()
        self.url_context_menu.add_command(label='Select All', command=lambda: url_entry.select_range(0, 'end'))

        url_entry.bind('<Button-3>', self.show_url_context_menu)

        # Format info button
        info_btn = ttk.Button(self, text='ℹ', width=2, command=self.show_url_info)
        info_btn.grid(row=row, column=5, padx=(5, 0))

        # Tooltip
        self.create_tooltip(info_btn, 'Get information about the URL')

    def show_url_context_menu(self, event):
        """Show right-click context menu for URL entry"""
        try:
            # Enable/disable paste based on clipboard content
            try:
                clipboard_content = self.clipboard_get()
                if clipboard_content:
                    self.url_context_menu.entryconfig('Paste', state='normal')
                else:
                    self.url_context_menu.entryconfig('Paste', state='disabled')
            except:
                self.url_context_menu.entryconfig('Paste', state='disabled')

            # Show the menu
            self.url_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.url_context_menu.grab_release()

    def paste_from_clipboard(self):
        """Paste from clipboard to URL entry"""
        try:
            clipboard_content = self.clipboard_get()
            if clipboard_content:
                # Clear current content and paste
                self.url_var.set('')
                self.url_var.set(clipboard_content.strip())
                self.status_var.set('URL pasted from clipboard')
        except Exception as paste_error:
            self.status_var.set(f'Failed to paste: {str(paste_error)}')

    def setup_quality_section(self, row):
        """Setup quality preset buttons"""
        ttk.Label(self, text='Quality:', style='TLabel').grid(row=row, column=0, sticky='w', pady=(10, 5))

        qualities = ['best', '4k', '1080p', '720p', '480p', 'audio']
        self.quality_var = tk.StringVar(value=self.download_manager.settings.get('default_quality', 'best'))

        frame = ttk.Frame(self, style='TFrame')
        frame.grid(row=row, column=1, columnspan=4, sticky='ew')

        for i, quality in enumerate(qualities):
            btn = ttk.Radiobutton(
                frame,
                text=QUALITY_PRESETS[quality]['name'],
                variable=self.quality_var,
                value=quality,
                style='TRadiobutton'
            )
            btn.pack(side='left', padx=(0, 15))

        # Subtitle selection
        subtitle_frame = ttk.Frame(self, style='TFrame')
        subtitle_frame.grid(row=row + 1, column=1, columnspan=4, sticky='ew', pady=(5, 0))

        ttk.Label(subtitle_frame, text='Subtitles:', style='TLabel').pack(side='left')

        self.subtitle_var = tk.StringVar(value='none')
        subtitle_combo = ttk.Combobox(
            subtitle_frame,
            textvariable=self.subtitle_var,
            values=list(SUBTITLE_LANGS.values()),
            state='readonly',
            width=15
        )
        subtitle_combo.pack(side='left', padx=(10, 20))

        # Create reverse mapping for value to key
        self.subtitle_key_from_value = {v: k for k, v in SUBTITLE_LANGS.items()}

        # Advanced options
        self.show_advanced = tk.BooleanVar(value=False)
        self.advanced_frame = ttk.Frame(self, style='TFrame')

        ttk.Checkbutton(
            self,
            text='Advanced Options ▼',
            variable=self.show_advanced,
            command=self.toggle_advanced,
            style='TCheckbutton'
        ).grid(row=row + 2, column=1, sticky='w', pady=(5, 0))

    def setup_button_section(self, row):
        """Setup action buttons"""
        btn_frame = ttk.Frame(self, style='TFrame')
        btn_frame.grid(row=row, column=0, columnspan=6, pady=(15, 10))

        # Download button
        self.download_btn = ttk.Button(
            btn_frame,
            text='📥 Download',
            command=self.start_download,
            style='TButton'
        )
        self.download_btn.pack(side='left', padx=(0, 10))

        # Queue button
        queue_btn = ttk.Button(
            btn_frame,
            text='➕ Add to Queue',
            command=lambda: self.start_download(add_to_queue=True),
            style='TButton'
        )
        queue_btn.pack(side='left', padx=(0, 10))

        # Clear button
        clear_btn = ttk.Button(
            btn_frame,
            text='🗑 Clear URL',
            command=self.clear_url,
            style='TButton'
        )
        clear_btn.pack(side='left', padx=(0, 10))

        # Open folder button
        open_btn = ttk.Button(
            btn_frame,
            text='📂 Open Folder',
            command=self.open_download_folder,
            style='TButton'
        )
        open_btn.pack(side='left')

    def setup_downloads_section(self, row):
        """Setup downloads tree view"""
        # Create frame for tree and scrollbar
        frame = ttk.Frame(self, style='TFrame')
        frame.grid(row=row, column=0, columnspan=6, sticky='nsew', pady=10)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # Treeview
        columns = ('status', 'title', 'progress', 'speed', 'eta', 'size')
        self.downloads_tree = ttk.Treeview(
            frame,
            columns=columns,
            show='headings',
            height=10
        )

        # Configure columns
        self.downloads_tree.heading('status', text='Status', anchor='w')
        self.downloads_tree.heading('title', text='Title', anchor='w')
        self.downloads_tree.heading('progress', text='Progress', anchor='w')
        self.downloads_tree.heading('speed', text='Speed', anchor='w')
        self.downloads_tree.heading('eta', text='ETA', anchor='w')
        self.downloads_tree.heading('size', text='Size', anchor='w')

        self.downloads_tree.column('status', width=80)
        self.downloads_tree.column('title', width=300)
        self.downloads_tree.column('progress', width=80)
        self.downloads_tree.column('speed', width=80)
        self.downloads_tree.column('eta', width=60)
        self.downloads_tree.column('size', width=80)

        self.downloads_tree.grid(row=0, column=0, sticky='nsew')

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.downloads_tree.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.downloads_tree.configure(yscrollcommand=scrollbar.set)
        self.downloads_tree.bind('<Button-3>', self._show_context_menu)

    def _show_context_menu(self, event):
        """Show right-click context menu for a download row."""
        row = self.downloads_tree.identify_row(event.y)
        if not row:
            return
        self.downloads_tree.selection_set(row)

        tags = self.downloads_tree.item(row, 'tags')
        download_id = tags[0] if tags else None
        if not download_id or download_id not in self.download_manager.downloads:
            return

        status = self.download_manager.downloads[download_id]['status']
        menu = tk.Menu(self, tearoff=0)

        if status in ('downloading', 'queued'):
            menu.add_command(label='Cancel', command=lambda: self._ctx_cancel(download_id))
        if status in ('failed', 'cancelled'):
            menu.add_command(label='Retry', command=lambda: self._ctx_retry(download_id))
        if status == 'completed':
            menu.add_command(label='Open File', command=lambda: self._open_file(download_id))
            menu.add_command(label='Open Folder', command=self.open_download_folder)
        menu.add_separator()
        menu.add_command(label='Delete from List', command=lambda: self._ctx_delete(download_id))

        menu.tk_popup(event.x_root, event.y_root)

    def _ctx_cancel(self, download_id: str):
        self.download_manager.cancel_download(download_id)
        self.status_var.set('Download cancelled')

    def _ctx_retry(self, download_id: str):
        self.download_manager.retry_download(download_id)
        self.status_var.set('Download re-queued')

    def _ctx_delete(self, download_id: str):
        self.download_manager.remove_download(download_id)

    def _open_file(self, download_id: str):
        path = self.download_manager.downloads.get(download_id, {}).get('file_path')
        if path and os.path.isfile(path):
            import subprocess
            import sys
            if sys.platform == 'win32':
                os.startfile(path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
        else:
            self.status_var.set('File not found')

    def setup_stats_section(self, row):
        """Setup statistics labels"""
        stats_frame = ttk.Frame(self, style='TFrame')
        stats_frame.grid(row=row, column=0, columnspan=6, pady=(5, 0))

        self.active_var = tk.StringVar(value='Active: 0')
        ttk.Label(stats_frame, textvariable=self.active_var, style='TLabel').pack(side='left')

        ttk.Label(stats_frame, text=' | ', style='TLabel').pack(side='left')

        self.queue_var = tk.StringVar(value='Queued: 0')
        ttk.Label(stats_frame, textvariable=self.queue_var, style='TLabel').pack(side='left')

        ttk.Label(stats_frame, text=' | ', style='TLabel').pack(side='left')

        self.completed_var = tk.StringVar(value='Completed: 0')
        ttk.Label(stats_frame, textvariable=self.completed_var, style='TLabel').pack(side='left')

    def create_tooltip(self, widget, text):
        """Simple tooltip implementation"""
        def show(event):
            x, y, _, _ = widget.bbox()
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25

            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")

            label = tk.Label(tooltip, text=text, background='#ffffe0', borderwidth=1, relief='solid')
            label.pack()

        def hide(event):
            for child in widget.winfo_children():
                if isinstance(child, tk.Toplevel):
                    child.destroy()

        widget.bind('<Enter>', show)
        widget.bind('<Leave>', hide)

    def on_url_paste(self):
        """Handle URL paste event"""
        # Get URL from clipboard
        try:
            url = self.clipboard_get()
            self.url_var.set(url.strip())
            self.status_var.set('URL pasted')
        except:
            pass

    def show_url_info(self):
        """Show information about the URL"""
        url = self.url_var.get().strip()
        if not url:
            self.status_var.set('Please enter a URL first')
            return

        def get_info():
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': False,
                }

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)

                self.master.after(0, lambda: self._show_url_info_dialog(info))

            except Exception as e:
                self.master.after(0, lambda: self.status_var.set(f'Failed to get info: {e}'))

        threading.Thread(target=get_info, daemon=True).start()
        self.status_var.set('Fetching URL information...')

    def _show_url_info_dialog(self, info: dict):
        """Show URL info dialog"""
        dialog = tk.Toplevel(self.master)
        dialog.title('URL Information')
        dialog.geometry('500x400')
        dialog.configure(bg=self.bg_color)

        title = info.get('title', 'Unknown')
        is_playlist = info.get('_type') == 'playlist'
        duration = info.get('duration')
        uploader = info.get('uploader')
        view_count = info.get('view_count')
        thumbnail = info.get('thumbnail')

        # Info text
        info_text = f"""
Title: {title}
Type: {'Playlist' if is_playlist else 'Video'}
Uploader: {uploader or 'Unknown'}
Duration: {self._format_duration(duration) if duration else 'Unknown'}
View Count: {view_count or 'Unknown'}
""".strip()

        text_widget = tk.Text(dialog, wrap=tk.WORD, height=10, bg=self.bg_color, fg=self.fg_color)
        text_widget.pack(padx=10, pady=10, fill='both', expand=True)
        text_widget.insert('1.0', info_text)
        text_widget.config(state='disabled')

        # If playlist, show item count
        if is_playlist:
            count = info.get('playlist_count', 0)
            ttk.Label(dialog, text=f'This playlist contains {count} videos',
                     background=self.bg_color, foreground=self.fg_color).pack(pady=10)

        # Download button
        btn_frame = ttk.Frame(dialog, style='TFrame')
        btn_frame.pack(pady=10)

        def download():
            self.quality_var.set('best')
            self.start_download()
            dialog.destroy()

        ttk.Button(btn_frame, text='Download', command=download,
                   style='TButton').pack(side='left', padx=5)

        ttk.Button(btn_frame, text='Close',
                   command=dialog.destroy, style='TButton').pack(side='left', padx=5)

    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to HH:MM:SS"""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f'{h}:{m:02d}:{s:02d}'
        return f'{m}:{s:02d}'

    def start_download(self, add_to_queue: bool = False):
        """Start or queue a download"""
        url = self.url_var.get().strip()
        if not url:
            self.status_var.set('Please enter a URL')
            return

        # Validate URL
        if not self._is_valid_url(url):
            self.status_var.set('Invalid URL')
            return

        quality = self.quality_var.get()

        if add_to_queue:
            download_id = self.download_manager.add_to_queue(url, quality)
            self.status_var.set('Added to queue')
        else:
            download_id = self.download_manager.add_to_queue(url, quality)
            self.status_var.set('Download started')

        # Clear URL field
        self.clear_url()

        # Refresh UI
        self.update_ui()

    def clear_url(self):
        """Clear URL input"""
        self.url_var.set('')

    def open_download_folder(self):
        """Open download folder in file explorer"""
        path = Path(self.download_manager.settings['download_dir'])
        if path.exists():
            webbrowser.open(str(path))
        else:
            self.status_var.set('Download folder does not exist')

    def on_download_error(self, status_msg: str, error_details: str):
        """Handle download errors from DownloadManager"""
        # Show error in status bar
        self.status_var.set(status_msg)

        # Show error dialog
        self.show_error_dialog('Download Error', error_details)

    def show_error_dialog(self, title: str, error_msg: str):
        """Show detailed error dialog"""
        dialog = tk.Toplevel(self.master)
        dialog.title(title)
        dialog.geometry('600x400')
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.master)

        # Title
        ttk.Label(dialog, text=title, font=('Segoe UI', 14, 'bold'),
                 background=self.bg_color, foreground=self.fg_color).pack(pady=10)

        # Error message in scrolled text
        frame = ttk.Frame(dialog, style='TFrame')
        frame.pack(fill='both', expand=True, padx=10, pady=5)

        text_widget = tk.Text(
            frame,
            wrap=tk.WORD,
            bg='#f8f9fa' if self.current_theme.get() == 'light' else '#2b2b2b',
            fg=self.fg_color,
            relief='solid',
            borderwidth=1
        )
        text_widget.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget.configure(yscrollcommand=scrollbar.set)

        # Insert error message
        text_widget.insert('1.0', error_msg)
        text_widget.config(state='disabled')

        # Common solutions
        solutions = """
Common Solutions:
1. Check your internet connection
2. Try a lower quality preset
3. Update yt-dlp: pip install yt-dlp --upgrade
4. The video might be blocked/region-restricted
5. Some sites require login/cookies

Full log available in: ytdlp_gui.log
"""
        ttk.Label(dialog, text=solutions, background=self.bg_color,
                 foreground=self.fg_color, justify='left').pack(pady=10, padx=10)

        # Buttons
        btn_frame = ttk.Frame(dialog, style='TFrame')
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text='OK', command=dialog.destroy,
                   style='TButton').pack(side='left', padx=5)

        def copy_error():
            dialog.clipboard_clear()
            dialog.clipboard_append(error_msg)
            dialog.update()

        ttk.Button(btn_frame, text='Copy Error', command=copy_error,
                   style='TButton').pack(side='left', padx=5)

        # Focus on dialog
        dialog.focus_set()

    def toggle_advanced(self):
        """Show/hide advanced options"""
        if not hasattr(self, 'advanced_frame'):
            self.advanced_frame = ttk.Frame(self, style='TFrame')

        if self.show_advanced.get():
            self.advanced_frame.grid(row=8, column=0, columnspan=6, sticky='ew', pady=10)
            self.setup_advanced_options()
        else:
            self.advanced_frame.grid_forget()

    def setup_advanced_options(self):
        """Setup advanced download options"""
        # Clear existing widgets
        for widget in self.advanced_frame.winfo_children():
            widget.destroy()

        # Add proxy settings
        proxy_frame = ttk.LabelFrame(self.advanced_frame, text='Proxy Settings', style='TLabelframe')
        proxy_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(proxy_frame, text='Proxy URL:', style='TLabel').pack(side='left')
        self.proxy_var = tk.StringVar(value=self.download_manager.settings.get('proxy_url', ''))
        proxy_entry = ttk.Entry(proxy_frame, textvariable=self.proxy_var, width=40)
        proxy_entry.pack(side='left', padx=10, expand=True)

        # Add format selection
        format_frame = ttk.LabelFrame(self.advanced_frame, text='Format Selection', style='TLabelframe')
        format_frame.pack(fill='x', padx=5, pady=5)

        self.format_var = tk.StringVar()
        format_entry = ttk.Entry(format_frame, textvariable=self.format_var, width=30)
        format_entry.pack(side='left', padx=10)

        ttk.Button(
            format_frame,
            text='View Available Formats',
            command=self.show_format_dialog,
            style='TButton'
        ).pack(side='left', padx=5)

    def show_format_dialog(self):
        """Show format selection dialog"""
        url = self.url_var.get().strip()
        if not url:
            self.status_var.set('Please enter a URL first')
            return

        dialog = tk.Toplevel(self.master)
        dialog.title('Available Formats')
        dialog.geometry('700x500')
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.master)

        ttk.Label(dialog, text='Available Formats', font=('Segoe UI', 14, 'bold'),
                 background=self.bg_color, foreground=self.fg_color).pack(pady=10)

        # Format list
        tree_frame = ttk.Frame(dialog, style='TFrame')
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

        columns = ('format_id', 'ext', 'resolution', 'filesize', 'vcodec', 'acodec', 'tbr')
        format_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)

        for col in columns:
            format_tree.heading(col, text=col.replace('_', ' ').title())
            if col in ['format_id', 'ext']:
                format_tree.column(col, width=80)
            elif col == 'resolution':
                format_tree.column(col, width=120)
            elif col == 'filesize':
                format_tree.column(col, width=100)
            else:
                format_tree.column(col, width=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=format_tree.yview)
        format_tree.configure(yscrollcommand=scrollbar.set)

        format_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')

        def get_formats():
            try:
                with YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    formats = info.get('formats', [])

                    # Clear existing items
                    # Clear existing items safely
                    children = format_tree.get_children()
                    if children:
                        for item in children:
                            format_tree.delete(item)

                    for fmt in formats:
                        size = fmt.get('filesize') or fmt.get('filesize_approx')
                        if size:
                            # Format size in MB
                            size_text = f"{size / 1024 / 1024:.1f} MB"
                        else:
                            size_text = 'N/A'

                        format_tree.insert('', 'end', values=(
                            fmt.get('format_id', 'N/A'),
                            fmt.get('ext', 'N/A'),
                            fmt.get('resolution', 'audio only' if fmt.get('acodec') != 'none' else 'video only'),
                            size_text,
                            fmt.get('vcodec', 'N/A'),
                            fmt.get('acodec', 'N/A'),
                            f"{fmt.get('tbr', 0):.0f}k"
                        ))

                    if not formats:
                        format_tree.insert('', 'end', values=('No formats available', '', '', '', '', '', ''))

            except Exception as e:
                format_tree.insert('', 'end', values=(f'Error: {str(e)}', '', '', '', '', '', ''))

        # Load formats in background
        threading.Thread(target=get_formats, daemon=True).start()

        # Selection and buttons
        btn_frame = ttk.Frame(dialog, style='TFrame')
        btn_frame.pack(pady=10)

        ttk.Label(btn_frame, text='Selected Format ID:', style='TLabel').pack(side='left')
        selected_format = tk.StringVar()
        format_entry = ttk.Entry(btn_frame, textvariable=selected_format, width=15)
        format_entry.pack(side='left', padx=10)

        def on_select(event):
            # Get the selection
            selected_items = format_tree.selection()
            if selected_items and len(selected_items) > 0:
                values = format_tree.item(selected_items[0])['values']
                if values and len(values) > 0:
                    selected_format.set(str(values[0]))

        format_tree.bind('<<TreeviewSelect>>', on_select)

        def use_selected():
            self.format_var.set(selected_format.get())
            dialog.destroy()

        ttk.Button(btn_frame, text='Use This Format', command=use_selected, style='TButton').pack(side='left', padx=10)
        ttk.Button(btn_frame, text='Close', command=dialog.destroy, style='TButton').pack(side='left')

    def open_settings(self):
        """Open settings dialog"""
        dialog = tk.Toplevel(self.master)
        dialog.title('Settings')
        dialog.geometry('500x400')
        dialog.configure(bg=self.bg_color)
        dialog.transient(self.master)

        ttk.Label(dialog, text='Settings', font=('Segoe UI', 16, 'bold'),
                 background=self.bg_color, foreground=self.fg_color).pack(pady=10)

        # Download directory
        dir_frame = ttk.Frame(dialog, style='TFrame')
        dir_frame.pack(fill='x', padx=20, pady=10)

        ttk.Label(dir_frame, text='Download Directory:',
                 background=self.bg_color, foreground=self.fg_color).pack(side='left')

        dir_var = tk.StringVar(value=self.download_manager.settings['download_dir'])
        dir_entry = ttk.Entry(dir_frame, textvariable=dir_var, width=40)
        dir_entry.pack(side='left', padx=(10, 5))

        def browse():
            from tkinter import filedialog
            folder = filedialog.askdirectory(initialdir=dir_var.get())
            if folder:
                dir_var.set(folder)

        ttk.Button(dir_frame, text='Browse', command=browse, style='TButton').pack(side='left')

        # Max concurrent downloads
        concurrent_frame = ttk.Frame(dialog, style='TFrame')
        concurrent_frame.pack(fill='x', padx=20, pady=10)

        ttk.Label(concurrent_frame, text='Max Concurrent Downloads:',
                 background=self.bg_color, foreground=self.fg_color).pack(side='left')

        concurrent_var = tk.IntVar(value=self.download_manager.settings['max_concurrent'])
        concurrent_spin = ttk.Spinbox(concurrent_frame, from_=1, to=10, textvariable=concurrent_var, width=5)
        concurrent_spin.pack(side='left', padx=10)

        # Theme
        theme_frame = ttk.Frame(dialog, style='TFrame')
        theme_frame.pack(fill='x', padx=20, pady=10)

        ttk.Label(theme_frame, text='Theme:',
                 background=self.bg_color, foreground=self.fg_color).pack(side='left')

        theme_combo = ttk.Combobox(theme_frame, textvariable=self.current_theme,
                                   values=['light', 'dark'], state='readonly')
        theme_combo.pack(side='left', padx=10)

        # Buttons
        btn_frame = ttk.Frame(dialog, style='TFrame')
        btn_frame.pack(pady=20)

        def save():
            self.download_manager.settings['download_dir'] = dir_var.get()
            self.download_manager.settings['max_concurrent'] = concurrent_var.get()
            self.download_manager.settings['theme'] = self.current_theme.get()
            self.download_manager.save_settings()
            self.apply_theme()
            dialog.destroy()
            self.status_var.set('Settings saved')

        ttk.Button(btn_frame, text='Save', command=save, style='TButton').pack(side='left', padx=5)
        ttk.Button(btn_frame, text='Cancel', command=dialog.destroy, style='TButton').pack(side='left', padx=5)

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        pattern = re.compile(
            r'^https?://(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)$'
        )
        return bool(pattern.match(url))

    def process_queue(self):
        """Process download queue"""
        self.download_manager.process_queue()
        self.master.after(1000, self.process_queue)

    def update_ui(self):
        """Update UI elements"""
        # Update downloads tree
        self._update_downloads_tree()

        # Update statistics
        self._update_statistics()

        # Schedule next update
        self.master.after(1000, self.update_ui)

    def _update_downloads_tree(self):
        """Update downloads tree view"""
        # Clear existing items
        for item in self.downloads_tree.get_children():
            self.downloads_tree.delete(item)

        # Add downloads
        for download_id, download in self.download_manager.downloads.items():
            status = download['status']
            progress = download.get('progress', 0)

            if isinstance(progress, str) and '%' in progress:
                progress = progress.strip('%')

            progress = f"{progress}%"

            values = (
                status.upper(),
                download.get('title', 'Unknown'),
                progress,
                download.get('speed', ''),
                download.get('eta', ''),
                self._format_size(download.get('file_size'))
            )

            tag = status
            self.downloads_tree.insert('', 'end', values=values, tags=(download_id, tag))

        # Configure row colors
        self.downloads_tree.tag_configure('completed', background='#d4edda')
        self.downloads_tree.tag_configure('failed', background='#f8d7da')
        self.downloads_tree.tag_configure('downloading', background='#fff3cd')

    def _update_statistics(self):
        """Update statistics labels"""
        active = len(self.download_manager.active_downloads)
        queued = len(self.download_manager.queue)
        completed = sum(1 for d in self.download_manager.downloads.values()
                       if d['status'] == 'completed')

        self.active_var.set(f'Active: {active}')
        self.queue_var.set(f'Queued: {queued}')
        self.completed_var.set(f'Completed: {completed}')

    def _format_size(self, bytes_size: Optional[int]) -> str:
        """Format bytes to human readable size"""
        if not bytes_size:
            return ''

        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0

        return f"{bytes_size:.1f} TB"


def main(initial_url: Optional[str] = None):
    """Main application entry point"""
    # Setup root window
    root = tk.Tk()
    root.title('YT-DLP Downloader')
    root.geometry('900x650')

    # Set icon if available
    try:
        root.iconbitmap('ytdlp_icon.ico')
    except:
        pass

    # Create main application
    app = YTDLPGUI(master=root)
    app.pack(fill='both', expand=True)

    # Set initial URL if provided
    if initial_url:
        app.url_var.set(initial_url)

    # Center window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    # Handle window close
    def on_closing():
        if hasattr(app, 'minimize_to_tray') and app.minimize_to_tray:
            root.withdraw()
        else:
            root.destroy()

    root.protocol('WM_DELETE_WINDOW', on_closing)

    # Start main loop
    root.mainloop()


if __name__ == '__main__':
    main()
