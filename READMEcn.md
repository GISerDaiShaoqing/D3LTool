# D3L Tool of NASA Satellite

| 项目   | 信息                                                         |
|:-------|:-------------------------------------------------------------|
| 作者   | 戴劭勍                                                       |
| 官网   | <https://gisersqdai.top/D3LTool/>                            |
| GitHub | [@GISerDaiShaoqing](https://github.com/GISerDaiShaoqing)     |
| 邮箱   | <dsq1993qingge@163.com>                                      |
| ORCID  | [0000-0003-0858-4728](https://orcid.org/0000-0003-0858-4728) |
| 许可   | MIT                                                          |

[English](README.md)

[![GLASS engine: glass.sqdaitools](https://img.shields.io/badge/GLASS%20engine-glass.sqdaitools%20v0.1.0-2ea44f)](https://github.com/GISerDaiShaoqing/glass.sqdaitools)

D3L Tool v2 是一个免费开源的 NASA 卫星数据**检索与下载**工具：登录 → 检索 → 下载全流程在软件内完成，
基于 NASA 官方 [earthaccess](https://earthaccess.readthedocs.io/) 与 CMR 检索服务重构，
v2.3 起还支持单像元时间序列采样与软件内绘图（OPeNDAP 直采）。
**GLASS 数据支持（v2.5 起提供，v2.6.0 全面升级，v2.7.0 自适应）**：公开的 **GLASS**（Global Land Surface Satellite）
档案也纳入同一流程——免登录；GLASS 检索/下载模块以作者的 R 包
[glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools)
（[文档](https://giserdaishaoqing.github.io/glass.sqdaitools/)，v0.1.0）为骨架：
D3L Tool 管"找和下"，后处理在 R 侧完成——两个项目配套使用。
不再需要去 NASA 网站创建订单，也彻底告别浏览器模拟。

## 特性

- **内置检索**：按产品、时间范围、MODIS/VIIRS 正弦瓦片（可点击的 36×18 瓦片地图）或经纬度范围检索，
  检索不需要登录
- **产品覆盖**：MODIS、VIIRS（LAADS DAAC）、MERRA-2（GES DISC），也可输入任意 CMR short_name
- **GLASS 数据源**（v2.5.0 新增，v2.6.0 全面升级，v2.7.0 自适应）：检索并下载 GLASS（Global Land
  Surface Satellite）产品体系——公开 [glass.hku.hk](https://glass.hku.hk) 档案的
  133 个变体（131 个经真实 granule 核验），无需 Earthdata 登录；四种归档布局
  全覆盖，全球 CMG 产品无需选瓦片，静态集无需日期。检索引擎以作者的 R 包
  [glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools/tree/v0.1.0)
  v0.1.0 为骨架（归档扫描变体清单、瓦片定位、合成 DOY 展开、核验过滤）；
  填充值处理、瓦片镶嵌、重投影裁剪与时序合成仍在 R 侧完成——
  见下文[「GLASS 支持与 glass.sqdaitools」](#glass-支持与-glasssqdaitoolsv250)
- **健壮下载**：多线程队列、分块进度、HTTP 断点续传、失败自动重试、文件大小校验
- **MCP 服务器**（v2.1 新增）：`d3ltool-mcp` 把检索/瓦片换算/下载暴露为
  [MCP 工具](docs/mcp.md)，Claude Desktop、Claude Code、Codex、Cursor、
  OpenCode、Qoder、ZCode 等 AI 客户端可直接调用
- **AI 助手**（v2.1 新增，v2.2 改版）：主窗口右缘滑出的悬浮抽屉，数据界面完全
  不受影响；⚙ 弹出式设置接入任意 OpenAI 兼容 API Key（DeepSeek / Qwen / Kimi /
  智谱 / OpenAI / Ollama…），自然语言直接完成检索与下载；聊天区可自定义背景图；
  下载会先弹窗确认
- **时间序列**（v2.3 新增）：独立右缘抽屉，MODIS/VIIRS 与 MERRA-2 产品任选，
  输入经纬度与日期范围即可在软件内绘制该像元随时间变化的折线图，一键导出
  CSV——数据由 NASA OPeNDAP 直采，不经任何第三方子集服务；2017 年
  MODIS Web Service 实验的现代复活
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
d3ltool search LAI_MODIS_250M --start 2018-08-01 --end 2018-12-31 --tile h28v05   # GLASS，免登录
```

### GLASS 支持与 glass.sqdaitools（v2.5.0）

GLASS 模块以作者的 R 包
[glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools/tree/v0.1.0)
（[文档](https://giserdaishaoqing.github.io/glass.sqdaitools/)，v0.1.0）为骨架：
归档扫描得到的变体清单（133 个产品×来源×分辨率，其中 131 个经真实 granule
核验）、正弦瓦片定位、合成 DOY 展开与核验产品过滤均移植自它。两个项目
**配套使用**、分工明确：

| | 负责 |
|---|---|
| **D3LTool**（GUI / CLI / MCP） | GLASS 产品检索与批量下载——断点续传、大小校验、免登录（公开档案） |
| **R：glass.sqdaitools** | 填充值/比例因子处理、多瓦片镶嵌、重投影与 ROI 裁剪、时间合成（基于 `terra`） |

D3LTool 下载好的文件在 R 中做后处理：

```r
# R >= 4.1；重依赖 terra / sf
devtools::install_github("GISerDaiShaoqing/glass.sqdaitools")
glass.sqdaitools::glass_process(files, roi = my_roi,
                                product = "LAI_MODIS_250M",
                                fun = "mean", outfile = "lai_2023_mean.tif")
```

![对内置 AI 助手说一句"帮我下载厦门市 2024-10-23 的 GLASS 的 EVI 数据"——
`list_products` 定变体、`search_granules` 按 bbox 检索、`start_download`
免登录下载，三个文件全部完成；后续镶嵌/裁剪/合成在 R 中用
glass.sqdaitools 完成](images/GlassDownload.png)

**v2.6.0 升级**：登记表对齐 glass.sqdaitools 全量核验版（131/133 实测），
四种归档布局全覆盖——`year_doy` 合成目录、`flat` 静态文件集（KGClim/AGB：
无需日期，GUI 自动禁用日期、CLI 改为可选）、`year_files` 年目录（BBE/TPSCE：
按文件名 `A{yyyy}{ddd}` 片段过滤，无合成周期的按年整列）与 `year_yyyddd`
日目录（AWGF_LST：7 位 `YYYYDDD`）。全球 CMG 产品（文件名无 `h##v##`）
对瓦片/范围框完全免疫，数据文件扩展名按变体来自核验台账
（`.hdf`/`.tif`/`.nc`/`.dat`）。目录列表遵循实测的 glass.hku.hk 礼貌策略：
8/24/72s 指数退避 + 15s 冷却末次重试、列表请求间隔 ≥1.2s、同一年目录
无论日期跨度多长只列一次。

**v2.7.0 自适应**：登记表中未登记合成周期的约 50 个核验变体（FVC、
Albedo AVHRR/MIX/0.5D、PAR、RN/SM、NDVI/EVI 0.25°、NPP 等）不再迷信
`year_doy` 标签——检索按区间逐年只列一次真实目录，直接适配档案实况：
文件直躺年目录（文件名携带合成码）、`yyyyMM` 月码、或根下套一层版本
包装目录（NPP 的 `GLASS_NPP_0.05D_V40/`）。合成日期从文件名解析
（A 头优先，其次取文件名中最先出现的日期 token），步长从相邻合成
起点差反推，span 语义取舍；年内只有一个文件则整年保留。只有子目录的
静态根（ABI 500M 的 365 个日目录）明确报错而非静默空表。"网站"菜单
新增 GLASS 产品官网与配套 R 包主页 glass.sqdaitools（其 0.6.0 迭代与本
版本同步）。

版本兼容：D3L Tool **2.7.0** ↔ glass.sqdaitools **≥ 0.1.0**——后续若有
API 变更会在两边的 release notes 同步声明。
GLASS 数据来自 GLASS 产品团队（[glass.hku.hk](https://glass.hku.hk)），
使用请遵守其引用政策。

### MCP / AI 助手

两条通道共用同一套工具：`check_auth` / `list_products` / `point_to_tile` /
`tile_bounds` / `search_granules` / `start_download` / `download_status` /
`cancel_download` / `retry_download`，另有 `point_timeseries` /
`plot_timeseries`（v2.3）与浏览器辅助下载的 `export_download_urls` /
`open_download_page`（v2.4）。密码永远不会作为工具参数——下载复用本机
已登录的 Earthdata 凭据（GLASS 公开档案 URL 无需登录）。

```bash
python -m pip install "d3ltool[mcp]"   # 然后把 MCP 客户端指向 d3ltool-mcp
```

Claude Desktop / Claude Code / Codex / Cursor / OpenCode / Qoder / ZCode
配置与软件内 AI 助手的用法见 [docs/mcp.md](docs/mcp.md)。

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
- GLASS 数据由 GLASS 产品团队（[glass.hku.hk](https://glass.hku.hk)）生产，
  使用请遵守其引用政策；GLASS 模块（v2.5）移植自作者的
  [glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools) R 包
- 使用 [MIT 许可](https://mit-license.org/)发布
- 有问题欢迎[提交 issue](https://github.com/GISerDaiShaoqing/D3LTool/issues)
  或联系 dsq1993qingge@163.com

## 更新日志

- **2026-11 v2.7.0** — 未登记合成周期的 GLASS 变体改为**自适应检索**而非
  "cadence 错误"或静默空表：约 50 个核验变体（FVC、Albedo AVHRR/MIX/0.5D、
  PAR、RN/SM、NDVI/EVI 0.25°、NPP 等）登记表无合成周期，而档案实际有
  四种组织形态——文件直躺年目录（`A{yyyy}{ddd}` 合成码）、月码
  （`yyyyMM`）、真 DOY 子目录、或根下套一层版本包装目录（NPP 的
  `GLASS_NPP_0.05D_V40/` 与其 `YEARLY` 姊妹并列）。检索逐年只列一次，
  从文件名解析合成日期（A 头优先，其次文件名最先出现的日期 token——
  NDVI 0.25° 尾部的处理日期 "2023068" 不再被误读为 DOY），步长由相邻
  合成起点差反推、按 span 语义取舍；年内只一个文件的整年保留；只有
  子目录的静态根（ABI 500M 的 365 个日目录）明确报错而非静默空表。
  "网站"菜单新增 GLASS 产品官网与 glass.sqdaitools 主页——与 R 包 0.6.0
  迭代同步。live 档案验收：`FVC_AVHRR_0_5D` 2018-08-01..09-15 = 恰好
  14 个文件（7 合成 × hdf + hdf.xml）。首个重度场景：`AWGF_LST_ABI_2km`
  跨四年 = 约 1410 个日目录，GLASS 检索因此**可随时取消**（检索按钮兼任
  "取消检索"）并显示目录级进度条；查询将列出超过 200 个目录时产品提示
  会提前预警。
- **2026-11 v2.6.0** — GLASS 模块对齐 glass.sqdaitools 全量核验登记表
  （133 个变体中 131 个经真实 granule 实测）：四种归档布局全覆盖——
  `year_doy` 合成目录、`flat` 静态文件集（KGClim/AGB；无需日期——GUI
  自动禁用、CLI 改为可选）、`year_files` 年目录（BBE/TPSCE；按文件名
  `A{yyyy}{ddd}` 片段过滤，无合成周期的按年整列）与 `year_yyyddd` 日目录
  （AWGF_LST）。全球 CMG 产品（文件名无 `h##v##`）对瓦片/范围框完全免疫
  ——不再有"按分瓦片假设检索出零结果"的坑；数据文件扩展名（`.hdf`/`.tif`/
  `.nc`/`.dat`）按变体取自核验台账的真实 granule 样本。目录列表遵循实测的
  glass.hku.hk 礼貌策略：8/24/72s 指数退避 + 15s 冷却末次重试、任意两次
  列表请求间隔 ≥1.2s、同一年目录无论日期跨度只列一次（抓取缓存——此前
  BBE 一整年逐日要抓 366 次同一页面，现在 1 次）。产品描述标注 Albedo 多
  波段（后处理在 R 包选子数据集）与 BBE 归档 scale 标注方向反（×10000，
  由 R 包修正）。登记表再生成支持接入 R 包核验台账
  （`tools_gen_glass_registry.py`）。四种布局端到端 live 验收通过
  （LAI 2018-08 h25v05；KGClim 14 个 tif；BBE 1982-01-01~03；AWGF_LST
  2021-06-30 共 48 个文件）
- **2026-11 v2.5.0** — 新增 **GLASS** 数据源：软件现在也能检索并下载 GLASS
  产品体系——130+ 个产品×来源×分辨率变体，由公开
  [glass.hku.hk](https://glass.hku.hk) 档案以纯 HTML 目录列表提供
  （不走 CMR、无需 Earthdata 登录）。产品目录新增 **GLASS** 组，收录完整
  变体清单（5 个已核验变体排前：LAI/NDVI/EVI MODIS 250m、FVC 500m、Ta 逐日）；
  GLASS 变体 id 自动路由到新的档案检索——日期范围展开为合成 DOY 文件夹，
  复用同一张正弦瓦片地图与瓦片换算，bbox 与正弦网格的相交用解析法精确判定
  （与作者的 [glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools)
  R 包一致；极冠行退化为整行纳入）。下载复用现有引擎——公开 URL 免登录，
  GUI 与 `start_download` 对全 GLASS 批次跳过 Earthdata 闸门——v2.4 的
  清单导出/浏览器辅助下载对 GLASS 原样可用。未核验合成周期的 skeleton
  变体会直接从档案自身推导年份/DOY 文件夹；registry 骨架无法刻画的布局
  （气候态根目录、已下线的目录）会给出明确报错而不是静默空表。
  MCP/AI：同样 13 个工具自动覆盖 GLASS（`list_products(group='GLASS')`，
  结果上限 80 行），软件内助手的系统提示词注明免登录路线。GLASS 引擎以作者的
  R 包
  [glass.sqdaitools](https://github.com/GISerDaiShaoqing/glass.sqdaitools/tree/v0.1.0)
  v0.1.0（[文档](https://giserdaishaoqing.github.io/glass.sqdaitools/)）为骨架——
  Python 侧 registry 由其数据集生成（`tools_gen_glass_registry.py`）；
  版本兼容 D3L Tool 2.5.0 ↔ glass.sqdaitools ≥ 0.1.0（API 变更在两边
  release notes 同步声明）。检索下载在 D3LTool，R 包保留后处理
  （填充值/镶嵌/裁剪/合成）——见[「GLASS 支持与 glass.sqdaitools」](#glass-支持与-glasssqdaitoolsv250)；
  GLASS 数据来自 GLASS 产品团队（glass.hku.hk），使用请遵守其引用政策
- **2026-11 v2.4.0** — 新增**浏览器辅助下载**（v1.0 2018 浏览器自动化的现代、
  零依赖嗣法）：结果表加**「导出下载清单」**（勾选的粒子 URL 导成 `.txt`——一行一个
  地址，`wget -i` / `aria2c -i` / 下载管理器直接吃——外加一张自包含 `.html`
  索引页）和**「在浏览器打开」**（索引页弹进你的默认浏览器，逐个点或用
  Download It All / DownThemAll 类扩展全选批量下）；任务表加**「导出失败清单」**
  （只导失败任务——下次检索就覆盖结果表，而失败 URL 在任务表里留着，救援线跨
  检索生存）：401/403 卡住的文件改由浏览器里已登录的 Earthdata 会话去拉。
  结果表另加**「清除结果」**一键清空。
  同款能力经 MCP/AI 暴露：新增 `export_download_urls` / `open_download_page`
  两工具（现共 13 个；凭据不进聊天/MCP，走浏览器会话）。瓦片行同时新增
  「清除瓦片」按钮一键全清（此前只能逐个再点已选瓦片取消）。瓦片地图窄行的
  格线也改为随行带宽收窄——旧的固定 9px 步距把极区窄行的格线画过行边界，
  在球体外面留下一把竖条纹（现已与点击分区完全对齐）
- **2026-10 v2.3.0** — 新增**时间序列**抽屉（独立右缘抽屉，边缘 "TS" 按钮与 AI
  抽屉并列，二者互斥展开）：任选 MODIS/VIIRS 产品与图层，填入经纬度与日期范围，
  软件内直接绘制该像元的折线图（QtCharts）——2017 年 MODIS Web Service 单点
  时间序列实验的现代复活。像元值**直接由 NASA OPeNDAP 采样**——MODIS/VIIRS 走
  LAADS、MERRA-2 走 GES DISC 云网关（与下载同源同凭据：不需要 AppEEARS、不需要
  代理、大陆直连），并支持一键**导出 CSV**。同款采样也以 `point_timeseries` +
  `plot_timeseries` 工具暴露给 MCP 客户端与软件内 AI 助手——助手取完序列可直接
  画进软件的时间序列抽屉。附带修正：经纬度→瓦片换算改用真实正弦投影网格（与实际文件逐像素
  校准），修复了经纬度定位与 AI point_to_tile 旧版 10° 方盒近似的偏差。图层名现支持
  模糊匹配——直接写 'NDVI' 也能命中 _250m_16_days_NDVI（忽略大小写/下划线/空格）——
  AI 聊天里工具报错会带出具体原因，不再只显示错误键名；CMR 查无的产品名（模型照
  MOD13Q1 类推出的 MCD13Q1 之类）会被直接点破，不再误导去检查日期范围。AI 助手绘图
  现经队列信号转回 GUI 线程，修掉 plot_timeseries 在工作线程直接改抽屉控件导致的偶发闪退。
  采样过程也在聊天里实时显示进度（单行刷新），⏹ 可在两个 granule 之间中断——温度序列
  过去要在慢速 GES DISC 网关上静默磨几分钟。结果现带图层长名与原生单位（T2M 是开尔文，
  °C = K − 273.15），一串 264~277 的裸数值不会再被模型读成"加密货币价格"；模型的空回复
  现在会自动重试（仍空则在聊天里报错），不再无声收尾、让抽屉看起来像卡死了。过短的
  图层提示（<3 字符）不再子串乱匹配——单独一个 'T' 曾把 CLDTMP（云顶温度）错当成 T2M——
  而是报错并列出可用图层名；取数成功的结果还会直接指挥助手下一步调用 plot_timeseries 画图。
  超过 6000 字符工具结果预算的长序列会被自适应压缩、series_id 固定在开头——过去循环在点列数组
  中间硬切，恰好砍掉模型最需要的那个字段（DS 亲口诊断出了这一点）。MERRA-2 逐小时
  时间戳改用文件原生 00:30~23:30 顺序标注——旧的 (h+1)%24 卷绕把每天最后一小时倒标到
  00:30，图上画出跨天倒折线；助手欢迎语同时注明了折线连线规则与原生单位
- **2026-10 v2.2.0** — AI 助手改版为右缘悬浮抽屉：数据界面不再受影响，API 设置
  挪进弹出对话框，聊天区支持自定义背景图
- **2026-10 v2.1.1** — 修复：AI 助手下载确认（点 Yes 却报"用户拒绝"——PySide6
  `Signal(dict)` 跨线程排队连接会拷贝载荷，改用 `Signal(object)`）；MCP 服务器
  从 ~/.netrc 懒恢复已保存的 Earthdata 登录态
- **2026-10 v2.1.0** — MCP 服务器（`d3ltool-mcp`：stdio 上 9 个工具，供 Claude Desktop /
  Cursor / ZCode 调用，复用本机登录凭据）与软件内 AI 助手对话页（任意 OpenAI 兼容服务商、
  agent 工具调用、下载弹窗确认、共享下载任务表）
- **2026-09 v2.0.3** — 产品目录窗口（按卫星浏览产品/版本/说明、可筛选、双击选用）；CI 因 GitHub 退役 macos-13 Intel runner 改为仅 Apple Silicon 构建（Intel Mac 用户用 `pip install d3ltool`）
- **2026-09 v2.0.2** — Earthdata 登录彻底修复：适配 earthaccess 0.19 认证单例、启动时自动从本机 netrc 恢复会话、登录失败提示精准化（401/网络/账号受限）
- **2026-09 v2.0.0** — 全新重构：earthaccess/CMR 检索、瓦片地图、断点续传、PySide6 双语界面、跨平台
- **2018-04-27 v1.0** — 首个版本（浏览器模拟订单下载）
