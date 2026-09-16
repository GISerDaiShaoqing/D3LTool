# D3L Tool of NASA Satellite 用户手册（软著申请用草稿）

> 提交前请补齐：① 开发完成日期 ② 首次发表日期（无则填"未发表"）③ 正式定稿的软件全称
> （建议：`D3LTool NASA卫星数据下载软件 V2.0.2`，全称必须与本手册页眉、申请表一致）。
> 截图建议使用 `images/Main2.png` 与运行中的程序截图。

## 一、软件概述

D3L Tool of NASA Satellite（简称 D3LTool）是一款用于检索与下载美国 NASA
对地观测卫星数据的桌面应用软件，支持 MODIS、VIIRS（LAADS DAAC）与
MERRA-2（GES DISC）产品。软件以 NASA 官方 earthaccess 库与 CMR 检索服务
为基础，将登录、检索、下载全流程集成于同一图形界面内，提供中文/English
双语切换、可点击的正弦瓦片地图、多线程断点续传下载队列以及命令行接口。

本软件由戴劭勍开发。2018 年发布的 v1.0 采用浏览器模拟方式批量下载订单数据；
2026 年发布的 v2.0 在现代技术栈上整体重构，不再依赖浏览器，也不再需要去
NASA 网站人工创建订单。

## 二、运行环境

- 操作系统：Windows 10/11（64 位），或 macOS 12+，或主流 Linux 发行版
- 运行方式：双击独立安装包 `D3LToolNASA.exe`（Windows，无需安装 Python），
  或安装 Python 3.10+ 后执行 `python -m pip install -e .` 并运行 `d3ltool-gui`
- 网络：需访问 ladsweb.modaps.eosdis.nasa.gov、urs.earthdata.nasa.gov、
  disc.gsfc.nasa.gov 等站点；支持在"设置"中配置 HTTP/SOCKS 代理

## 三、安装与启动

1. 从 GitHub Releases 或官网下载对应平台的安装包；
2. Windows 用户双击 `D3LToolNASA.exe` 直接启动（首次启动解压约 2-3 秒）；
3. macOS 首次打开如被 Gatekeeper 拦截，右键选择"打开"或执行
   `xattr -cr D3LToolNASA.app`；
4. 亦可 `pip install d3ltool` 后运行 `d3ltool-gui`（图形界面）或 `d3ltool`（命令行）。

## 四、主要功能与操作步骤

### 4.1 登录 NASA Earthdata 账号

1. 菜单"设置 → 登录 Earthdata"，输入在 https://urs.earthdata.nasa.gov 注册的
   用户名与密码（免费注册；用户名不是邮箱）；
2. 检索不需要登录；下载需要登录；
3. 登录成功后凭据持久化保存在本机用户目录的 `_netrc` 文件中（仅本机保存，
   不上传），下次启动软件自动恢复登录状态。

### 4.2 检索数据

1. 在左侧"产品"卡片选择产品组（MODIS Terra / Aqua / Combined、VIIRS、
   MERRA-2），点击"产品目录"按钮可打开产品目录窗口浏览各卫星的全部产品、
   版本与中文说明，双击即可填入产品与版本；也可在"自定义产品 / Custom"分组
   直接输入任意 CMR short_name；
2. 选择开始/结束日期；
3. 选择区域（三种方式任选）：
   - 在正弦瓦片地图上直接点击选择 MODIS/VIIRS 瓦片（可多选），
     或在输入框中填写 `h04v03` 等瓦片号（多个用逗号分隔），
     或输入经纬度后点击"定位到瓦片"；
   - 在"经纬度范围 bbox"中填写左下/右上经纬度（适用于 MERRA-2 等数据）；
4. 点击红色"检索"按钮，检索结果显示在右上表格中（文件名/日期/瓦片/大小）。

### 4.3 下载数据

1. 在结果表中勾选需要的文件，点击"加入下载队列"；
2. 右下任务表实时显示每个文件的进度、速度与状态，支持暂停/继续/重试；
3. 已完成的文件再次下载会自动跳过，中断的文件自动断点续传；
4. 下载目录、并发数与代理在"设置"对话框中配置，设置保存在
   `~/.d3ltool/config.json`。

### 4.4 命令行接口

```
d3ltool login                                  # 登录并持久化凭据
d3ltool search VNP46A1 --start 2020-03-01 --end 2020-03-31 --tile h04v03
d3ltool download VNP46A1 --start 2020-03-01 --end 2020-03-31 --tile h04v03 --dest D:/data
d3ltool search M2T1NXSLV --start 2019-08-01 --end 2019-08-31 --bbox 100 20 120 40
```

### 4.5 其他功能

- "网站"菜单：程序官网、作者博客与 NASA 官方入口；
- "遥感资源"菜单：整理的常用遥感资源清单；
- "帮助"菜单：打赏（支付宝收款码）与关于信息；
- "语言"菜单：中文 / English 一键切换（重启后生效）。

## 五、常见问题

1. **下载 401/403**：请确认 Earthdata 账号有效，并到 LAADS/GES DISC 网站登录
   并同意相应数据使用协议（EULA）；
2. **下载速度慢**：请检查代理设置；LAADS/GES DISC 国内直连速度不稳定属正常
   现象，工具支持断点续传，中断后重试即可；
3. **登录提示 401**：用户名或密码不正确，请先在浏览器验证账号；
4. **文件未下载完整**：任务表显示"失败"时可右键重试，已下载部分自动续传。

## 六、技术支持

邮箱：dsq1993qingge@163.com
问题反馈：https://github.com/GISerDaiShaoqing/D3LTool/issues
