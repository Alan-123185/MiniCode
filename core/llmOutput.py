import uuid
from pydantic import Field, PrivateAttr
from pydantic import BaseModel


class Memory(BaseModel):
    summary: str=Field(default_factory=str, description="当前任务状态的总结和关键结论，简明扼要，便于llm快速理解上下文")
    next_steps: list[str] = Field(default_factory=list,description="下一步的计划或行动")
    files : list[str] = Field(default_factory=list,description="当前涉及的文件路径列表")
    errors: list[str] = Field(default_factory=list,description="当前存在的问题或待处理的事项")
    _memory_id: str = PrivateAttr(default_factory=lambda: str(uuid.uuid4()),description="当前记忆的唯一标识符，便于追踪和管理")

    @property
    def memory_id(self) -> str:
        return self._memory_id

class llmOutput(BaseModel):
    content: str = Field(default_factory=str, description="LLM输出的内容，可能是文本、代码或其他格式")
    memory:Memory=Field(default_factory=Memory, description="当前对话的记忆状态，包含总结、下一步计划和错误信息，简单描述即可")


