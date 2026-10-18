from typing import Protocol, Literal, runtime_checkable

"""
模式接口
"""
@runtime_checkable
class basicMode(Protocol):
    model_name:Literal["work","plan","free_fly"]

    @staticmethod
    def get_tools() -> list[str]:
        ...
    @staticmethod
    def get_prompt_template() -> str:
        ...
