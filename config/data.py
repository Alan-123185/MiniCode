from pathlib import Path
from typing import ClassVar
from langgraph.checkpoint.memory import MemorySaver, InMemorySaver
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env") # ← 关键：读 .env
    DEFAULT_BASE_URL: str = ""  # 默认 base_url

    DEFAULT_API_KEY: str = ""  # 默认 api_key

    DEFAULT_MODEL: str = ""  # 默认模型名
    # 默认流式模型
    DEFAULT_STREAMING_MODEL: bool = False
    # 内存记忆对象
    default_memory: ClassVar[InMemorySaver] = MemorySaver()
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


    LLM_MAX_UP_MESSAGE_COUNT :int = 25             #滑动窗口存储的最大上下文消息数
    LLM_MAX_UP_MESSAGE_TOKEN : int =20000          #滑动窗口存储的最大上下文消耗token数
    LLM_MAX_TOKEN : int = 90000                    #摘要机制触发的最小token数

    MAX_OLD_MESSAGE_LENGTH: int = 300                #需要压缩的旧消息长度阈值，超过该长度的旧消息会被压缩短
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