🇬🇧 [English](README.md) · 🇨🇳 [中文](README.zh.md) · 🇪🇸 [Español](README.es.md) · 🇮🇳 [हिन्दी](README.hi.md) · 🇸🇦 [العربية](README.ar.md) · 🇵🇹 [Português](README.pt.md) · 🇷🇺 [Русский](README.ru.md) · 🇫🇷 [Français](README.fr.md) · 🇯🇵 [日本語](README.ja.md) · 🇩🇪 [Deutsch](README.de.md)

# Gazette Drouot watcher

监控 gazette-drouot.com 的一个或多个栏目（文章列表）页面，每当有新文章或文章更新时都会发送一条 Windows 通知——点击通知即可在默认浏览器中打开该文章。

## 工作原理

- 每次运行时，都会完整扫描每个已配置栏目的前 `MAX_PAGES` 个列表页面（而不仅仅是扫描到发现"已知"文章为止——测试表明该网站的分页顺序并不总是按时间顺序排列，过早停止可能会悄无声息地漏掉真正的新内容）。
- 每篇找到的文章都会根据其数字 id **以及**发布日期与已保存的状态（`state/<rubrique-key>.json`）进行比对。新 id → 发送通知。已知 id 但日期与上次不同 → 再次发送通知（该文章可能已被重新发布/编辑）。完全没有显示日期的文章只会被通知一次，之后不再检查。
- 某个栏目首次运行时，只会静默记录当前已有的内容作为基线——安装时不会因预先存在的文章而产生大量通知。
- 如果在一次运行中某个栏目出现的新增/更新文章超过 `FLOOD_CAP` 篇，只有前几篇会单独收到通知——其余的会合并为一条"还有 N 篇新文章"的汇总通知。

## 安装设置

- **运行期间必须关闭 VPN**——Cloudflare 会对 VPN IP 强制进行自动化无法通过的交互式验证。普通家庭 IP 不会有问题。
- 需要已安装 Microsoft Edge（通过 Playwright 的 `channel="msedge"` 直接使用系统中的 Edge，无需单独下载浏览器）。
- `pip install -r requirements.txt`

## 配置

**`gazette_watcher/config.py` 是唯一需要编辑的文件**，涵盖一切设置：监控哪些页面、检查频率、扫描深度、通知上限、提醒冷却时间等——每个设置项都有注释说明（也可以在控制面板的"设置"标签页中编辑，见下文）。修改后将在下次运行时生效，**唯一例外**是 `POLL_INTERVAL_MINUTES`，修改后还需在控制面板中再次点击**"安装"**，才能以新的间隔更新实际的 Windows 计划任务。

## 控制面板（图形界面）

**这就是应用程序本身**——单个独立的 `.exe` 文件，运行它的电脑无需单独安装 Python，也不需要任何脚本文件。一个桌面窗口，涵盖以下所有操作：安装/启用/禁用/卸载计划任务（直接通过原生的计划任务 API，不涉及 PowerShell），以及一个设置面板（如果设置出错，可"恢复默认设置"），取代手动编辑配置文件。国旗图标用于切换界面语言（英语、中文、西班牙语、हिन्दी、العربية、葡萄牙语、俄语、法语、日本語、德语——默认跟随 Windows 界面语言，不支持时回退为英语）；太阳/月亮图标用于切换浅色/深色模式（默认跟随 Windows 主题）。两项选择都会保存在 `gui_prefs.json` 中。

**如果您只有 `.exe` 文件：**双击 `GazetteDrouotWatcher.exe` 即可——无需安装其他任何东西。该文件需直接放在此项目文件夹中，与 `gazette_watcher/` 等同级。在窗口中点击**"安装"**即可注册计划任务——此后程序会按照 `config.py` 中设定的间隔在后台自动检查，无需保持此窗口（甚至整个程序）打开，并且每次电脑重启后会自动重新启动。

**从源代码运行：**双击 `main.pyw`（Windows 会通过 `pythonw.exe` 运行 `.pyw` 文件，不会出现控制台窗口），或运行：
```
pythonw.exe main.pyw
```

**自行构建 `.exe`**（该文件已被 gitignore 排除——不会提交到源代码仓库，请自行重新构建或从 Release 中下载）：
```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name GazetteDrouotWatcher --icon icon.ico main.pyw
```
然后将 `dist/GazetteDrouotWatcher.exe` 复制到项目根目录（与 `main.pyw` 同级），并删除残留的 `build/`、`dist/` 和 `*.spec`。

## 手动运行

`main.pyw --watch`（或等效的 `GazetteDrouotWatcher.exe --watch`）就是计划任务实际调用的命令——执行一次检查后退出，没有图形界面。这也等同于：
```
python -m gazette_watcher.watcher
```

## 出现问题时

程序设有两种不同的警报通知，每种通知在 `ALERT_COOLDOWN_HOURS`（config.py）时间内最多只会发送一次，以避免持续存在的问题在每次运行时都发送通知：

- **"blocked by Cloudflare"（被 Cloudflare 阻止）**——网站的反爬虫防护拦截了请求。几乎总是通过关闭 VPN 即可解决。
- **"needs an update"（需要更新）**——页面加载成功，但其 HTML 结构已不再符合此脚本的预期。很可能是 gazette-drouot.com 更改了页面布局，需要更新抓取器的选择器（`gazette_watcher/scraper.py`）以匹配新结构。

`logs/watcher.log` 中包含每次运行的完整详情——如果通知不再出现，请先查看此日志。

## 在不影响真实网站的情况下进行测试

`test/` 目录包含一个小型本地伪站点测试环境，可用于单独测试抓取/通知逻辑，而不会给真实网站增加负担，也不依赖其实时内容。详见 `test/README.md`。

## 添加要监控的其他页面

在 `config.py` 的 `RUBRIQUES` 中添加另一个条目即可——只要该页面使用相同的 `div.articleResume` 卡片结构，无需再做其他更改。
