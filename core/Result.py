from typing import Optional, TypeVar, Generic
from pydantic import BaseModel
T = TypeVar('T')


class Result(BaseModel,Generic[T]):
    code: int=200
    message: Optional[str] = None
    response: Optional[T]=None      # 将上面的结果直接塞进 data
    error: Optional[str] = None


    @classmethod
    def success(self):
        return Result(message="success")




