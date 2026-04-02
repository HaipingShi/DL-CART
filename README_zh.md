<p align="right">
  <a href="README.md">🇬🇧 English</a> | 🇨🇳 简体中文
</p>

<div align="center">
  <a href="https://github.com/HaipingShi/ytdlp-lh/releases/latest">
    <img src="logo.png" alt="独轮车 Logo" width="120" height="120">
  </a>

  <h1>独轮车 DL Cart</h1>

  <p><strong>全能视频下载器 — 基于 yt-dlp</strong></p>

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
    <a href="https://github.com/HaipingShi/ytdlp-lh/releases/latest"><strong>📥 下载 EXE（Windows，免安装）</strong></a>
  </p>
</div>

---

> **这是什么？** 一款名叫 **独轮车（DL Cart）** 的独立视频下载器，将 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 和 [FFmpeg](https://ffmpeg.org/) 的全部能力打包到一个双击即运行的单文件 `.exe` 中。无需安装 Python、无需配置 FFmpeg、无需敲命令行 — 粘贴链接即可下载。
>
> DL = Downloader = 独轮，独轮车载着你的视频滚滚而来。

---

## 功能一览

yt-dlp 能做的，它都能做，而且操作更方便：

### 核心下载引擎

- **支持 1000+ 网站** — YouTube、B站、Twitter/X、TikTok、抖音、Vimeo 等等（与 yt-dlp 完全一致）
- **默认最佳画质** — 自动选择最高质量的视频 + 音频流并合并
- **画质预设** — 4K、1080p、720p、480p、仅音频，一键切换
- **自定义格式** — 高级用户可直接输入 yt-dlp 格式字符串
- **限速下载** — 设置最大下载带宽（KB/s），适合共享网络环境

### 字幕 & 元数据

- **10+ 种字幕语言** — 英文、简中、繁中、日文、韩文、西班牙文、法文、德文、俄文、自动检测
- **自动生成字幕** — 下载机器生成的字幕（如果网站支持）
- **嵌入缩略图** — 自动将视频封面嵌入下载文件
- **写入元数据** — 通过 FFmpeg 写入标题、上传者等信息

### 下载管理

- **并发下载** — 最多同时下载 10 个任务（可配置）
- **队列系统** — 添加多个链接，有空位自动开始下一个
- **取消 & 重试** — 干净地取消正在进行的下载；一键重试失败任务
- **持久化历史** — 最近 200 条下载记录保存到磁盘，重启不丢失
- **右键操作** — 取消 / 重试 / 打开文件 / 打开文件夹 / 从列表删除

### 实时监控

- **可视化进度条** — Unicode 方块进度条 `████░░░░ 45%`，实时更新
- **速度 & 剩余时间** — 实时显示下载速度和预计剩余时间
- **文件大小追踪** — 显示总大小和已下载字节数
- **颜色状态标识** — 绿色 = 完成，黄色 = 下载中，红色 = 失败

### 系统集成

- **内置 FFmpeg** — ffmpeg.exe 打包在 EXE 内，零外部依赖
- **Windows 通知** — 下载完成时弹出系统通知
- **暗色 / 亮色主题** — 在设置中切换，默认暗色
- **代理支持** — 可配置 HTTP/SOCKS 代理，突破网络限制

---

## 🔒 Windows 安全提示

首次运行 EXE 时，Windows 可能会显示：

> *"Windows 已保护你的电脑"*

这是**误报** — 应用由 [公开源代码](https://github.com/HaipingShi/ytdlp-lh) 通过 GitHub Actions 自动构建。出现提示是因为 EXE 没有代码签名。

**解决方法：**

1. 点击 **"更多信息"**
2. 点击 **"仍要运行"**

如果不想绕过提示，可以[自己从源码构建 EXE](#从源码构建) 或[直接用 Python 运行](#从源码运行)。

---

## 下载安装

### Windows EXE（推荐）

1. 前往 **[最新版本](https://github.com/HaipingShi/ytdlp-lh/releases/latest)**
2. 下载 `DLCart.exe`
3. 双击运行 — 无需安装，无需依赖

EXE 已包含 yt-dlp + FFmpeg，开箱即用。

<a name="从源码运行"></a>
### 从源码运行

要求：Python 3.8+，Windows / macOS / Linux。

```bash
git clone https://github.com/HaipingShi/ytdlp-lh.git
cd ytdlp-lh
pip install yt-dlp
python ytdlp_gui.py
```

> 从源码运行需单独安装 FFmpeg。Windows 下将 `ffmpeg.exe` 放在 `ytdlp_gui.py` 同目录即可。

<a name="从源码构建"></a>
### 从源码构建

```bash
pip install pyinstaller

# Windows（需要当前目录有 ffmpeg.exe 和 ffprobe.exe）
pyinstaller --onefile --windowed --collect-all yt_dlp ^
  --add-binary "ffmpeg.exe;." --add-binary "ffprobe.exe;." ^
  --name DLCart ytdlp_gui.py
```

---

## 快速上手

1. **双击** `DLCart.exe`
2. **粘贴** 任意视频链接到输入框（Ctrl+V）
3. **选择画质** — 保持"最佳"即可获得最高画质
4. **点击下载**
5. 完成后右键点击记录 → **"打开文件"** 即可播放

### 快捷操作

| 操作 | 方法 |
|------|------|
| 粘贴链接 | 在输入框中 Ctrl+V，或右键 → 粘贴 |
| 取消下载 | 右键点击行 → 取消 |
| 重试失败 | 右键点击行 → 重试 |
| 打开已下载文件 | 右键点击行 → 打开文件 |
| 打开下载目录 | 右键点击行 → 打开文件夹 |
| 清空输入框 | 点击清除按钮 |

---

## 设置

点击 ⚙️ 按钮打开。所有设置跨会话持久化。

| 设置 | 说明 | 默认值 |
|------|------|--------|
| 下载目录 | 文件保存位置 | `~/Downloads` |
| 最大并发 | 同时下载数（1–10） | 3 |
| 速度限制 | KB/s 上限，0 = 不限速 | 0 |
| 主题 | 暗色或亮色 | 暗色 |

设置文件位于 `~/.dlcart/settings.json`。

---

## 支持的网站

本应用支持 **yt-dlp 支持的所有网站** — 超过 1000 个且持续增加。以下是部分热门站点：

| 网站 | 网站 | 网站 |
|------|------|------|
| YouTube | B站 (Bilibili) | Twitter/X |
| TikTok / 抖音 | Vimeo | Dailymotion |
| Facebook | Instagram | Reddit |
| SoundCloud | Niconico | Twitch |
| Pinterest | Tumblr | 更多... |

完整列表：[yt-dlp 支持的网站](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

---

## 项目结构

```
ytdlp-lh/
├── ytdlp_gui.py          # 整个应用只有一个文件
├── requirements.txt      # Python 依赖
├── .github/workflows/
│   └── build.yml         # CI：构建 EXE 并发布到 GitHub Releases
├── docs/                 # 文档和计划
└── README.md
```

---

## 常见问题

<details>
<summary><strong>Windows 提示"已保护你的电脑"</strong></summary>

这是 SmartScreen 拦截未签名应用。点击 <strong>"更多信息"</strong> → <strong>"仍要运行"</strong>。详情见上方的安全提示部分。
</details>

<details>
<summary><strong>视频下载了但没有声音</strong></summary>

说明视频流和音频流没有合并。请确保 FFmpeg 可用。使用 EXE 版本时 FFmpeg 已内置，不应出现此问题。从源码运行时需单独安装 FFmpeg。
</details>

<details>
<summary><strong>"不支持的 URL" 错误</strong></summary>

- 检查网络连接是否正常
- 确认链接在浏览器中可以打开
- 该网站可能需要登录、有地区限制、或暂未被 yt-dlp 支持
</details>

<details>
<summary><strong>下载速度慢</strong></summary>

- 尝试设置速度限制（设置 → 速度限制） — 部分服务器会限制过快的连接
- 选择较低的画质以减小文件大小
- 运营商可能限制了视频流量 — 尝试使用 VPN
</details>

<details>
<summary><strong>应用无法启动</strong></summary>

**EXE 版本：**

- 需要 Windows 10 1809 或更高版本
- 右键 → 属性 → 勾选"解除锁定"
- 尝试以管理员身份运行

**Python 版本：**

- 确认 Python 3.8+：`python --version`
- 安装依赖：`pip install yt-dlp`
- 查看 `dlcart.log` 获取错误详情
</details>

---

## 参与贡献

1. Fork 本仓库
2. 创建分支：`git checkout -b feature/my-feature`
3. 提交：`git commit -m 'Add my feature'`
4. 推送：`git push origin feature/my-feature`
5. 发起 Pull Request

欢迎在 [Issues](https://github.com/HaipingShi/ytdlp-lh/issues) 提交 Bug 报告和功能建议。

---

## 许可证

MIT License — 见 [LICENSE](LICENSE)。

---

## 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — 让一切成为可能的下载引擎
- [FFmpeg](https://ffmpeg.org/) — 流合并、元数据和缩略图嵌入
- [Python](https://www.python.org/) + [Tkinter](https://docs.python.org/3/library/tkinter.html) — 应用运行时和 GUI 框架

---

<div align="center">
  <p><strong>觉得有用？给个 ⭐ Star 吧！</strong></p>
</div>
