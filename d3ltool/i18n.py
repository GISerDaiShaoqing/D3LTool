# -*- coding: utf-8 -*-
"""Bilingual string table (zh / en). All UI text comes from here via tr()."""

_current = {"lang": "zh"}

STRINGS = {
    "zh": {
        "app_title": "D3L Tool of NASA Satellite",
        "menu_help": "帮助",
        "menu_language": "语言",
        "menu_settings": "设置",
        "menu_about": "关于",
        "act_login": "登录 Earthdata",
        "act_logout": "退出登录",
        "act_settings": "设置...",
        "act_about": "关于",
        "act_quit": "退出",
        "lang_zh": "中文",
        "lang_en": "English",
        "status_logged_in": "已登录：{user}",
        "status_logged_out": "未登录（仅检索可用）",
        "login_title": "登录 NASA Earthdata",
        "login_username": "用户名",
        "login_password": "密码",
        "login_remember": "记住用户名",
        "login_ok": "登录",
        "login_cancel": "取消",
        "login_hint": "检索不需要登录；下载需要 Earthdata 账号（凭据仅保存在本机 ~/.netrc）",
        "login_running": "正在登录...",
        "login_success": "登录成功",
        "login_failed": "登录失败：{reason}",
        "login_need_account": "还没有账号？在 urs.earthdata.nasa.gov 免费注册",
        "auth_bad_credentials": "Earthdata 用户名或密码不正确（URS 返回 401）。"
                                "请先用浏览器在 https://urs.earthdata.nasa.gov 登录验证："
                                "用户名不是邮箱；注意输入法可能引入全角字符或首尾空格；"
                                "忘记密码可在该页面重置。",
        "auth_network": "无法连接 urs.earthdata.nasa.gov，请检查网络或代理设置。",
        "auth_blocked": "Earthdata 拒绝了本次登录（账号被锁定/受限或需要先在浏览器完成一次登录验证）。"
                        "请先用浏览器登录 https://urs.earthdata.nasa.gov 后重试。",
        "auth_urs_ok_but_failed": "URS 认可该账号，但登录流程未完成：{detail}。请重试一次；"
                                  "若仍失败请到 GitHub Issues 反馈。",
        "auth_earthaccess_generic": "Earthdata 登录未完成：{detail}。"
                                    "若提示 EULA/权限，请先在 https://urs.earthdata.nasa.gov 登录并确认已同意相应 DAAC 协议。",
        "group_product": "产品",
        "group_time": "时间范围",
        "group_area": "区域",
        "label_product_group": "产品组",
        "label_product": "产品",
        "label_custom": "自定义",
        "label_version": "版本(可选)",
        "btn_catalog": "产品目录",
        "catalog_title": "产品目录",
        "catalog_all": "全部",
        "catalog_filter": "筛选",
        "catalog_filter_hint": "按产品名或说明筛选，如 夜光 / NDVI / MERRA",
        "catalog_hint": "双击行或点“选用”即可填入主面板的产品与版本",
        "col_group": "卫星/数据集",
        "col_shortname": "产品 short_name",
        "col_version": "版本",
        "col_desc": "说明",
        "btn_use_product": "选用",
        "label_start": "开始日期",
        "label_end": "结束日期",
        "label_tile": "瓦片",
        "tile_hint": "点击下方瓦片图选择（可多选）；或直接填写，如 h04v03，多个用逗号分隔",
        "label_locate": "经纬度定位",
        "locate_btn": "定位到瓦片",
        "label_bbox": "经纬度范围 bbox（MERRA-2 等）",
        "label_bbox_tip": "格式：左下经度,左下纬度,右上经度,右上纬度，如 100,20,120,40",
        "label_limit": "结果上限",
        "btn_search": "检索",
        "btn_cancel_search": "取消检索",
        "search_running": "正在检索 {product} ...",
        "search_done": "检索完成：{n} 条结果（{secs:.1f} 秒）",
        "search_failed": "检索失败：{reason}",
        "search_none": "没有检索到数据，请调整条件（时间/瓦片/版本）后重试",
        "results_title": "检索结果",
        "results_col_check": "选",
        "results_col_name": "文件名",
        "results_col_date": "日期",
        "results_col_tile": "瓦片",
        "results_col_size": "大小(MB)",
        "btn_select_all": "全选",
        "btn_select_none": "全不选",
        "btn_enqueue": "加入下载队列",
        "tasks_title": "下载任务",
        "tasks_col_file": "文件",
        "tasks_col_state": "状态",
        "tasks_col_progress": "进度",
        "tasks_col_speed": "速度",
        "tasks_col_size": "大小",
        "state_pending": "等待中",
        "state_running": "下载中",
        "state_done": "已完成",
        "state_skipped": "已存在，跳过",
        "state_failed": "失败",
        "state_paused": "已暂停",
        "state_canceled": "已取消",
        "btn_pause": "暂停",
        "btn_resume": "继续",
        "btn_retry": "重试",
        "btn_clear_done": "清除已完成",
        "btn_open_dir": "打开下载目录",
        "msg_enqueue_none": "请先在结果表中勾选要下载的文件",
        "msg_need_login": "下载需要先登录 Earthdata 账号",
        "msg_lang_restart": "语言已切换为 {lang}，重启程序后界面语言生效。",
        "tab_data": "数据",
        "tab_agent": "AI 助手",
        "act_agent": "AI 助手",
        "agent_input_hint": "输入问题，Enter 发送（Shift+Enter 换行）",
        "agent_send": "发送",
        "agent_stop": "停止",
        "agent_clear": "清空对话",
        "agent_you_label": "你：",
        "agent_ai_label": "AI：",
        "agent_settings": "AI 服务设置（OpenAI 兼容）",
        "agent_base_url": "API 地址",
        "agent_model": "模型",
        "agent_api_key": "API Key",
        "agent_key_placeholder": "sk-...",
        "agent_test": "测试连接",
        "agent_testing": "正在测试...",
        "agent_test_ok": "连接成功 ✓",
        "agent_test_fail": "连接失败：{reason}",
        "agent_need_setup": "请先填写：{fields}",
        "agent_key_note": "API Key 仅保存在本机 ~/.d3ltool/config.json，只发送给你填写的服务商；Earthdata 密码永远不会经过对话。",
        "agent_gear": "设置",
        "agent_hide": "收起",
        "agent_bg": "聊天背景（留空恢复默认）",
        "agent_bg_pick": "浏览...",
        "agent_bg_clear": "清除",
        "agent_drawer_tip": "打开 AI 助手",
        "agent_welcome": "这是内置 AI 助手。点右上角 ⚙ 填好 API 地址与 Key 后，可用自然语言下载数据（例：“2020 年 1 月北京的夜光数据帮我下载”），也可以直接计算并绘制任意点位的时间序列（例：“帮我画禹城 2010 年的 NDVI 序列”）。工具与 MCP 服务器共用；下载会先弹窗确认。",
        "agent_tool_run": "调用工具 {name}",
        "agent_confirm_title": "确认下载",
        "agent_confirm_text": "AI 请求执行 {name}，允许吗？",
        "agent_system_prompt": "你是 NASA 数据工具 D3LTool 的内置 AI 助手。工具分三组："
                               "1) 点位时间序列——point_timeseries(经纬度+产品+起止日期) 直接从 "
                               "NASA OPeNDAP 采样单像元序列（MODIS/VIIRS/MERRA-2，无需下载整景"
                               "文件），返回点列与 series_id；在软件内接着调 plot_timeseries"
                               "(series_id) 即可把序列画进时间序列抽屉。"
                               "2) 检索下载——search_granules 检索 granule、start_download 提交"
                               "下载队列、download_status/cancel_download/retry_download 管理"
                               "任务。"
                               "3) 辅助——check_auth 查登录、list_products 查产品目录、"
                               "point_to_tile/tile_bounds 经纬度与瓦片换算。"
                               "规则：1) 用户要“时间序列/趋势/折线图/某点的变化”时直接用 "
                               "point_timeseries，不要检索或下载整景影像；2) 画完图后用一两句话"
                               "总结数据特征（趋势、季节性、异常值）；3) 只有用户明确要“文件/"
                               "影像”时才走 search_granules→start_download；4) 产品名/文件名/"
                               "瓦片号必须用工具查询，不要编造；5) start_download 会弹窗请用户"
                               "确认，被拒绝时不要反复重试；6) 未登录时检索仍可用，下载与序列采样"
                               "需要登录（not_authenticated 时引导用户在主界面登录 Earthdata，"
                               "密码不经过对话）；7) 用用户的语言简洁回答。",
        "tab_ts": "时间序列",
        "act_ts": "时间序列",
        "ts_drawer_tip": "打开时间序列",
        "ts_product_ph": "LAADS 产品 short_name，如 MOD13Q1 / MOD11A2 / VNP46A1",
        "ts_layer": "图层",
        "ts_lat": "纬度",
        "ts_lon": "经度",
        "ts_lat_ph": "36.833",
        "ts_lon_ph": "116.567",
        "ts_plot": "绘制折线图",
        "ts_export": "导出 CSV",
        "ts_clear": "清空图表",
        "ts_exported": "已导出：{path}",
        "ts_nothing": "还没有可导出的序列——先绘制一次",
        "ts_need_fields": "请先填写：{fields}",
        "ts_field_product": "产品",
        "ts_bad_coords": "纬度需在 -90~90，经度需在 -180~180",
        "ts_bad_dates": "开始日期需早于或等于结束日期",
        "ts_stage_search": "正在检索该坐标所在瓦片的数据文件（CMR）...",
        "ts_odap_sample": "LAADS 直采：{i}/{n}（{date}）",
        "ts_done": "绘制完成：{source} / {layer}，{n} 个有效点（{start} ~ {end}）",
        "ts_no_data": "该时段没有有效数值（可能被云/QA 掩膜，或产品未覆盖该点）",
        "ts_unsupported": "时间序列目前支持 MODIS/VIIRS（LAADS 档案）与 MERRA-2 产品；{product} 暂不支持",
        "ts_no_granules": "没有找到 {product} 的数据文件（瓦片 {tile}，{start} ~ {end}）——请检查日期范围",
        "ts_no_granules_url": "CMR 里找到了 {product}，但它的 OPeNDAP 链接缺失——请到 GitHub Issues 反馈",
        "ts_failed": "时间序列获取失败：{reason}",
        "ts_api_note": "单像元时间序列由 NASA OPeNDAP 直采：MODIS/VIIRS 走 LAADS，MERRA-2 走 GES DISC 云网关（复用本机登录凭据，直连可用、无需 AppEEARS）。",
        "settings_title": "设置",
        "settings_download_dir": "下载目录",
        "settings_browse": "浏览...",
        "settings_workers": "并发下载数",
        "settings_proxy": "代理（留空不使用，如 http://127.0.0.1:7890 或 socks5://...）",
        "settings_saved": "设置已保存",
        "about_text": "D3L Tool of NASA Satellite\n\n"
                      "NASA MODIS / VIIRS / MERRA-2 数据检索与下载工具，附点位时间序列采样\n\n"
                      "v2.0 © 2026 GLM-5.3-Flash 基于 earthaccess / CMR 重构 · \n\n"
                      "v1.0 © 2018 戴劭勍 (dsq1993qingge@163.com)\n\n"
                      "官网: https://gisersqdai.top/D3LTool/",
        "menu_sites": "网站",
        "menu_rs": "遥感资源",
        "site_home": "程序官网",
        "site_blog": "作者博客",
        "site_nasa": "NASA LAADS DAAC",
        "site_nasa_tools": "NASA 工具与服务",
        "rs_envi": "ENVI-IDL技术殿堂",
        "rs_cpeos": "国家遥感数据与应用服务平台",
        "rs_chinageo": "国家综合地球观测数据共享平台",
        "rs_gscloud": "地理空间数据云",
        "rs_nrscc": "国家遥感中心",
        "rs_usgs": "USGS Landsat",
        "rs_cresda": "中国资源卫星应用中心",
        "act_donate": "打赏",
        "donate_text": "您的支持是对软件开发者最大的鼓励！",
        "err_title": "错误",
        "info_title": "提示",
    },
    "en": {
        "app_title": "D3L Tool of NASA Satellite",
        "menu_help": "Help",
        "menu_language": "Language",
        "menu_settings": "Settings",
        "menu_about": "About",
        "act_login": "Sign in to Earthdata",
        "act_logout": "Sign out",
        "act_settings": "Settings...",
        "act_about": "About",
        "act_quit": "Quit",
        "lang_zh": "中文",
        "lang_en": "English",
        "status_logged_in": "Signed in: {user}",
        "status_logged_out": "Not signed in (search still works)",
        "login_title": "Sign in to NASA Earthdata",
        "login_username": "Username",
        "login_password": "Password",
        "login_remember": "Remember username",
        "login_ok": "Sign in",
        "login_cancel": "Cancel",
        "login_hint": "Search works without login; downloads need an Earthdata account "
                      "(credentials are stored only in ~/.netrc on this machine)",
        "login_running": "Signing in...",
        "login_success": "Signed in",
        "login_failed": "Sign-in failed: {reason}",
        "login_need_account": "No account? Register free at urs.earthdata.nasa.gov",
        "auth_bad_credentials": "Earthdata username or password is incorrect (URS 401). "
                                "Verify by signing in at https://urs.earthdata.nasa.gov in a browser: "
                                "the username is not an email; watch for full-width IME characters "
                                "or stray spaces; reset the password there if needed.",
        "auth_network": "Cannot reach urs.earthdata.nasa.gov; check network or proxy settings.",
        "auth_blocked": "Earthdata refused this sign-in (account locked/restricted, or a one-time "
                        "browser verification is required). Sign in at https://urs.earthdata.nasa.gov first, then retry.",
        "auth_urs_ok_but_failed": "URS accepts this account but the login flow did not complete: {detail}. "
                                  "Please retry; if it persists, report it on GitHub Issues.",
        "auth_earthaccess_generic": "Earthdata login did not complete: {detail}. "
                                    "If EULA/permissions are mentioned, sign in at https://urs.earthdata.nasa.gov "
                                    "and accept the relevant DAAC agreement.",
        "group_product": "Product",
        "group_time": "Time range",
        "group_area": "Area",
        "label_product_group": "Group",
        "label_product": "Product",
        "label_custom": "Custom",
        "label_version": "Version (optional)",
        "btn_catalog": "Catalog",
        "catalog_title": "Product catalog",
        "catalog_all": "All",
        "catalog_filter": "Filter",
        "catalog_filter_hint": "filter by name or description, e.g. night / NDVI / MERRA",
        "catalog_hint": "Double-click a row or press 'Use' to fill the product and version",
        "col_group": "Satellite / dataset",
        "col_shortname": "short_name",
        "col_version": "Version",
        "col_desc": "Description",
        "btn_use_product": "Use",
        "label_start": "Start date",
        "label_end": "End date",
        "label_tile": "Tiles",
        "tile_hint": "Click the tile map below to select (multi-select); or type e.g. h04v03, comma separated",
        "label_locate": "Locate by lat/lon",
        "locate_btn": "Locate tile",
        "label_bbox": "Bounding box (MERRA-2 etc.)",
        "label_bbox_tip": "Format: west,south,east,north, e.g. 100,20,120,40",
        "label_limit": "Max results",
        "btn_search": "Search",
        "btn_cancel_search": "Cancel search",
        "search_running": "Searching {product} ...",
        "search_done": "Search done: {n} granules ({secs:.1f} s)",
        "search_failed": "Search failed: {reason}",
        "search_none": "No granules found; try adjusting time / tiles / version",
        "results_title": "Search results",
        "results_col_check": "Sel",
        "results_col_name": "File",
        "results_col_date": "Date",
        "results_col_tile": "Tile",
        "results_col_size": "Size (MB)",
        "btn_select_all": "Select all",
        "btn_select_none": "Select none",
        "btn_enqueue": "Add to download queue",
        "tasks_title": "Downloads",
        "tasks_col_file": "File",
        "tasks_col_state": "State",
        "tasks_col_progress": "Progress",
        "tasks_col_speed": "Speed",
        "tasks_col_size": "Size",
        "state_pending": "Pending",
        "state_running": "Downloading",
        "state_done": "Done",
        "state_skipped": "Exists, skipped",
        "state_failed": "Failed",
        "state_paused": "Paused",
        "state_canceled": "Canceled",
        "btn_pause": "Pause",
        "btn_resume": "Resume",
        "btn_retry": "Retry",
        "btn_clear_done": "Clear finished",
        "btn_open_dir": "Open download folder",
        "msg_enqueue_none": "Select files in the results table first",
        "msg_need_login": "Please sign in to Earthdata before downloading",
        "msg_lang_restart": "Language switched to {lang}. Restart the app to apply.",
        "tab_data": "Data",
        "tab_agent": "AI Assistant",
        "act_agent": "AI Assistant",
        "agent_input_hint": "Type a question; Enter sends (Shift+Enter for a newline)",
        "agent_send": "Send",
        "agent_stop": "Stop",
        "agent_clear": "Clear chat",
        "agent_you_label": "You:",
        "agent_ai_label": "AI:",
        "agent_settings": "AI provider (OpenAI-compatible)",
        "agent_base_url": "Base URL",
        "agent_model": "Model",
        "agent_api_key": "API Key",
        "agent_key_placeholder": "sk-...",
        "agent_test": "Test connection",
        "agent_testing": "Testing...",
        "agent_test_ok": "Connection OK ✓",
        "agent_test_fail": "Connection failed: {reason}",
        "agent_need_setup": "Please fill in: {fields}",
        "agent_key_note": "The API key is stored only in ~/.d3ltool/config.json on this "
                          "machine and sent only to the provider you chose; your Earthdata "
                          "password never passes through the chat.",
        "agent_gear": "Settings",
        "agent_hide": "Hide",
        "agent_bg": "Chat background (empty = default)",
        "agent_bg_pick": "Browse...",
        "agent_bg_clear": "Clear",
        "agent_drawer_tip": "Open AI assistant",
        "agent_welcome": "This is the built-in AI assistant. Open ⚙ (top right) to fill in "
                         "the provider and API key, then just ask, e.g. “download the January "
                         "2020 nighttime lights around Beijing”, or have it compute and plot "
                         "a point time series, e.g. “plot the 2010 NDVI series at Yucheng”. "
                         "It shares the tool set with the MCP server; downloads ask for "
                         "confirmation first.",
        "agent_tool_run": "calling tool {name}",
        "agent_confirm_title": "Confirm download",
        "agent_confirm_text": "The AI wants to run {name}. Allow it?",
        "agent_system_prompt": "You are the built-in AI assistant of D3LTool, a NASA data "
                               "tool. Tools come in three groups: 1) point time series — "
                               "point_timeseries(lon/lat + product + date range) samples a "
                               "single pixel's series straight from NASA OPeNDAP "
                               "(MODIS/VIIRS/MERRA-2, no whole-file downloads) and returns "
                               "the points plus a series_id; inside the desktop app follow "
                               "with plot_timeseries(series_id) to draw it in the "
                               "time-series drawer. 2) search & download — search_granules "
                               "(CMR search), start_download (queue, asks confirmation), "
                               "download_status / cancel_download / retry_download. "
                               "3) helpers — check_auth (sign-in state), list_products "
                               "(catalog), point_to_tile / tile_bounds (tile math). "
                               "Rules: 1) for 'time series / trend / line chart / how a "
                               "point changed' requests call point_timeseries directly — "
                               "never search or download whole granules for that; 2) after "
                               "plotting, summarise the series in a sentence or two (trend, "
                               "seasonality, outliers); 3) only walk search_granules → "
                               "start_download when the user explicitly asks for files or "
                               "imagery; 4) look up product names, files and tiles with "
                               "tools, never invent them; 5) start_download pops a "
                               "confirmation dialog — if declined, do not retry "
                               "repeatedly; 6) without sign-in, search still works but "
                               "downloads and series sampling need it (not_authenticated → "
                               "guide the user to sign in on the main window; the password "
                               "never passes through chat); 7) answer in the user's "
                               "language, concisely.",
        "tab_ts": "Time series",
        "act_ts": "Time series",
        "ts_drawer_tip": "Open the time-series drawer",
        "ts_product_ph": "LAADS product short_name, e.g. MOD13Q1 / MOD11A2 / VNP46A1",
        "ts_layer": "Layer",
        "ts_lat": "Lat",
        "ts_lon": "Lon",
        "ts_lat_ph": "36.833",
        "ts_lon_ph": "116.567",
        "ts_plot": "Plot series",
        "ts_export": "Export CSV",
        "ts_clear": "Clear chart",
        "ts_exported": "Exported: {path}",
        "ts_nothing": "Nothing to export yet — plot a series first",
        "ts_need_fields": "Please fill in: {fields}",
        "ts_field_product": "product",
        "ts_bad_coords": "Latitude must be within -90..90, longitude within -180..180",
        "ts_bad_dates": "The start date must be on or before the end date",
        "ts_stage_search": "Listing the granules of the tile covering the point (CMR)...",
        "ts_odap_sample": "LAADS direct sampling: {i}/{n} ({date})",
        "ts_done": "Plotted {source} / {layer}: {n} valid points ({start} ~ {end})",
        "ts_no_data": "No valid values in this period (cloud/QA masked, or the point is not covered)",
        "ts_unsupported": "Time series currently supports MODIS/VIIRS (LAADS archive) and "
                          "MERRA-2 products; {product} is not supported yet",
        "ts_no_granules": "No granules found for {product} (tile {tile}, {start} ~ {end}) — "
                          "check the date range",
        "ts_no_granules_url": "{product} exists in CMR but carries no OPeNDAP link — "
                              "please report this on GitHub Issues",
        "ts_failed": "Time series failed: {reason}",
        "ts_api_note": "Pixel series are sampled directly via NASA OPeNDAP: MODIS/VIIRS from "
                       "LAADS, MERRA-2 from the GES DISC cloud gateway (same credentials as "
                       "the downloader, reachable without a proxy and without AppEEARS).",
        "settings_title": "Settings",
        "settings_download_dir": "Download folder",
        "settings_browse": "Browse...",
        "settings_workers": "Concurrent downloads",
        "settings_proxy": "Proxy (blank = none, e.g. http://127.0.0.1:7890 or socks5://...)",
        "settings_saved": "Settings saved",
        "about_text": "D3L Tool of NASA Satellite\n\n"
                      "Search & download NASA MODIS / VIIRS / MERRA-2 data, plus point time-series sampling\n\n"
                      "v2.0 © 2026 GLM-5.3-Flash Rebuilt on earthaccess / CMR · \n\n"
                      "v1.0 © 2018 Dai Shaoqing (dsq1993qingge@163.com)\n\n"
                      "Website: https://gisersqdai.top/D3LTool/",
        "menu_sites": "Websites",
        "menu_rs": "RS resources",
        "site_home": "Project website",
        "site_blog": "Author's blog",
        "site_nasa": "NASA LAADS DAAC",
        "site_nasa_tools": "NASA tools & services",
        "rs_envi": "ENVI-IDL技术殿堂",
        "rs_cpeos": "国家遥感数据与应用服务平台",
        "rs_chinageo": "国家综合地球观测数据共享平台",
        "rs_gscloud": "地理空间数据云",
        "rs_nrscc": "国家遥感中心",
        "rs_usgs": "USGS Landsat",
        "rs_cresda": "中国资源卫星应用中心",
        "act_donate": "Donate",
        "donate_text": "Your support means a lot to the developer!",
        "err_title": "Error",
        "info_title": "Info",
    },
}


def set_language(lang: str) -> None:
    if lang in STRINGS:
        _current["lang"] = lang


def get_language() -> str:
    return _current["lang"]


def tr(key: str, **kw) -> str:
    text = STRINGS.get(_current["lang"], {}).get(key)
    if text is None:
        text = STRINGS["en"].get(key, key)
    if kw:
        try:
            text = text.format(**kw)
        except (KeyError, IndexError, ValueError):
            pass
    return text
