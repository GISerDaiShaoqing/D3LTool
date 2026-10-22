# MCP 服务器与 AI 助手接入指南 / MCP server & AI Assistant guide

自 v2.1.0 起，D3LTool 有两条 AI 通道，共用同一套工具：

1. **MCP 服务器**（`d3ltool-mcp`）—— 供 Claude Desktop、Cursor、ZCode 等外部 AI 客户端调用；
2. **软件内 AI 助手**（GUI 右缘滑出的“AI 助手”抽屉）—— 自带 API Key 的 OpenAI 兼容 agent，不出软件即可对话完成任务。

Since v2.1.0, D3LTool exposes one shared tool set over **two channels**:
an **MCP server** for external AI clients, and a built-in **AI Assistant**
drawer that slides out from the right edge of the GUI.

## 工具清单 / Tool set

| 工具 | 作用 |
| --- | --- |
| `check_auth` | 查询本机 Earthdata 登录状态 |
| `list_products` | 内置产品目录（MODIS / VIIRS / MERRA-2，按组筛选） |
| `point_to_tile` | 经纬度 → 正弦瓦片 (h, v) 及范围 |
| `tile_bounds` | h/v → 瓦片地理范围 |
| `search_granules` | CMR 检索：short_name + 时间 + 瓦片/范围，返回文件名/日期/大小/下载地址 |
| `start_download` | 把 URL 加入下载队列（断点续传），返回任务 id |
| `download_status` | 查询下载进度（状态/大小/速度/失败原因） |
| `cancel_download` / `retry_download` | 按任务 id 取消 / 重试 |

**凭证模型 / Credentials**: 检索匿名即可；下载工具复用本机已登录的 Earthdata 凭据
（GUI 登录一次会持久化到 `~/.netrc`（Windows `_netrc`），CLI 用 `d3ltool login`）。
**用户名/密码永远不会作为工具参数**出现在对话或 MCP 消息里。

Search is anonymous; download tools reuse the Earthdata sign-in persisted on
this machine. Passwords are never tool parameters.

## 方式一：MCP 服务器

### 安装

```bash
python -m pip install "d3ltool[mcp]"
# 或从源码仓库
cd D3LTool && python -m pip install -e ".[mcp]"
```

SDK 要求 `mcp>=1.2,<3`（v1 的 `fastmcp` 与 v2 的 `mcpserver` API 均已适配；上限挡住
未来 3.x 的大版本破坏）。

入口二选一：`d3ltool-mcp`（pip 安装注册的命令）或 `python -m d3ltool.mcp_server`；
使用官方发行包时也可以直接指向 `D3LToolMCP(.exe)`。

JSON-RPC 走 stdio，服务器不监听任何端口。

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json`（macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`）:

```json
{
  "mcpServers": {
    "d3ltool": {
      "command": "d3ltool-mcp"
    }
  }
}
```

用发行包 exe 的话把 `command` 换成 exe 的绝对路径，例如：

```json
{
  "mcpServers": {
    "d3ltool": { "command": "D:/D3LTool/D3LToolMCP.exe" }
  }
}
```

### Cursor

`~/.cursor/mcp.json` 内容同上（`mcpServers` 结构一致）。

### ZCode / 其他支持 MCP 的客户端

同样往客户端的 `mcpServers` 配置中添加一个条目：

```json
{
  "mcpServers": {
    "d3ltool": { "command": "d3ltool-mcp" }
  }
}
```

### 验证 / Verify

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"0"}}}' | d3ltool-mcp
# 应返回一行包含 "serverInfo":{"name":"d3ltool"...} 的 JSON
```

配置完成后在客户端里直接说需求即可，例如：
“查一下 2020 年 1 月北京的夜光数据，把前三个文件下载到 D:/data”。
客户端会依次调用 `point_to_tile → search_granules → start_download → download_status`。

## 方式二：软件内 AI 助手

点主窗口右缘的 **AI** 按钮（或菜单 **设置 → AI 助手**）滑出助手抽屉：

1. **API 地址** —— 下拉预填了主流服务商模板，包括：
   - OpenAI：`https://api.openai.com/v1`
   - DeepSeek：`https://api.deepseek.com/v1`
   - 通义千问 Qwen：`https://dashscope.aliyuncs.com/compatible-mode/v1`
   - Moonshot Kimi：`https://api.moonshot.cn/v1`
   - 智谱 GLM：`https://open.bigmodel.cn/api/paas/v4`
   - SiliconFlow：`https://api.siliconflow.cn/v1`
   - Ollama（本地）：`http://127.0.0.1:11434/v1`，**不需要 API Key**；
     局域网内他人的 Ollama 服务把 host 换成对方地址即可，但要求对方
     Ollama 以 `OLLAMA_HOST=0.0.0.0` 启动（默认只监听 127.0.0.1，
     跨机器会连接超时），且防火墙放行 11434 端口
   - 自定义：任何 OpenAI 兼容接口
2. **模型名** + **API Key**（Ollama 留空），点 **测试连接** 验证。
3. 聊天框直接提需求。AI 会调用与 MCP 相同的工具集；调用 `start_download`
   前会弹窗请你确认，下载任务与手动下载共用同一个任务表（支持暂停/续传）。

### Key 安全 / Key storage

- API Key 明文保存在本机 `~/.d3ltool/config.json`（行业常规做法），只发送给你填写的服务商；
- Earthdata 密码不经过对话（下载凭据来自本机 netrc）；
- 对话记录只在当前会话内存中，**软件关闭即清空**，不落盘。

## 常见问题 / Troubleshooting

- **`d3ltool-mcp` 报 "MCP SDK is not installed"**：`python -m pip install "d3ltool[mcp]"`
- **AI 助手说下载未登录（not_authenticated）**：先在 GUI 登录一次（凭据随后自动持久化），或命令行 `d3ltool login`
- **客户端列表里搜不到 d3ltool 服务器**：检查 `command` 的路径，Windows 下 pip 脚本在
  `Python\Scripts\d3ltool-mcp.exe`；确认 `pip show mcp` 显示版本在 1.2~2.x 区间
- **流式输出中途断开**：多数服务商对长连接有限时，任务建议拆小；下载本身由
  D3LTool 引擎完成并支持断点续传，与对话无关
