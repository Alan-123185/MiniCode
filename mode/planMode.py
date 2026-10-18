from typing import ClassVar

from prompt.dynamicPrompt.modelPrompt.Plan import Plan_pro
from prompt.staticPrompt.Forbid import Forbid_pro
from prompt.staticPrompt.Intro import Intro_pro
from prompt.staticPrompt.Output import Output_pro
from prompt.staticPrompt.System import System_pro
from prompt.staticPrompt.Task import Task_pro
from prompt.staticPrompt.Tone import Tone_pro
from prompt.staticPrompt.Usetool import UseTool_pro
from tools.toolManage import toolManage


class planMode:
    model_name:ClassVar[str] = "plan"

    plan_tools :ClassVar[list[str]]= [
        "readfile",
        "listfiles",
        "search_code_by_keyword",
        "search_file_by_keyword",
        "get_original_content_by_tool_call_id",
        "get_original_content_by_memory_id",
        "code_outline",
        "execute_command",
        "free_search"
    ]
    @staticmethod
    def get_tools():
        return [tool for tool in toolManage.tools if tool.name in planMode.plan_tools]

    @staticmethod
    def get_prompt_template():
        return planMode._build_static_plan_system_prompt()

    @staticmethod
    def _build_static_plan_system_prompt() -> str:
        parts = [
            Intro_pro,
            System_pro,
            Task_pro,
            UseTool_pro,
            Forbid_pro,
            Tone_pro,
            Output_pro,
            Plan_pro
        ]
        return "\n\n".join(parts)

