# 剩余任务计划（Tasks 4–6）

> 已完成：Task 1（取消下载）、Task 2（右键菜单）、Task 3（历史记录持久化）
> 
> 最新提交：`af49b64` feat: history persistence
>
> 所有改动只涉及一个文件：`ytdlp_gui.py`

---

## 当前状态总结

| 任务 | 状态 | 提交 |
|------|------|------|
| Task 1: 真正取消下载 (threading.Event) | ✅ 完成 | `95770ba`, `f58c0a6` |
| Task 2: 右键上下文菜单 | ✅ 完成 | `8ddebc5`, `8841982`, `88e0fb7`, `07429a1` |
| Task 3: 历史记录持久化 | ✅ 完成 | `af49b64` |
| Task 4: Windows 完成通知 | ⏳ 待实现 | — |
| Task 5: Unicode 进度条 | ⏳ 待实现 | — |
| Task 6: 限速设置 | ⏳ 待实现 | — |

---

## Task 4 — Windows 完成通知

**目标：** 下载完成时弹出 Windows toast 通知（右下角系统通知）。

**原理：** 用 `subprocess` 调用 PowerShell 一行命令触发 `Windows.UI.Notifications`，无需额外库，打包进 exe 后同样有效。非 Windows 系统静默忽略。

**只改 `ytdlp_gui.py`。**

### Step 1：在 `YTDLPGUI` 中添加 `_notify` 静态方法

在 `YTDLPGUI` 类内任意位置添加（建议放在 `_open_file` 之后）：

```python
@staticmethod
def _notify(title: str, message: str):
    """Show a Windows toast notification (fire-and-forget)."""
    try:
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
        pass  # 通知是尽力而为，绝不让它崩溃应用
```

注意：`subprocess` 已在文件顶部 import，无需再加。

### Step 2：在 `download_video` 下载完成后调用 `_notify`

在 `download_video` 方法里找到：

```python
download['status'] = 'completed'
self.save_history()
```

在 `self.save_history()` 之后加：

```python
title = download.get('title', 'Unknown') or 'Unknown'
if self.master:
    self.master.after(0, lambda t=title: YTDLPGUI._notify('Download Complete', t))
```

> `self.master` 是 Tkinter 根窗口的引用。`after(0, ...)` 确保在主线程执行。`YTDLPGUI` 是类名，可直接用（不需要 self）。

### Step 3：提交

```bash
git add ytdlp_gui.py
git commit -m "feat: Windows toast notification on download complete"
git push
```

### 手动测试

在 Windows 上下载一个短视频，完成后右下角应弹出系统通知。非 Windows 系统：无通知，不报错。

---

## Task 5 — Unicode 进度条

**目标：** 把下载列表 Progress 列的 `45%` 改为 `████░░░░ 45%`。

**只改 `ytdlp_gui.py`，只改一处。**

### Step 1：在模块级别添加 `_progress_bar` 辅助函数

找到文件顶部 `BUNDLED_FFMPEG_DIR = _find_bundled_ffmpeg()` 这行，在它之后添加：

```python
def _progress_bar(pct: float, width: int = 8) -> str:
    """Return a Unicode block progress bar, e.g. '████░░░░ 45%'"""
    filled = round(pct / 100 * width)
    return '█' * filled + '░' * (width - filled) + f' {pct:.0f}%'
```

### Step 2：在 `_update_downloads_tree` 中使用该函数

找到 `_update_downloads_tree` 方法（约第 1260 行）。找到构建 `values` 元组的地方，其中 `progress` 变量被格式化为字符串。

找到类似这样的代码：
```python
progress = f"{progress}%"
```
或者直接在 `values` 里用 `progress` 的地方，替换为：

```python
try:
    progress = _progress_bar(float(progress))
except (ValueError, TypeError):
    progress = str(progress)
```

> 如果 `progress` 已经是 `'45.3'` 这样的字符串（来自 yt_dlp），`float()` 转换会成功。如果是 `'N/A'` 或 `None` 等，fallback 到 `str(progress)`。

### Step 3：提交

```bash
git add ytdlp_gui.py
git commit -m "feat: visual unicode progress bar in download list"
git push
```

### 手动测试

开始下载，观察列表 Progress 列应显示 `████░░░░ 45%` 并实时更新。

---

## Task 6 — 限速设置

**目标：** 用户可在设置里填写最大下载速度（KB/s），0 表示不限速。

**只改 `ytdlp_gui.py`，改三处。**

### Step 1：在 `DEFAULT_SETTINGS` 中添加 `speed_limit_kb`

找到 `DEFAULT_SETTINGS` 字典（约第 50 行附近），添加一行：

```python
DEFAULT_SETTINGS = {
    'download_dir': str(Path.home() / 'Downloads'),
    'max_concurrent': 3,
    'default_quality': 'best',
    'theme': 'dark',
    'speed_limit_kb': 0,   # 0 = unlimited
}
```

### Step 2：在设置对话框中添加限速输入框

找到 `open_settings` 方法。在 `concurrent_frame` 块之后、`theme_frame` 块之前，插入：

```python
speed_frame = ttk.Frame(dialog, style='TFrame')
speed_frame.pack(fill='x', padx=20, pady=10)

ttk.Label(speed_frame, text='Speed Limit (KB/s, 0 = unlimited):',
         background=self.bg_color, foreground=self.fg_color).pack(side='left')

speed_var = tk.IntVar(value=self.download_manager.settings.get('speed_limit_kb', 0))
ttk.Spinbox(speed_frame, from_=0, to=100000, textvariable=speed_var, width=8).pack(side='left', padx=10)
```

在同一个 `open_settings` 方法内找到 `save()` 内部函数，添加：

```python
self.download_manager.settings['speed_limit_kb'] = speed_var.get()
```

> 确保这行在 `self.download_manager.save_settings()` 调用之前，这样新值会被持久化。

### Step 3：在 `_get_download_options` 中传给 yt_dlp

找到 `_get_download_options` 方法（在 `DownloadManager` 中）。找到 `ffmpeg_location` 那一行（类似 `**(({'ffmpeg_location': BUNDLED_FFMPEG_DIR}) if BUNDLED_FFMPEG_DIR else {}),`），在它之后添加：

```python
speed_kb = self.settings.get('speed_limit_kb', 0)
if speed_kb and speed_kb > 0:
    options['ratelimit'] = speed_kb * 1024  # yt_dlp 期望 bytes/s
```

> 注意：`_get_download_options` 构建 `options` 字典，`ratelimit` 是 yt_dlp 的标准选项，单位是 bytes/s。

### Step 4：提交

```bash
git add ytdlp_gui.py
git commit -m "feat: speed limit setting"
git push
```

### 手动测试

打开设置，填入 200（KB/s），保存。下载时观察列表中的速度显示不超过约 200 KB/s。

---

## 完成所有任务后

推送到 GitHub 触发自动构建：

```bash
git push
```

GitHub Actions 会在 `windows-latest` 上构建 `dist/YT-DLP-GUI.exe` 并自动发布到 Release `latest`。

下载链接：`https://github.com/HaipingShi/ytdlp-lh/releases/latest`

---

## 快速参考：改动位置

| Task | 方法/位置 | 改动内容 |
|------|-----------|---------|
| 4 | `YTDLPGUI._notify` (新方法) | PowerShell toast 通知 |
| 4 | `DownloadManager.download_video` | completed 后调用 `_notify` |
| 5 | 模块级 `_progress_bar` (新函数) | Unicode 进度条生成器 |
| 5 | `YTDLPGUI._update_downloads_tree` | 用 `_progress_bar` 格式化 progress |
| 6 | `DEFAULT_SETTINGS` | 加 `speed_limit_kb: 0` |
| 6 | `YTDLPGUI.open_settings` | 加限速输入框和 save() 里保存 |
| 6 | `DownloadManager._get_download_options` | 传 `ratelimit` 给 yt_dlp |
