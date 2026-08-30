from pydantic import BaseModel, Field
from typing import Optional, List, Union
from enum import Enum

from config.data import settings
from core.toolParams import ReadFileParams, BaiduSearchParams, RunCommandParams, SearchCodeByKeywordParams, \
    SearchFileByKeywordParams, FileEditParams, CreateFileParams, UndoOperationGroupParams, DeleteFileParams, \
    QueryOperationGroupParams, ListFilesParams

ParmsType=Union[
    ReadFileParams,
    BaiduSearchParams,
    RunCommandParams,
    ListFilesParams,
    SearchCodeByKeywordParams,
    SearchFileByKeywordParams,
    FileEditParams,
    CreateFileParams,
    DeleteFileParams,
    UndoOperationGroupParams,
    QueryOperationGroupParams
]


class TaskStatus(str, Enum):
    PENDING = "pending"     # 等待前置任务完成
    READY = "ready"         # 前置条件满足，可被执行
    RUNNING = "running"     # 执行中
    SUCCESS = "success"     # 执行成功
    FAILED = "failed"       # 执行失败

class TaskType(str, Enum):
    READ="read"          # 读取文件或数据
    WRITE="write"        # 写入文件或数据
    EXECUTE="execute"    # 执行命令或脚本

class Task(BaseModel):
    id: str = Field(..., description="任务唯一标识")
    prompt: str = Field(..., description="任务的自然语言描述，用于指导执行")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="当前任务状态")
    payload: TaskType = Field(..., discriminator="tool_name")
    deps: List[str] = Field(default_factory=list, description="依赖的前置任务 ID 列表，用于构建 DAG")
    type: TaskType = Field(..., description="任务类型，决定由哪个执行器处理")
    result: Optional[str] = Field(default=None, description="执行成功后的结果（如生成的代码、测试日志等）")
    error: Optional[str] = Field(default=None, description="执行失败时的错误信息")
    retry_count: int = Field(default=0, description="已重试次数")
    max_retries: int = Field(default=settings.MAX_TOOL_CALLS, description="最大重试次数")
    # 可选：created_at, updated_at 等时间戳用于追踪


class TaskList(BaseModel):
    tasks: List[Task] = Field(default_factory=list, description="任务列表")
