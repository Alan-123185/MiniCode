from typing import Optional, TypeVar, Generic
from pydantic import BaseModel
T = TypeVar('T')


class Result(BaseModel,Generic[T]):
    code: int=200
    message: Optional[str] = None
    response: Optional[T]=None      # 将上面的结果直接塞进 data
    error: Optional[str] = None
    # 工具状态事件的结构化载荷 (来自 core/toolStatusEvent.outputEvent: {status, message})。
    # message 字段对工具事件只放人话文案, status 供前端精确归类进"工具调用折叠面板",
    # 不再依赖猜中文短句 (历史会话走结构化 tool_calls, 流式会话走这里, 两条路统一)。
    toolEvent: Optional[dict] = None


    @classmethod
    def success(self):
        return Result(message="success")




