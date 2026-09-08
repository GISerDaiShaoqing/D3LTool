# D3L Tool of NASA Satellite v2.0

D3L Tool v2 是一个免费开源的 NASA 卫星数据下载工具：在软件内完成 **登录 → 检索 → 下载** 全流程，
不再需要去 NASA 网站创建订单，也**不再依赖浏览器模拟**。

D3L Tool v2 is a free & open-source downloader for NASA Earth science data:
**login → search → download** all inside one app. No more manual orders, no more browser automation.

## 特性 / Features

- **内置检索 / Built-in search**：按产品、时间范围、MODIS/VIIRS 正弦瓦片（h##v##，可点击瓦片图选择）或经纬度范围检索
  Search by product, date range, sinusoidal tile (clickable tile map) or bounding box
- **产品覆盖 / Coverage**：MODIS、VIIRS（LAADS DAAC）与 MERRA-2（GES DISC），基于 NASA 官方
  [CMR](https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html) 与 [earthaccess](https://earthaccess.readthedocs.io/)
- **健壮下载 / Robust download**：多线程队列、分块进度、断点续传（Range）、失败自动重试、文件大小校验
  Multi-threaded queue, chunked progress, HTTP Range resume, auto-retry, size validation
- **中英双语 / Bilingual**：菜单一键切换中文 / English
- **GUI + CLI**：PySide6 图形界面，同时提供命令行（`d3ltool search` / `d3ltool download`）
- **代理支持 / Proxy**：适应复杂网络环境

## 安装 / Install

需要 Python 3.10+。

```bash
cd D3LTool
python -m pip install -e .
```

可选安装开发依赖（含 pytest）：`python -m pip install -e ".[dev]"`

## 使用 / Usage

### 图形界面 / GUI

```bash
d3ltool-gui     # 或 python -m d3ltool
```

1. 菜单/工具栏 **登录** —— 输入 [NASA Earthdata Login](https://urs.earthdata.nasa.gov/) 账号密码
   （检索不需要登录；凭据只保存在本机 `~/.netrc`）
2. 左侧 **检索面板** —— 选产品（或填自定义 short_name）、时间范围、点瓦片图选区域（MERRA-2 可填经纬度范围）
3. 结果表勾选文件 → **加入下载队列**，右下角任务表实时显示进度，支持暂停/续传/重试

### 命令行 / CLI

```bash
# 登录（交互输入，持久化到 ~/.netrc）
d3ltool login

# 检索：VNP46A1 夜光产品，2020年3月，瓦片 h04v03
d3ltool search VNP46A1 --start 2020-03-01 --end 2020-03-31 --tile h04v03

# 下载到指定目录
d3ltool download VNP46A1 --start 2020-03-01 --end 2020-03-31 --tile h04v03 --dest D:/data --workers 4

# MERRA-2（按经纬度范围）
d3ltool search M2T1NXSLV --start 2019-08-01 --end 2019-08-31 --bbox 100 20 120 40
```

## 设置 / Settings

- 下载目录、并发数、代理（HTTP/SOCKS）：GUI 内 **设置** 对话框；配置保存在 `~/.d3ltool/config.json`
- 已完成的文件再次下载时会自动跳过；未完成的 `.part` 文件自动断点续传

## 打包单文件 exe / Build a standalone exe

```bash
.venv/Scripts/pyinstaller.exe D3LToolNASA.spec --noconfirm
# 产物: dist/D3LToolNASA.exe（窗口版，带 D3L 图标，内嵌全部资源）
```

图标由 `make_icon.py` 生成（种子固定、可复现），改配色后重跑该脚本再重新打包即可。

## 跨平台发行 / Cross-platform

代码本身三平台通用（PySide6 + earthaccess 均为跨平台库），差异只在打包。
`D3LToolNASA.spec` 平台感知：Windows 用 `.ico`、macOS 用 `.icns` 并产出 `.app`、Linux 直接出二进制。

- **自动化（推荐）**：推送 `v*` 标签或在 Actions 页手动触发 `build` 工作流，
  会自动在 windows / macos-14(Apple Silicon) / macos-13(Intel) / ubuntu 四个环境构建，
  产物上传到 Actions Artifacts，标签构建同时挂到 GitHub Release。
- **注意**：PyInstaller 不能交叉编译，mac 版必须在 macOS 上构建 —— 这正是用 CI 的原因。
- **macOS Gatekeeper**：无签名（未加入 Apple 开发者计划）的 .app 首次打开会被拦截，
  可右键 → 打开，或执行 `xattr -cr D3LToolNASA.app`；若需正式分发，加入
  Apple Developer Program（$99/年）后在 CI 中补充签名与公证。
- **零安装替代**：`pip install d3ltool` 在任何平台都能直接用 CLI / GUI（`d3ltool-gui`）。

## 常见问题 / FAQ

- **下载 401/403**：请在 [Earthdata Login](https://urs.earthdata.nasa.gov/) 完成注册并同意相应 DAAC 的 EULA
- **速度慢**：优先检查代理设置；LAADS/GES DISC 国内直连速度不稳定属正常现象，工具支持续传，中断后重试即可
- **旧版 v1.0（浏览器模拟订单下载）**：已停止维护，源码保留于本仓库上层目录

## 致谢 / Credits

- v1.0 (2018) 原作者：戴劭勍 (Dai Shaoqing)
- v2.0 基于 NASA [earthaccess](https://earthaccess.readthedocs.io/) 与 CMR 重写

## License

MIT
