# Missing Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add right-click menu (cancel/delete/retry/open file), history persistence, download complete notification, visual progress bar, and speed limit to the existing YT-DLP GUI.

**Architecture:** All five features touch only `ytdlp_gui.py`. `DownloadManager` owns data/logic; `YTDLPGUI` owns UI. Each task is self-contained and testable by running the app manually.

**Tech Stack:** Python 3.13, tkinter, yt_dlp, threading.Event for cancellation, JSON for history, ctypes for Windows toast notification.

---

## File map

| File | Changes |
|------|---------|
| `ytdlp_gui.py` | All changes — five features added incrementally |

---

## Task 1 — Real cancellation in DownloadManager

**Goal:** Allow actively-downloading tasks to be stopped mid-download.

**How it works:** Store a `threading.Event` per download ID. The `progress_hook` checks the event on every progress tick and raises `Exception("cancelled")` if it is set. `cancel_download()` sets the event.

**Files:**
- Modify: `ytdlp_gui.py` — `DownloadManager.__init__`, `cancel_download`, `download_video`

- [ ] **Step 1: Add `_cancel_flags` dict to `__init__`**

In `DownloadManager.__init__` (around line 99), add one line after `self.lock = threading.Lock()`:

```python
self._cancel_flags: Dict[str, threading.Event] = {}
```

- [ ] **Step 2: Replace `cancel_download` with a working implementation**

Find and replace the entire `cancel_download` method (lines 311–321):

```python
def cancel_download(self, download_id: str):
    """Cancel a queued or active download."""
    if download_id not in self.downloads:
        return
    # Signal the progress hook to abort
    if download_id in self._cancel_flags:
        self._cancel_flags[download_id].set()
    # Remove from queue if not yet started
    with self.lock:
        if download_id in self.queue:
            self.queue.remove(download_id)
    self.downloads[download_id]['status'] = 'cancelled'
    logger.info(f"Download cancelled: {download_id}")
```

- [ ] **Step 3: Create the cancel flag before each download starts and check it in `progress_hook`**

In `download_video` (around line 185), add flag creation right after `download = self.downloads[download_id]`:

```python
cancel_flag = threading.Event()
self._cancel_flags[download_id] = cancel_flag
```

Inside `progress_hook`, add the cancel check as the very first line:

```python
def progress_hook(d):
    if cancel_flag.is_set():
        raise Exception("Download cancelled by user")
    if d['status'] == 'downloading':
        ...  # existing code unchanged
```

- [ ] **Step 4: Clean up the flag in `finally`**

In the `finally` block (around line 264), add:

```python
finally:
    self._cancel_flags.pop(download_id, None)
    with self.lock:
        self.active_downloads.discard(download_id)
    self.process_queue()
```

- [ ] **Step 5: Add `remove_download` and `retry_download` helper methods** (needed by Task 2)

Add after `cancel_download`:

```python
def remove_download(self, download_id: str):
    """Remove a finished/cancelled/failed download from the list."""
    self.cancel_download(download_id)
    with self.lock:
        self.downloads.pop(download_id, None)

def retry_download(self, download_id: str):
    """Re-queue a failed or cancelled download."""
    if download_id not in self.downloads:
        return
    d = self.downloads[download_id]
    self.downloads.pop(download_id, None)
    self.add_to_queue(d['url'], d['quality'], d.get('format_id'), d.get('subtitles', 'none'))
```

- [ ] **Step 6: Manual test**

Run the app, start a download, immediately click Download again on a second URL to fill the queue. Verify both are tracked. We'll wire up the cancel button in Task 2.

---

## Task 2 — Right-click context menu

**Goal:** Right-clicking any row in the downloads list shows a context menu with actions appropriate to the row's status.

**Files:**
- Modify: `ytdlp_gui.py` — `setup_downloads_section`, new `_show_context_menu`, `_open_file` methods

- [ ] **Step 1: Bind right-click on `downloads_tree` inside `setup_downloads_section`**

After `self.downloads_tree.configure(yscrollcommand=scrollbar.set)` (last line of that method), add:

```python
self.downloads_tree.bind('<Button-3>', self._show_context_menu)
```

- [ ] **Step 2: Add `_show_context_menu` method to `YTDLPGUI`**

Add after `setup_downloads_section`:

```python
def _show_context_menu(self, event):
    """Show right-click context menu for a download row."""
    row = self.downloads_tree.identify_row(event.y)
    if not row:
        return
    self.downloads_tree.selection_set(row)

    # The row iid is the download_id stored during tree refresh
    download_id = self.downloads_tree.item(row, 'tags')[0] if self.downloads_tree.item(row, 'tags') else None
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
        os.startfile(path)
    else:
        self.status_var.set('File not found')
```

- [ ] **Step 3: Tag each tree row with its `download_id` during refresh**

In `_update_downloads_tree` (around line 1180+), find the `self.downloads_tree.insert(...)` call and add `tags=(download_id,)`:

```python
self.downloads_tree.insert('', 'end', values=values, tags=(download_id,))
```

Note: this replaces the existing `tags=(tag,)` — store the download_id as the first tag and the status-color tag separately:

```python
self.downloads_tree.insert('', 'end', values=values, tags=(download_id, tag))
```

The existing `tag_configure` calls on `'completed'`, `'failed'`, `'downloading'` use the *last* matching tag. Tkinter applies all matching tag styles, so both tags coexist safely.

- [ ] **Step 4: Manual test**

Run the app. Right-click a queued item → Cancel should appear. Right-click a completed item → Open File and Delete should appear. Right-click failed item → Retry and Delete should appear.

---

## Task 3 — History persistence

**Goal:** Completed and failed downloads survive app restarts. Stored in `~/.ytdlp_gui/history.json`.

**Files:**
- Modify: `ytdlp_gui.py` — `DownloadManager.__init__`, new `load_history` / `save_history`, `download_video` (call save on completion/failure), `YTDLPGUI.setup_button_section` (Clear History button)

- [ ] **Step 1: Add `load_history` to `DownloadManager`**

Add after `save_settings`:

```python
def load_history(self):
    """Load persisted download history from disk."""
    history_path = Path.home() / '.ytdlp_gui' / 'history.json'
    if not history_path.exists():
        return
    try:
        with open(history_path) as f:
            history = json.load(f)
        for item in history:
            # Restore only finished entries; skip if already in downloads
            if item.get('id') and item['id'] not in self.downloads:
                self.downloads[item['id']] = item
    except Exception as e:
        logger.warning(f"Failed to load history: {e}")

def save_history(self):
    """Persist completed/failed downloads to disk."""
    history_path = Path.home() / '.ytdlp_gui' / 'history.json'
    history_path.parent.mkdir(exist_ok=True)
    finished = [
        d for d in self.downloads.values()
        if d['status'] in ('completed', 'failed', 'cancelled')
    ]
    # Keep only the 200 most recent entries
    finished.sort(key=lambda d: d.get('completed_at') or d.get('started_at') or datetime.min, reverse=True)
    finished = finished[:200]
    # datetime objects aren't JSON-serialisable — convert to ISO strings
    def serialise(d):
        out = {}
        for k, v in d.items():
            out[k] = v.isoformat() if isinstance(v, datetime) else v
        return out
    try:
        with open(history_path, 'w') as f:
            json.dump([serialise(d) for d in finished], f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save history: {e}")
```

- [ ] **Step 2: Call `load_history` in `__init__`**

At the end of `DownloadManager.__init__`, add:

```python
self.load_history()
```

- [ ] **Step 3: Call `save_history` after each download finishes**

In `download_video`, after `download['status'] = 'completed'` and after `download['status'] = 'failed'`, add in both places:

```python
self.save_history()
```

- [ ] **Step 4: Add "Clear History" button to the UI**

In `setup_button_section`, after the Open Folder button:

```python
ttk.Button(
    btn_frame,
    text='🗑 Clear History',
    command=self._clear_history,
    style='TButton'
).pack(side='left', padx=(10, 0))
```

Add the method to `YTDLPGUI`:

```python
def _clear_history(self):
    """Remove all completed/failed entries from the list and history file."""
    to_remove = [
        did for did, d in self.download_manager.downloads.items()
        if d['status'] in ('completed', 'failed', 'cancelled')
    ]
    for did in to_remove:
        self.download_manager.downloads.pop(did, None)
    history_path = Path.home() / '.ytdlp_gui' / 'history.json'
    if history_path.exists():
        history_path.unlink()
    self.status_var.set(f'Cleared {len(to_remove)} history entries')
```

- [ ] **Step 5: Manual test**

Download a video. Close the app. Reopen — the completed entry should still appear in the list.

---

## Task 4 — Download complete notification

**Goal:** A Windows toast notification pops up when any download finishes.

**How:** Use `ctypes` to call `Windows.UI.Notifications` via PowerShell — no extra library needed and it works in a bundled exe.

**Files:**
- Modify: `ytdlp_gui.py` — new `_notify` method on `YTDLPGUI`, called from `download_video` via the existing `error_callback` pattern

- [ ] **Step 1: Add `_notify` static method to `YTDLPGUI`**

Add anywhere in `YTDLPGUI`:

```python
@staticmethod
def _notify(title: str, message: str):
    """Show a Windows toast notification (fire-and-forget)."""
    try:
        import subprocess
        # PowerShell one-liner — works on Windows 10/11, silent on failure
        script = (
            f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
            f"ContentType=WindowsRuntime] | Out-Null; "
            f"$t = [Windows.UI.Notifications.ToastTemplateType]::ToastText02; "
            f"$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($t); "
            f"$x.GetElementsByTagName('text')[0].AppendChild($x.CreateTextNode('{title}')) | Out-Null; "
            f"$x.GetElementsByTagName('text')[1].AppendChild($x.CreateTextNode('{message[:80]}')) | Out-Null; "
            f"$n = [Windows.UI.Notifications.ToastNotification]::new($x); "
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('YT-DLP GUI').Show($n)"
        )
        subprocess.Popen(
            ['powershell', '-WindowStyle', 'Hidden', '-Command', script],
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
    except Exception:
        pass  # Notifications are best-effort; never crash the app
```

- [ ] **Step 2: Call `_notify` when a download completes**

In `download_video`, after `download['status'] = 'completed'`, add:

```python
title = download.get('title', 'Unknown') or 'Unknown'
self.master.after(0, lambda t=title: YTDLPGUI._notify('Download Complete', t))
```

- [ ] **Step 3: Manual test**

Start a short download. When it finishes a Windows toast should appear in the bottom-right corner. (On non-Windows or in VM the call silently does nothing.)

---

## Task 5 — Visual progress bar in the download list

**Goal:** Replace the raw `45%` text in the Progress column with a Unicode bar like `████░░░░ 45%`.

**Files:**
- Modify: `ytdlp_gui.py` — `_update_downloads_tree` only

- [ ] **Step 1: Add a helper function at module level**

After `BUNDLED_FFMPEG_DIR = _find_bundled_ffmpeg()`, add:

```python
def _progress_bar(pct: float, width: int = 8) -> str:
    """Return a Unicode block progress bar, e.g. '████░░░░ 45%'"""
    filled = round(pct / 100 * width)
    return '█' * filled + '░' * (width - filled) + f' {pct:.0f}%'
```

- [ ] **Step 2: Use the helper in `_update_downloads_tree`**

Find where `progress` is formatted (the lines that build `values`). Replace:

```python
progress = f"{progress}%"
```

with:

```python
try:
    progress = _progress_bar(float(progress))
except (ValueError, TypeError):
    progress = str(progress)
```

- [ ] **Step 3: Manual test**

Start a download and watch the Progress column — it should show `████░░░░ 45%` updating in real time.

---

## Task 6 — Speed limit setting

**Goal:** Let users cap download speed (KB/s) to avoid saturating their connection.

**Files:**
- Modify: `ytdlp_gui.py` — `DEFAULT_SETTINGS`, `open_settings` dialog, `_get_download_options`

- [ ] **Step 1: Add `speed_limit_kb` to `DEFAULT_SETTINGS`**

```python
DEFAULT_SETTINGS = {
    'download_dir': str(Path.home() / 'Downloads'),
    'max_concurrent': 3,
    'default_quality': 'best',
    'theme': 'dark',
    'speed_limit_kb': 0,   # 0 = unlimited
}
```

- [ ] **Step 2: Add speed limit field to the Settings dialog**

In `open_settings`, after the `concurrent_frame` block and before the `theme_frame` block, add:

```python
speed_frame = ttk.Frame(dialog, style='TFrame')
speed_frame.pack(fill='x', padx=20, pady=10)

ttk.Label(speed_frame, text='Speed Limit (KB/s, 0 = unlimited):',
         background=self.bg_color, foreground=self.fg_color).pack(side='left')

speed_var = tk.IntVar(value=self.download_manager.settings.get('speed_limit_kb', 0))
ttk.Spinbox(speed_frame, from_=0, to=100000, textvariable=speed_var, width=8).pack(side='left', padx=10)
```

In the `save()` function inside `open_settings`, add:

```python
self.download_manager.settings['speed_limit_kb'] = speed_var.get()
```

- [ ] **Step 3: Pass the limit to yt_dlp in `_get_download_options`**

In `_get_download_options`, after the `**(({'ffmpeg_location': ...}))` line, add:

```python
speed_kb = self.settings.get('speed_limit_kb', 0)
if speed_kb and speed_kb > 0:
    options['ratelimit'] = speed_kb * 1024  # yt_dlp expects bytes/s
```

- [ ] **Step 4: Manual test**

Open Settings, set Speed Limit to 200 KB/s, save. Start a download — speed shown in the list should not exceed ~200 KB/s.

---

## Commit strategy

After each task passes its manual test:

```bash
git add ytdlp_gui.py
git commit -m "feat: <task description>"
git push   # triggers GitHub Actions rebuild
```

Task descriptions:
- Task 1: `feat: real download cancellation via threading.Event`
- Task 2: `feat: right-click context menu (cancel/retry/delete/open file)`
- Task 3: `feat: history persistence across restarts`
- Task 4: `feat: Windows toast notification on download complete`
- Task 5: `feat: visual unicode progress bar in download list`
- Task 6: `feat: speed limit setting`
