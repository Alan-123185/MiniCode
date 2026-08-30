from langchain_core.messages import SystemMessage
from config.modelConfig import model_config
from core.Task import TaskList
from prompt.plan_prompt import PLAN_PROMPT
from states.OverallState import OverAllState
from utils.filePathTools import relativePathToAbsolute

TOOLS_DESCRIPTION = relativePathToAbsolute("./toolJSONSchema.json").read_text(encoding="utf-8")


def plan_node(state: OverAllState) -> OverAllState:
    # 计划节点，主要是根据当前的状态来决定下一步的操作
    # 这里可以根据具体的业务逻辑来实现不同的计划策略
    # 例如，如果当前状态中有未处理的工具调用，则继续处理工具调用
    # 如果没有未处理的工具调用，则进入输出节点
    plan_prompt = PLAN_PROMPT.format(TOOLS_DESCRIPTION=TOOLS_DESCRIPTION)
    model = model_config["value"].with_structured_output(TaskList)
    task_list = model.invoke([SystemMessage(content=plan_prompt)])
    return {
        "tasks": task_list
    }