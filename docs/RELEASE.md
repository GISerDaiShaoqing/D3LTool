# 发版文档规范（v2.3.0 起生效）

> 本文件定义每次发版或改动版本号时**必须同步更新的全部文件**，供 ZCode 等
> agent 自动执行，也适用于人工对照。目标：版本号、工具数、测试数与各处对外
> 描述永远一致，作者不需要逐个文件人工核对。
> **Git 操作（add / commit / push / tag）一律由作者本人执行**，agent 只准备命令。

## 0. 统一口径（所有对外文案必须遵守）

1. 主定位永远是 **NASA 数据检索与下载工具**；时间序列等附带功能以
   "附带 / since vX.Y / lightweight" 措辞放在主定位之后，不进主定位、
   不进软著登记名称。
2. 时序功能只叫 **"点位时间序列采样与绘图"**（英文 point time-series
   sampling & plotting），不写 "数据分析 / analysis" —— 功能边界是取序列、
   画折线、导 CSV。
3. 凡提到时序功能的轻量场景，末尾补一句定位提醒：大范围、长序列的正式分析
   建议检索并下载原始数据后离线处理。
4. 中文主句式：
   > 免费开源的 NASA 卫星数据**检索与下载**工具：登录 → 检索 → 下载全流程在
   > 软件内完成；v{X.Y} 起还支持单像元时间序列采样与软件内绘图（OPeNDAP 直采）。
5. 英文主句式：
   > A free & open-source tool to **search and download** NASA Earth science
   > data — the whole workflow in one app — and, since v{X.Y}, to sample a
   > pixel's time series over OPeNDAP and plot it in-app.

## 1. 发版文件矩阵（按序执行，一个不漏）

| # | 文件 | 改什么 | 说明 |
|---|---|---|---|
| 1 | `pyproject.toml` | `[project] version`；`description` 按口径微调 | |
| 2 | `d3ltool/__init__.py` | `__version__` | 源码文档生成器自动读它 |
| 3 | `CITATION.cff` | `version`、`date-released`；新功能时补 abstract 一句与 keywords | |
| 4 | `README.md` | 定位变化时改首段；新功能加 Features 条目；`## Changelog` 顶部加新条目 `- **YYYY-MM vX.Y.Z** — 要点` | 历史条目是事实，不改 |
| 5 | `READMEcn.md` | 同上，中文镜像 | |
| 6 | `index.html` / `index-cn.html` | 徽章版本、lede、meta description、新功能加 📈 风格卡片、MCP 工具数、指南新增小节 | 官网页面源码，随仓库走，作者手动部署到服务器 |
| 7 | `docs/mcp.md` | 工具表加行；Routing 段与实际路由一致 | MCP 客户端直接读它 |
| 8 | `d3ltool/i18n.py` | 新 UI 字符串 zh/en 同步加；`about_text`（zh/en）口径 | |
| 9 | `paper/paper.md`（JOSS） | 新功能加 tags / Summary 句 / Statement bullet / 模块说明；**工具数与测试数每次刷新** | 提交前删作者注释 |
| 10 | `docs/copyright/user_manual_zh.md` | 头部版本建议；概述；新功能章节（操作步骤与实际 UI 一致，控件名用界面实际文案） | 软著 |
| 11 | `docs/submission_checklist.md` | 版本号、开发完成/首次发表日期、Zenodo release 版本、pytest 数 | |
| 12 | `docs/copyright/source_code_document.txt` | 用命令重新生成：`python tools_gen_source_doc.py` | 页眉版本自动读取 `__init__.py`，禁止手改 |

## 2. "活数字"来源（禁止手数）

- **MCP/AI 工具数** = `len(d3ltool.tools.REGISTRY)`（当前 11）。
  引用处：README.md、READMEcn.md、index.html、index-cn.html、paper/paper.md、
  user_manual §4.6、docs/mcp.md。
- **pytest 测试数** = 全量 `python -m pytest tests/ -q` 末行 passed 数（当前 116）。
  引用处：paper/paper.md、docs/submission_checklist.md。
- **版本号**以 `d3ltool/__init__.py` 的 `__version__` 为准，pyproject.toml 与
  CITATION.cff 必须与它一致。

## 3. 流程

1. 代码与测试完成，全量 pytest 通过；
2. 按矩阵 1→12 顺序更新（12 用命令重新生成）；
3. 跑 §4 自检并向作者汇报：改了哪些文件、各自改了什么、自检输出；
4. 作者执行 commit 与 push；
5. 该版本要随 release 发布（新功能默认要）时，作者执行
   `git tag -f vX.Y.Z && git push -f origin vX.Y.Z`，CI 三平台自动构建并挂到
   GitHub Release；amend 过的提交需先 `git push --force-with-lease`；
6. 发版后作者把两个 index 页同步部署到官网服务器；
7. 若改了 `agent_system_prompt` / `agent_welcome`：提醒作者 AI 聊天需清空
   会话或重启软件才生效；
8. 提醒：纯文案轮次**不需要**重打 tag（网页/文档不进 release 产物），
   含代码功能的轮次**必须**重打（否则 release exe 缺功能，文实不符）。

### 版本号策略

- 小步功能/修复默认并入当前版本号；作者拍板"还是 X.Y.Z"时不 bump；
- 需要 bump 时三处同步：pyproject.toml、`__init__.py`、CITATION.cff；
- 软著登记版本 ≤ 当前发布版本；手册、源码文档页眉与申请表三者版本一致；
  登记全称用主功能命名，附带功能不进名称（在 `tools_gen_source_doc.py`
  顶部 `APP_NAME` 常量处改）。

## 4. 自检（改完后逐条跑，输出随汇报给出）

```bash
# ① 版本号三处 + 官网徽章一致
grep -n 'version = "' pyproject.toml && grep -n '__version__' d3ltool/__init__.py \
  && grep -n '^version:' CITATION.cff && grep -n 'badge">v' index.html index-cn.html

# ② 上一版本号残留（应无输出；模式按"上一个版本号"滚动更新）
grep -rn "v2\.2\.0\|V2\.0\.2\|v2\.0\.3" README.md READMEcn.md index.html index-cn.html \
  docs/*.md docs/copyright/*.md paper/paper.md CITATION.cff | grep -v "Changelog\|变更记录\|v2\.0\.3+"

# ③ 工具数与测试数
python -c "import d3ltool.tools as t; print(len(t.REGISTRY))"
python -m pytest tests/ -q
```

## 5. 永不回改的部分

- Changelog 历史条目与 `docs/legacy/`（v1 描述是历史事实）；
- `images/` 截图（UI 改版才换图，换图需作者现截）；
- 已提交登记的软著旧版材料。
