# AGENTS.md — D3LTool 维护约定

本项目是 D3LTool（NASA MODIS/VIIRS/MERRA-2 数据检索与下载工具，PySide6 GUI
+ CLI + MCP 服务器 + 内置 AI 助手）。对 agent 的硬约定：

1. **发版或改动版本号时，必须完整执行 `docs/RELEASE.md`**：那份文件定义了
   需要同步更新的 12 个文件矩阵、统一口径句式、"活数字"（工具数/测试数/版本号）
   的自动来源，以及收尾自检。不要只改代码不改对外文案。
2. **Git 操作（add / commit / push / tag）一律由作者本人执行**，agent 只给出
   命令与提交信息建议；凭据走本机 netrc，Earthdata 密码永远不出现在对话、
   工具参数或日志里。
3. 对外定位口径：检索与下载为主，附带功能（点位时间序列采样与绘图等）以
   "since vX.Y / lightweight" 措辞缀后；不称"数据分析"。详见
   `docs/RELEASE.md` §0。
4. **两包版本叙事统一（v2.7.0 起生效）**：对外文档互称"配套/同步迭代"时，
   glass.sqdaitools 的版本号以其实际迭代为准（当前 **v0.5.0**）。R 包发新
   版本后全文 grep 更新——只改"对齐/同步/修复轮同步"类的动态描述；
   **不改历史事实**：引擎移植自 v0.1.0 的溯源句、changelog 历史条目、
   `≥ 0.1.0` API 下限兼容行、指向 R 包 v0.1.0 tag 的源码链接。自检：
   ```bash
   grep -rn "0\.[0-9]\.0" README.md READMEcn.md index.html index-cn.html \
     paper/paper.md docs/*.md
   ```
   输出逐条判定"动态对齐 vs 历史事实"后再动手。
