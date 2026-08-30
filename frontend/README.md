# MiniCodex

MiniCodex 的桌面端 UI，基于 **Vue 3 + Vite + Electron + Pinia** 构建，对接后端 FastAPI 服务（`http://127.0.0.1:8000`）。

## 功能

- 💬 与 LLM 智能体流式对话（SSE，基于 `@microsoft/fetch-event-source`）
- ✅ 工具调用审批：agent 请求使用文件编辑等工具时，弹出批准/拒绝卡片
- 🗂 多会话管理：新建、切换、删除会话，会话名由后端生成；当前会话尚未发送消息时点击"新建对话"不会重复创建，而是聚焦输入框并轻提示"当前对话尚未开始"
- ⚙️ 设置弹窗：点击侧边栏底部齿轮图标，配置模型 / Base URL / API Key
- 📁 会话级工作目录：在对话框右上角徽章或输入框下方按钮中选择，每个会话独立绑定（Electron 内唤起系统原生目录选择器，浏览器内降级为路径输入）
- 🎨 界面以白色为主，按钮为浅蓝色

## 目录结构

```
src/
├── electron/               # Electron 主进程与预加载脚本
│   ├── main.js             # 创建窗口、加载 dev server 或打包产物
│   └── preload.js          # contextBridge 暴露 API base 地址
├── public/                 # 静态资源
├── src/
│   ├── api/index.js        # 后端 API 封装（REST + SSE 流式解析）
│   ├── components/         # 聊天窗口、输入框、会话列表、模型/目录配置
│   ├── stores/chat.js      # Pinia 状态管理
│   ├── App.vue             # 布局骨架
│   └── main.js             # Vue 入口
├── index.html
├── vite.config.js          # 开发代理 /api -> http://127.0.0.1:8000
└── package.json
```

## 快速开始

> 前置：已启动后端 `uvicorn main:app --port 8000`（项目根目录下），并已安装 Node.js ≥ 18。

```bash
# 安装依赖
npm install

# 浏览器开发模式（Vite dev server，通过 /api 代理访问后端）
npm run dev

# Electron 开发模式（先 build 再以 Electron 打开 dist 产物）
npm run electron:dev

# 可选: Electron + Vite 热更新模式
# 终端 1: npm run dev  (启动 Vite)
# 终端 2 (PowerShell): $env:VITE_DEV_SERVER_URL="http://localhost:5173"; npx electron .
# 终端 2 (CMD):        set VITE_DEV_SERVER_URL=http://localhost:5173 && npx electron .

# 打包桌面应用
npm run dist
```

## 接口对接说明

后端 API（`/MiniCode` 前缀）:

| 接口 | 方法 | 说明 |
|------|------|------|
| `/MiniCode/chat` | POST | 发送消息，SSE 流式返回 |
| `/MiniCode/approve` | POST | 批准/拒绝工具调用（`decision` 传 `"yes"` / `"no"`），SSE 返回 |
| `/MiniCode/new_chat` | POST | 新建会话 |
| `/MiniCode/sessions/{user_id}` | GET | 获取用户会话列表（含后端生成的会话名） |
| `/MiniCode/history/{session_id}` | POST | 获取会话历史 |
| `/MiniCode/deleteChat/{session_id}` | POST | 删除会话 |
| `/MiniCode/model` | POST | 切换模型 |
| `/MiniCode/old_model` | GET | 恢复默认模型配置 |
| `/MiniCode/workplace` | POST | 设置工作目录 |

### 跨域策略（未修改后端代码）

- **开发模式**：浏览器直接访问 Vite dev server（端口 5173），请求走 `/api` 前缀，由 `vite.config.js` 代理转发到 `127.0.0.1:8000`，无需后端 CORS 配置。
- **Electron 打包产物**：渲染进程直接请求 `http://127.0.0.1:8000`，若后端未配置 CORS 会被浏览器拦截。此时两种做法（按需选择）：
  1. 在后端 `main.py` 添加 `CORSMiddleware`（后续可做）；
  2. 或在 Electron 主进程内代理 API 请求（`net.request` / 自定义 protocol）。
- 打包后 API 地址可在 `electron/main.js` 的 `get-api-base-url` handler 中调整。

## 与后端事件结构的约定

SSE 每条事件为 `Result` JSON：`{ code, message, response, error }`。

- 流式中间事件：仅 `message`（工具状态提示等）
- 审批中断：仅 `message`，且为**最后一个事件**（流结束、无 `response`）
- 最终结果：`message` 为答案摘要，`response` 为 `agentResult`

前端据此判断：流结束后最后一个事件不含 `response` 即视为审批请求，弹出批准/拒绝卡片，批准值为 `"yes"`、拒绝值为 `"no"`（与后端 `decision != "yes"` 的判断一致）。
