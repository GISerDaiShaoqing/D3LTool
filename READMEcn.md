# D3L Tool of NASA Satellite

|作者|戴劭勍|
|---|---|
|邮箱|dsq1993qingge@163.com|
|官网|https://gisersqdai.top/D3LTool/|

[English](README.md)

D3L Tool v2 是一个免费开源的 NASA 卫星数据**检索与下载**工具：登录 → 检索 → 下载全流程在软件内完成，
基于 NASA 官方 [earthaccess](https://earthaccess.readthedocs.io/) 与 CMR 检索服务重构——
不再需要去 NASA 网站创建订单，也彻底告别浏览器模拟。

## 特性

- **内置检索**：按产品、时间范围、MODIS/VIIRS 正弦瓦片（可点击的 36×18 瓦片地图）或经纬度范围检索，
  检索不需要登录
- **产品覆盖**：MODIS、VIIRS（LAADS DAAC）、MERRA-2（GES DISC），也可输入任意 CMR short_name
- **健壮下载**：多线程队列、分块进度、HTTP 断点续传、失败自动重试、文件大小校验
- **中英双语**：菜单一键切换中文 / English（PySide6 界面）
- **跨平台**：Windows exe / macOS .app / Linux 二进制（CI 自动构建），或 `pip install d3ltool`
- **代理支持**：适应复杂网络环境

## 安装

需要 Python 3.10+。

```bash
python -m pip install -e .
```

开发环境（含 pytest）：`python -m pip install -e ".[dev]"`

## 使用

### 图形界面

```bash
d3ltool-gui     # 或 python -m d3ltool
```

1. **设置 → 登录 Earthdata**，输入免费的
   [NASA Earthdata](https://urs.earthdata.nasa.gov/) 账号
   （检索不需要登录，下载需要；凭据只保存在本机 `~/.netrc`）
2. 选择产品、时间范围，在瓦片地图上点选区域（或输入 `h04v03`，或填写经纬度范围）
3. 点红色"检索"，勾选文件，**加入下载队列**

### 命令行

```bash
d3ltool login
d3ltool search VNP46A1 --start 2020-03-01 --end 2020-03-31 --tile h04v03
d3ltool download VNP46A1 --start 2020-03-01 --end 2020-03-31 --tile h04v03 --dest D:/data
d3ltool search M2T1NXSLV --start 2019-08-01 --end 2019-08-31 --bbox 100 20 120 40
```

## 独立安装包 / Release

预编译包在 [GitHub Releases](https://github.com/GISerDaiShaoqing/D3LTool/releases/latest) 下载：
Windows exe、macOS .app（Apple Silicon 与 Intel 双架构）、Linux 二进制，
推送 `v*` 标签后 CI 自动构建并发布。

本地打包：

```bash
pyinstaller D3LToolNASA.spec --noconfirm   # 产物 dist/D3LToolNASA(.exe/.app)
```

## 文档

- 项目官网：<https://gisersqdai.top/D3LTool/>
- [中文文档](https://gisersqdai.top/D3LTool/documentationcn.html) /
  [Documentation (EN)](https://gisersqdai.top/D3LTool/documentation.html)
- v1.0（2018，浏览器模拟方案）的旧版说明保留在 [docs/legacy/](docs/legacy/)

## 致谢与许可

- v1.0（2018）作者：戴劭勍；v2.0 基于
  [earthaccess](https://earthaccess.readthedocs.io/) / CMR 重构
- 使用 [MIT 许可](https://mit-license.org/)发布
- 有问题欢迎[提交 issue](https://github.com/GISerDaiShaoqing/D3LTool/issues)
  或联系 dsq1993qingge@163.com

## 更新日志

- **2026-09 v2.0.3** — 产品目录窗口（按卫星浏览产品/版本/说明、可筛选、双击选用）；CI 因 GitHub 退役 macos-13 Intel runner 改为仅 Apple Silicon 构建（Intel Mac 用户用 `pip install d3ltool`）
- **2026-09 v2.0.2** — Earthdata 登录彻底修复：适配 earthaccess 0.19 认证单例、启动时自动从本机 netrc 恢复会话、登录失败提示精准化（401/网络/账号受限）
- **2026-09 v2.0.0** — 全新重构：earthaccess/CMR 检索、瓦片地图、断点续传、PySide6 双语界面、跨平台
- 2018-04-27 v1.0 — 首个版本（浏览器模拟订单下载）
