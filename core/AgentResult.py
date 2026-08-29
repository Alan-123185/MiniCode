from typing import Optional, List

from pydantic import BaseModel


class AgentResult(BaseModel):
    answer: str                          # 最终答案
    steps: List[str]                     # 关键步骤快照，如 ["调用搜索工具", "检索知识库", "生成回复"]
    total_tokens: Optional[int]          # 总消耗 Token
    status: str                          # "success" | "error" | "partial"


