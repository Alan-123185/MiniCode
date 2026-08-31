from typing import List

from pydantic import BaseModel, Field


class summaryState(BaseModel):
    modified_files: List[str] = Field(
        default_factory=list,
        description="所有被修改过的文件路径"
    )

    key_interfaces: List[str] = Field(
        default_factory=list,
        description="关键接口签名、函数名、类名"
    )

    environment_notes: List[str] = Field(
        default_factory=list,
        description="环境变量、配置项、依赖版本"
    )

    pending_issues: List[str] = Field(
        default_factory=list,
        description="尚未解决的遗留问题"
    )

    completed_milestones: List[str] = Field(
        default_factory=list,
        description="已完成的里程碑"
    )

