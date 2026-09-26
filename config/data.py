from pathlib import Path
from typing import ClassVar
import os
import string
from langgraph.checkpoint.memory import MemorySaver, InMemorySaver
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env") # ← 关键：读 .env
    DEFAULT_BASE_URL: str = ""  # 默认 base_url

    DEFAULT_API_KEY: str = ""  # 默认 api_key

    DEFAULT_MODEL: str = ""  # 默认模型名
    # 默认流式模型
    DEFAULT_STREAMING_MODEL: bool = True
    # 内存记忆对象
    default_memory: ClassVar[InMemorySaver] = MemorySaver()

    DEFAULT_TEMPERATURE: float = 0.3  # 默认温度参数

    DEFAULT_THEME: bool = True  # 默认主题 白

    DEFAULT_THINK_LEVEL: int = 2  # 默认思考等级

    web_search_timeout: int = 30  # 默认网页请求超时时间

    web_search_words_limit: int = 5000  # 默认搜索最大结果字数

    # 百度搜索默认返回条数
    baidu_search_default_return_number: int = 2
    # 默认百度搜索接口
    baidu_search_url: str = ""
    # 默认百度搜索api_key
    baidu_search_api_key: str = ""
    #rg.exe的路径
    rg_path : ClassVar[Path] = (
            Path(__file__)
            .resolve()
            .parent
            .parent
            / "bin"
            / "rg.exe"
    )

    file_change_tool_list:list=["file_edit","create_file","delete_file"]

    sql_script_path: ClassVar[Path] = (
            Path(__file__)
            .resolve()
            .parent
            .parent
            / "init_script.sql"
    )
    MXC_path: ClassVar[Path] = (
            Path(__file__)
            .resolve()
            .parent
            .parent
            / "bin"
            / "MXC"
            / "wxc-exec.exe"
    )

    db_path: ClassVar[Path] = (
            Path(__file__).resolve().parent.parent / "minicodexdatabase.db"
    )

    node_path:ClassVar[Path] = (
            Path(__file__)
            .resolve()
            .parent
            .parent
            / "bin"
            / "node"
            / "node.exe"
    )

    index_path:ClassVar[Path] = (
            Path(__file__)
            .resolve()
            .parent
            .parent
            / "MCP"
            / "agent_search_mcp"
            / "dist"
            / "index.js"
    )

    # On Windows, automatically detect all existing drive letters (C:\\, D:\\, ...)
    # so the config will include all system drives. On non-Windows platforms
    # default to an empty list.
    MXC_READ_ONLY_LIST: list[str] = (
        [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        if os.name == "nt"
        else []
    )
    MXC_containment: str = "processcontainer"  # 沙箱隔离方式，默认使用进程容器
    MXC_network_egress: str = "allow"  # 沙箱网络访问策略，默认禁止外发
    MXC_version: str="0.8.0-alpha"
    MXC_network_ingress: str = "deny"  # 沙箱网络访问策略，默认禁止入站
    MXC_network_hostLoopback: str = "deny"  # 沙箱网络访问策略，默认禁止回环访问
    #最大超步限制
    DEFAULT_RECURSION_LIMIT : int = 10
    # 编码方式集合
    ENCODINGS_TO_TRY: list[str] = ["utf-8", "gbk", "gb2312", "latin-1", "cp1252"]
    #单个工具最大重试次数
    MAX_TOOL_CALLS : int=3

    #统一管理魔法数字  关于file_edit工具的返回码
    check_patch_notfound :int=-1        #指定路径不存在
    check_patch_bad :int=1              #出现多个匹配项
    check_patch_ok :int=0               #可以使用
    check_patch_morethan_one: int= 2     #补丁修改了多个文件
    check_patch_error_path:int=3         #补丁修改的文件路径和目标路径不一致
    check_patch_line_error:int=4         #补丁中行号不合法
    check_patch_match_error:int=5        #补丁中的内容与原始内容不匹配
    check_patch_none: int =-2            #补丁中没有修改内容

    tool_failed:int=-1                    #工具执行失败
    tool_success:int=0                    #工具调用成功
    tool_try : int=1                      #尝试调用工具
    tool_refused:int=2                    #用户拒绝调用工具

    interrupt_type_approve: int =-1             #中断类型：需要用户确认
    interrupt_type_info:int =1                 #中断类型：仅提示信息
    interrupt_type_result: int = 0             #中断类型，返回结果
    #命令行执行相关参数
    COMMAND_TIMEOUT: int = 30       #命令执行最大时长

    # ---------- Docker 沙箱（新增） ----------
    SANDBOX_ENABLED: bool = False                    # 总开关：True 时 execute_command 在 Docker 容器内执行；False 或 Docker 不可用时回退宿主机直接执行（原行为）
    SANDBOX_IMAGE: str = "minicode-sandbox:latest"  # 沙箱镜像名（由 Dockerfile.sandbox 构建）
    SANDBOX_WORKDIR: str = "/workspace"              # 容器内工作区挂载点（宿主机 workplace 目录 bind mount 到这里）
    SANDBOX_MEM_LIMIT: str = "2g"                    # 容器内存上限（docker 格式，如 512m / 1g）
    SANDBOX_CPU_COUNT: float = 2.0                   # 容器可用 CPU 核数
    SANDBOX_NETWORK_ENABLED: bool = True             # 容器是否允许联网（pip/npm install 需要；严格安全场景可设 False）
    SANDBOX_IDLE_TTL_MINUTES: int = 120              # 容器空闲自动回收阈值（分钟），0 表示不自动回收
    SANDBOX_USER: str = "agent"                     # 容器内执行命令的用户名（避免 root 执行权限过大）
    LLM_MAX_UNDEGREDED_MESSAGE_TOKEN :int = 20000   #滑动窗口存储的最大未处理消息token数
    LLM_MAX_UP_MESSAGE_COUNT :int = 25             #滑动窗口存储的最大上下文消息数
    LLM_MAX_UP_MESSAGE_TOKEN : int =60000          #滑动窗口存储的最大上下文消耗token数
    LLM_MAX_TOKEN : int = 90000                    #摘要机制触发的最小token数

    MAX_OLD_MESSAGE_LENGTH: int = 300                #需要压缩的旧消息长度阈值，超过该长度的旧消息会被压缩短

    """
    大模型消息类型
    """
    LLM_MESSAGE_TYPE_SYSTEM: str = "system"
    LLM_MESSAGE_TYPE_HUMAN: str = "human"
    LLM_MESSAGE_TYPE_TOOL: str = "tool"
    LLM_MESSAGE_TYPE_AI: str = "ai"

    READ_FILE_MAX_COUNT:int=15000  #读取文件的最大字符数
    RETURN_FILE_MAX_COUNT:int=1500  #返回文件的边界最大字符数

    THREAD_HOLD :float=0.85   #文本匹配相似度
    MIN_HOLD: float =0.5      #最小近似相似度


    THINK_LEVEL_LOW: int= 1
    THINK_LEVEL_HIGH: int= 3
    THINK_LEVEL_MEDIUM: int= 2

    MAX_MODEL_COUNT: int = 5

    COMMAND_MAX_CHAR_COUNT: int = 6000  #命令行返回结果最大字符数
    COMMAND_HEAD:int = 3000             #命令行返回结果头部最大字符数
    COMMAND_TAIL:int = 2500             #命令行返回结果尾部最大字符数


    RG_SEARCH_MAX_COUNT:int=50          #rg搜索最大返回条数
    RG_SEARCH_TIMEOUT:int=30            #rg搜索超时秒数

    SAFE_COMMAND_WHITELIST: list[str] = [
        r"^git (status|log|show|diff|blame|shortlog|describe)( |$)",
        r"^git branch( (--list|-a|-v|-vv|--show-current))?$",  # 只放行列举，建/删分支不匹配
        r"^git (ls-files|rev-parse|remote -v|stash list|worktree list)( |$)",
        r"^(dir|type|where|ver|tree|cd|chdir|echo|findstr)( |$)",
        r"^(python|pip|node|npm|git|rg) (--version|-V)( |$)",
        r"^pip (list|show|freeze)( |$)",
    ]









    """
    数据库 pgsql
    """
    # DB_HOST: str = "localhost"
    # DB_PORT: int = 5432
    # DB_USER: str = "postgres"
    # DB_PASSWORD: str = "123456"
    # DB_NAME: str = "your_db"
    #
    # @property
    # def database_url(self) -> str:
    #     """同步连接串（给 SQLAlchemy ORM 用）"""
    #     return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    #
    # @property
    # def async_database_url(self) -> str:
    #     """异步连接串（给 FastAPI 异步用）"""
    #     return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    #
    # @property
    # def langgraph_pg_url(self) -> str:
    #     """LangGraph checkpointer 用的连接串"""
    #     return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()