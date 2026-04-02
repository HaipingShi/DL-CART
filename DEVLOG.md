# 开发日志 2026-04-02

## 目标

将 `ytdlp_gui.py`（Python Tkinter 应用）打包为 Windows 用户可直接双击运行的 `.exe` 文件。

---

## 最终方案

**两个文件，一键构建：**

```
ytdlp_gui.py   ← 应用源码
build.bat      ← 双击构建，产出 dist\DLCart.exe
```

`build.bat` 核心命令：
```bat
python -m pip install pyinstaller yt-dlp
python -m PyInstaller --onefile --windowed --collect-all yt_dlp --name DLCart ytdlp_gui.py
```

产出的 `DLCart.exe` 内嵌 Python + yt_dlp，用户无需安装任何依赖，双击即用。

---

## 错误记录与解决过程

### 错误 1：批处理文件乱码崩溃

**现象：**
```
'辫触锛佽鏌ョ湅涓婃柟鐨勯敊璇俊鎭?' 不是内部或外部命令
'娉ㄦ剰锛氭病鏈?FFmpeg' 不是内部或外部命令
```

**原因：** `.bat` 文件在 macOS 上以 UTF-8 编码写入，Windows cmd 默认 GBK，中文字符和 Unicode 符号（`╔ ║ ✓ ❌ ⚠️`）全部乱码，被当作命令执行。

**解决：** 批处理文件改为纯 ASCII 英文，去掉所有中文和 Unicode 符号。

---

### 错误 2：`--collect-all` 与 `.spec` 文件冲突

**现象：**
```
option(s) not allowed:
  --collect-all
makespec options not valid when a .spec file is given
```

**原因：** `--collect-all` 是生成 spec 时的选项，指定 `.spec` 文件后不能再传。

**解决：** 去掉 spec 文件，直接用命令行参数 `--collect-all yt_dlp`。

---

### 错误 3：Inno Setup 编译失败（无日志、静默退出）

**现象：** 构建脚本运行后直接退出，找不到生成的安装包，也没有错误信息。

**原因（两处）：**
1. `installer.iss` 引用了不存在的 `LICENSE` 文件，Inno Setup 报错退出
2. `if` 块内使用 `%errorlevel%`，需改为 `!errorlevel!`（延迟展开），否则捕获的值不对

**解决：**
- `installer.iss` 加 `skipifsourcedoesntexist` 标志
- 批处理改用 `!errorlevel!`，并将全程输出写入 `build.log`

---

### 错误 4：`tee` 不是 Windows 命令

**现象：** 批处理第一行 `call :main 2>&1 | tee "%LOG%"` 直接失败，脚本跳到 `goto :eof` 退出，窗口闪退，没有 `pause`。

**原因：** `tee` 是 Unix 命令，Windows 标准环境中不存在。即使安装了 Git for Windows，管道子进程中的 `pause` 也无法等待用户按键。

**解决：** 删除 `tee` 日志方案，改为最简单的直接输出到控制台，错误路径保证执行 `pause`。

---

### 错误 5：`ModuleNotFoundError: No module named 'yt_dlp'`（双 Python 环境）

**现象：** 构建成功，运行 `DLCart.exe` 崩溃：
```
ModuleNotFoundError: No module named 'yt_dlp'
```

**原因：** 电脑装了两个 Python：
- `pip` 指向 Python 3.13（yt_dlp 装在这里）
- `pyinstaller` 命令指向 Python 3.12（`C:\Python`，没有 yt_dlp）

PyInstaller 用 Python 3.12 打包，找不到 yt_dlp，打进去的是空的。构建日志的警告：
```
WARNING: collect_data_files - skipping data collection for module 'yt_dlp'
as it is not a package.
```

**解决：** 改用 `python -m PyInstaller`，强制与 `python -m pip` 使用同一解释器，确保打包环境一致。

---

### 错误 6：`AttributeError: 'YTDLPGUI' object has no attribute 'downloads_tree'`

**现象：** 运行 exe 崩溃：
```
File "ytdlp_gui.py", line 1142, in _update_downloads_tree
AttributeError: 'YTDLPGUI' object has no attribute 'downloads_tree'
```

**原因：** `ytdlp_gui.py` 源码中存在缩进 bug。`setup_ui()` 方法只有 3 行（`pack` + `configure`），创建 UI 组件的代码（title、各 section、`setup_downloads_section`）由于缩进错误混入了 `show_ffmpeg_warning()` 方法体内。

执行顺序：
1. `__init__` 调用 `setup_ui()` → 只执行了 2 行，`downloads_tree` 未创建
2. `__init__` 调用 `update_ui()` → 立即调用 `_update_downloads_tree()` → 访问不存在的 `downloads_tree` → 崩溃

**解决：** 将 UI 构建代码从 `show_ffmpeg_warning()` 中移出，放回 `setup_ui()` 方法体内，并删除 `show_ffmpeg_warning()` 中的重复代码。

---

## 已清理的过期文件

| 文件 | 原因 |
|------|------|
| `start.bat` / `setup.bat` / `start-fix.bat` / `manual-start.bat` | 旧版手动启动脚本，已被 `build.bat` 替代 |
| `MANUAL-COMMANDS.txt` / `WINDOWS-README.txt` / `v2.0-README.md` / `RUN.md` / `FEATURES.md` | 冗余文档 |
| `test_installation.py` | 调试用脚本 |
| `frontend/` | 空骨架目录（WinUI3，未实现，未与主程序连接）|
| `backend/` | 未与 `ytdlp_gui.py` 连接的废弃 FastAPI 代码 |
| `docs/` | 空目录 |
| `dist/yt-dlp-gui-windows/` | 旧版分发目录 |
| `build/`（spec、iss、bat 等）| 过度设计的构建系统，已简化为单个 `build.bat` |

---

## 经验总结

1. **Windows bat 文件只写 ASCII**，不要用中文或 Unicode 符号
2. **`python -m PyInstaller`** 比直接调用 `pyinstaller` 更可靠，避免多 Python 环境问题
3. **`--collect-all`** 只能在不使用 spec 文件时用；有 spec 文件就用 spec 里的 `collect_all()`
4. **`tee` 在 Windows 不存在**，日志方案不要依赖它
5. **PyInstaller `--onefile`** 打出的 exe 完全自包含，用户无需安装 Python
6. 过度设计（Inno Setup + spec + 日志系统）反而带来更多问题，最简方案最可靠
