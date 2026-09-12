CREATE TABLE IF NOT EXISTS session (
id TEXT  NOT NULL PRIMARY KEY,       -- 自增主键
name TEXT ,                          -- 会话名称
workplace TEXT ,                      -- 工作目录
user_id TEXT NOT NULL  ,             -- 用户 ID
created_at INTEGER               -- 创建时间，默认当前时间
);
CREATE TABLE IF NOT EXISTS operation_groups (
id TEXT PRIMARY KEY,                -- 业务主键：uuid4() 生成（例如 "abc-123"）
session_id TEXT NOT NULL,           -- LangGraph 的 thread_id（整个会话）
user_prompt TEXT,                   -- 用户当时说的话（用于展示回滚菜单列表）
created_at INTEGER,             -- 时间戳
is_undone BOOLEAN DEFAULT 0         -- 软删除标志
);
CREATE TABLE IF NOT EXISTS file_operations (
id INTEGER NOT NULL PRIMARY KEY,        -- 自增主键，用于倒序回滚
group_id TEXT NOT NULL,
file_path TEXT NOT NULL,
operation_type TEXT NOT NULL,  -- 'insert' | 'delete' | 'replace'
old_snippet TEXT,
new_snippet TEXT,
created_at INTEGER ,         -- 同样存 Unix 时间戳
FOREIGN KEY (group_id) REFERENCES operation_groups(id)
);
CREATE TABLE IF NOT EXISTS model (
id INTEGER PRIMARY KEY AUTOINCREMENT,
model_name TEXT NOT NULL,
base_url TEXT NOT NULL,
api_key TEXT NOT NULL,
is_default int NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
user_id TEXT NOT NULL PRIMARY KEY,
settings TEXT NOT NULL
);



CREATE TABLE IF NOT EXISTS summary (

    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,             -- 关联会话

    -- 消息基础信息
    message_type TEXT NOT NULL,           -- 'system', 'human', 'ai', 'tool'
    content TEXT,                         -- 原始完整内容（用于翻旧账）
    compressed_content TEXT,              -- 压缩后内容（用于构建 Prompt）

    -- 工具调用相关
    tool_call_id TEXT,                    -- 工具调用 ID（ToolMessage 必填，AIMessage 可为空）
    -- 扩展字段
    additional_kwargs TEXT,               -- 存储 tool_calls、usage_metadata 等 JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    memory_id TEXT,                      -- 关联的记忆 ID（可为空，表示该消息未被记忆）

    FOREIGN KEY (session_id) REFERENCES session(id)
);

-- 建索引，加速查询
CREATE INDEX IF NOT EXISTS idx_messages_session ON summary(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_tool_call ON summary(tool_call_id);
CREATE INDEX IF NOT EXISTS idx_file_ops_group ON file_operations(group_id);
CREATE INDEX IF NOT EXISTS idx_file_ops_created ON file_operations(created_at DESC);
