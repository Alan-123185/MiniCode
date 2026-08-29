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
start_line INTEGER NOT NULL,
end_line INTEGER NOT NULL,
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
CREATE INDEX IF NOT EXISTS idx_file_ops_group ON file_operations(group_id);
CREATE INDEX IF NOT EXISTS idx_file_ops_created ON file_operations(created_at DESC);
