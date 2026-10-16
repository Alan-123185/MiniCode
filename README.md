# MiniCode

> 一个面向本地代码仓库的桌面端 AI 编程智能体（Agent）。
> 让 AI 在你的本地仓库里**安全地读、写、跑**。

MiniCode 是一个可本地部署的编程智能体：它基于 **LangGraph** 编排「思考 → 调用工具 → 观察结果 → 继续」的循环，内置文件读写、代码检索、命令执行、版本回滚等一整套工具，并通过**工具审批**、**命令白名单**与**可选 Docker 沙箱**保证操作安全。前端是一个 **Vue 3 + Electron** 桌面应用，提供流式对话、工具调用可视化、多会话并行等完整体验。

---

## ✨ 特性

- 🧠 **LangGraph 智能体编排** — 显式状态机 + SQLite 检查点，支持中断、恢复与时间旅行
- 🛠️ **15+ 内置工具** — 文件读取/检索/编辑、命令执行、脚本运行、操作组回滚、只读探索子代理
- 📉 **上下文治理** — 滑动窗口 + 结构化摘要 + 降级压缩，长会话不爆 token
- 🔒 **安全边界** — 危险工具需审批、命令只读白名单、可选 Docker 沙箱隔离
- 🖥️ **桌面端体验** — SSE 流式对话、打字机渲染、工具调用折叠面板、多会话并行生成
- 📁 **会话级工作目录** — 每个会话独立绑定一个仓库目录
- ↩️ **可回滚编辑** — 每次文件改动记录为操作组，支持回滚到任意历史版本
- 🔌 **MCP 扩展** — 通过 MCP 协议接入外部工具（如联网搜索）

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│  Electron 桌面端 (Vue 3 + Vite + Pinia)                  │
│  ChatWindow / MessageInput / SessionList / SettingsModal │
└───────────────────────────┬─────────────────────────────┘
                            │  REST + SSE (http://127.0.0.1:8000)
┌───────────────────────────▼─────────────────────────────┐
│  FastAPI 后端 (main.py)                                  │
│  routers/  →  service/  →  graphs/chat_graph.py          │
│                                                          │
│   LangGraph StateGraph:                                  │
│   START → input → (summerize) → degrade → llm            │
│                    ↑                        │            │
│                    └──── tool ◄─────────────┘            │
│                             │                            │
│                          output → END                    │
│                                                          │
│   tools/  (文件/命令/回滚/子代理/MCP)                     │
│   context/ (摘要 + 降级管线)                              │
│   mapper/  (SQLite 持久化)                                │
└─────────────────────────────────────────────────────────┘
```

### 目录结构

```
MiniCode/
├── main.py                 # FastAPI 入口（lifespan 初始化图与工具）
├── graphs/chat_graph.py    # LangGraph 状态机定义与编译
├── nodes/                  # 图节点：input / llm / tool / output / degrade / summerize
├── states/                 # 图状态定义（OverallState / InputState / OutputState ...）
├── tools/                  # 工具实现（file_read / file_edit / command / sub_agent ...）
├── prompt/                 # 提示词（staticPrompt 静态段 + dynamicPrompt 动态段 + 组装器）
├── context/                # 上下文治理（degradeManage 降级 / summaryManage 摘要）
├── service/                # 业务逻辑层
├── routers/                # HTTP / SSE 路由
├── mapper/                 # SQLite 数据访问
├── requestcommon/          # 请求体模型
├── core/                   # 结果与事件模型（Result / toolResult / InterruptInfo ...）
├── utils/                  # 通用工具（命令安全 / 编码 / 路径 / 压缩 ...）
├── MCP/agent_search_mcp/   # MCP 搜索工具（Node.js）
├── frontend/               # Vue 3 + Electron 桌面端
├── bin/                    # 内置 node.exe / rg.exe
├── init_script.sql         # 数据库初始化脚本
└── requirements.txt
```

---

## 🚀 快速开始

### 环境要求

| 依赖 | 版本 |
|------|------|
| Python | ≥ 3.11 |
| Node.js | ≥ 18（前端 & MCP） |
| Git for Windows | 必需（`execute_command` 依赖 Git Bash） |

### 1. 后端

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，至少填写 DEFAULT_BASE_URL / DEFAULT_API_KEY / DEFAULT_MODEL

# 启动服务（默认 http://127.0.0.1:8000）
python main.py
# 或
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. 前端（桌面端）

```bash
cd frontend
npm install

# 浏览器开发模式（Vite dev server，通过 /api 代理后端）
npm run dev

# Electron 开发模式
npm run electron:dev

# 打包桌面应用（生成 NSIS 安装包）
npm run dist
```

> 打包前需先在项目根目录用 PyInstaller 生成 `main.exe`（见 `main.spec`），
> electron-builder 会通过 `extraResources` 将其与 `.env`、`init_script.sql`、`bin/`、`MCP/` 一并打入安装包。

### 3. 配置说明（`.env`）

```ini
# ---- 模型 ----
DEFAULT_BASE_URL = "https://your-llm-endpoint/v1"
DEFAULT_API_KEY  = "sk-xxxx"
DEFAULT_MODEL    = "your-model-name"

# ---- 联网搜索（可选）----
baidu_search_url     = ""
baidu_search_api_key = ""


## 🛠️ 内置工具

| 工具 | 说明 | 需审批 |
|------|------|:------:|
| `readfile` | 读取文件内容（多编码兜底） | — |
| `listfiles` | 列出目录树 | — |
| `code_outline` | 基于 AST 输出代码结构大纲 | — |
| `search_code_by_keyword` | 正文关键词/正则搜索 | — |
| `search_file_by_keyword` | 文件名搜索 | — |
| `file_edit` | 内容锚定替换（≥5 行上下文保证唯一命中） | ✅ |
| `create_file` | 创建新文件 | ✅ |
| `delete_file` | 删除文件 | ✅ |
| `execute_command` | 在 Git Bash 中执行命令 | ✅ |
| `run_code` | 写入临时脚本并执行（多语言） | ✅ |
| `undo_operationgroup` | 回滚到指定操作组版本 | ✅ |
| `query_operationgroup` | 查询会话的操作组列表 | — |
| `get_original_content_by_tool_call_id` | 取回被截断的原始工具输出 | — |
| `get_original_content_by_memory_id` | 取回被降级的原始消息 | — |
| `search_sub_agent` | 只读代码探索子代理 | — |
| `free_search` | 联网搜索（MCP） | — |

---

## 🔌 API 一览

所有接口以 `/MiniCode` 为前缀，统一返回 `Result`：`{ code, message, response, error }`。

| 接口 | 方法 | 说明 |
|------|------|------|
| `/MiniCode/chat` | POST | 发送消息，**SSE** 流式返回 |
| `/MiniCode/approve` | POST | 批准/拒绝工具调用（`decision`: `"yes"`/`"no"`），SSE |
| `/MiniCode/continue` | POST | 从最近检查点恢复中断的会话，SSE |
| `/MiniCode/editMessage` | POST | 编辑历史消息并从该检查点重新生成，SSE |
| `/MiniCode/stop` | POST | 停止指定会话的生成 |
| `/MiniCode/new_chat` | POST | 新建会话 |
| `/MiniCode/sessions` | GET | 获取用户会话列表 |
| `/MiniCode/history` | GET | 获取会话历史消息 |
| `/MiniCode/deleteChat` | POST | 删除会话 |
| `/MiniCode/workplace` | POST | 设置会话工作目录（仅可绑定一次） |
| `/MiniCode/add_model` | POST | 新增模型配置 |
| `/MiniCode/set_model` | POST | 切换当前生效模型 |
| `/MiniCode/update_model` | POST | 更新模型配置 |
| `/MiniCode/get_model` | GET | 获取模型列表 |
| `/MiniCode/settings` | POST | 保存生成参数（温度/主题/思考等级） |
| `/MiniCode/get_settings/{user_id}` | GET | 读取生成参数 |
| `/MiniCode/checkGit` | GET | 检测 Git 环境（未安装时尝试 winget 安装） |

### SSE 事件约定

每条事件为 `Result` JSON：

- **流式中间事件**：仅 `message`（工具状态提示），或 `toolEvent: { status, message }`（结构化工具事件）
- **审批中断**：仅 `message`，且为**最后一个事件**（流结束、无 `response`）
- **最终结果**：`message` 为答案摘要，`response` 为 `agentResult`

前端据此判断：流结束后最后一个事件不含 `response` 即视为审批请求。

---

## 🔒 安全机制

1. **工具审批（HITL）** — `file_edit` / `execute_command` / `delete_file` / `create_file` / `undo_operationgroup` / `run_code` 执行前中断，等待用户批准。
2. **命令白名单** — `execute_command` 按 `&& || | ; &` 拆链，**每一段**都必须命中只读白名单（`git status`、`dir`、`pip list` 等）。`git status && del xxx` 会因第二段不匹配而照常弹确认。
3. **路径约束** — 所有文件操作限定在会话工作目录内（`is_path_safe`）。
4. **Docker 沙箱（可选）** — 开启后命令在容器内执行，支持内存/CPU 限制、网络策略、空闲回收、非 root 用户。
5. **操作组回滚** — 每次文件改动可逆，误操作可回退。

---

## 🧩 上下文治理

长会话通过三层机制控制 token：

1. **滑动窗口** — 按 token 数（默认 75k 触发）与消息条数（默认 25 条）双重阈值管理。
2. **结构化摘要** — 超窗内容由 LLM 总结为 `summaryState`（已修改文件 / 遗留问题 / 已完成里程碑），作为动态提示词注入。
3. **降级压缩** — `degrade_node` 对超限消息做压缩，保留最近 3 条工具结果不处理。

此外，超长工具输出会被智能截断：优先提取 **pytest FAILURES/ERRORS 块** 与通用错误上下文，头尾保留 + 中间省略，并提示用 `get_original_content_by_tool_call_id` 查看原文。

---

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl/Cmd + N` | 新建对话 |
| `Ctrl/Cmd + K` | 聚焦会话搜索 |
| `Ctrl/Cmd + ,` | 打开设置 |
| `Ctrl/Cmd + Shift + L` | 切换主题 |

---

## 🧰 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI · Uvicorn |
| 智能体 | LangGraph · LangChain · langchain-openai |
| 持久化 | SQLite（aiosqlite）· LangGraph SqliteSaver |
| 代码解析 | tree-sitter |
| 前端 | Vue 3 · Vite · Pinia · marked |
| 桌面端 | Electron · electron-builder（NSIS） |
| 打包 | PyInstaller（后端）· electron-builder（前端） |

---

## 📄 版本

当前版本：**v1.1.0**（2026-10-16）

详见 [RELEASE_NOTES.md](./RELEASE_NOTES.md)。

---

## 📜 License

本项目仅供学习与个人使用。
