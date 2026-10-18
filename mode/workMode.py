from typing import ClassVar
from prompt.aseembler import build_static_system_prompt
from tools.toolManage import toolManage


class workMode:
    model_name:ClassVar[str]="work"
    #工作模式享有全部工具

    @staticmethod
    def get_tools():
        return toolManage.tools

    @staticmethod
    def get_prompt_template():
        return workMode._build_static_work_system_prompt()



    @staticmethod
    def _build_static_work_system_prompt() -> str:
        return build_static_system_prompt()

