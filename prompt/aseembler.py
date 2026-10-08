from prompt.staticPrompt.Actions import Actions_pro
from prompt.staticPrompt.Intro import Intro_pro
from prompt.staticPrompt.Output import Output_pro
from prompt.staticPrompt.System import System_pro
from prompt.staticPrompt.Task import Task_pro
from prompt.staticPrompt.Tone import Tone_pro
from prompt.staticPrompt.Usetool import UseTool_pro
from states.OverallState import OverAllState
from utils.dictToText import dict_to_text



"""
文首静态提示词组装
"""
def build_static_system_prompt() -> str:
    parts = [
        Intro_pro,
        System_pro,
        Task_pro,
        Actions_pro,
        UseTool_pro,
        Tone_pro,
        Output_pro,
    ]
    return "\n\n".join(parts)

"""
创建并返回一个摘要历史作为动态提示词 包含当前的摘要状态信息。
"""
def build_history_summary_prompt(state:OverAllState) -> str:
    return dict_to_text(state.summary_state.model_dump())