from pathlib import Path
from typing import Literal, Optional
from pydantic import BaseModel
from config.data import settings
from core.toolResult import toolResult


class toolstatusEvent(BaseModel):
    status: Literal[settings.tool_failed,settings.tool_success,settings.tool_try,settings.tool_refused]
    tool_name: str
    args: Optional[dict]=None
    result: Optional[toolResult]=None
    user_prompt: Optional[str]=None
    session_id: Optional[str]=None



def manage_toolstatusEvent(event: toolstatusEvent):
    """
    处理工具状态事件。方便展示给前端
    """
    if event.status == settings.tool_success:
        return success_return_str(event)
    elif event.status == settings.tool_failed:
        return failed_return_str(event)
    elif event.status == settings.tool_refused:
        return refused_return_str(event)
    elif event.status == settings.tool_try:
        return try_return_str(event)
    else:
        return f"工具 {event.tool_name} 状态未知: {event.status}"

#如果工具调用成功，返回一句简单的提示语，方便前端展示
def success_return_str(events: toolstatusEvent) -> str:
    if events.tool_name == "read_file":
        # 处理 read_file 工具的逻辑
        file_path = events.args.get("file_path")
        start_line = events.args.get("start_line", None)
        end_line = events.args.get("end_line", None)
        range_str= f" (lines {start_line}-{end_line})" if start_line is not None and end_line is not None else ""
        return f"读取文件 {Path(file_path).name} {range_str}"
    if events.tool_name == "edit_file":
        # 处理 edit_file 工具的逻辑
        tool_result=events.result
        return tool_result.message
    if events.tool_name == "delete_file":
        # 处理 delete_file 工具的逻辑
        file_path= events.args.get("file_path")
        return f"删除文件 {Path(file_path).name}"
    if events.tool_name == "create_file":
        # 处理 create_file 工具的逻辑
        file_path= events.args.get("file_path")
        return f"创建文件 {Path(file_path).name}"
    if events.tool_name == "execute_command":
        # 处理 execute_command 工具的逻辑
        command= events.args.get("command")
        command=command.strip()[0:50] + "..." if len(command)>50 else command.strip()
        return f"运行 {command} 成功"
    if events.tool_name == "run_code":
        # 处理 run_code 工具的逻辑
        filename= events.args.get("filename")
        return f"执行 {Path(filename).name} "
    if events.tool_name == "undo_operationgroup":
        # 处理 undo_operationgroup 工具的逻辑
        return "回滚..."
    else:
        return f"run {events.tool_name} "


def failed_return_str(events: toolstatusEvent) -> str:
    if events.tool_name == "read_file":
        # 处理 read_file 工具的逻辑
        file_path = events.args.get("file_path")
        return f"读取文件 {Path(file_path).name} 失败:\n {events.result.error}"
    if events.tool_name == "edit_file":
        # 处理 edit_file 工具的逻辑
        return f"编辑文件失败: {events.result.error}"
    if events.tool_name == "delete_file":
        # 处理 delete_file 工具的逻辑
        file_path= events.args.get("file_path")
        return f"删除文件 {Path(file_path).name} 失败:\n {events.result.error}"
    if events.tool_name == "create_file":
        # 处理 create_file 工具的逻辑
        file_path= events.args.get("file_path")
        return f"创建文件 {Path(file_path).name} 失败:\n {events.result.error}"
    if events.tool_name == "execute_command":
        # 处理 execute_command 工具的逻辑
        command= events.args.get("command")
        command=command.strip()[0:50] + "..." if len(command)>50 else command.strip()
        return f"运行 {command} 失败:\n {events.result.error}"
    if events.tool_name == "run_code":
        # 处理 run_code 工具的逻辑
        filename= events.args.get("filename")
        return f"执行 {Path(filename).name} 失败:\n {events.result.error}"
    if events.tool_name == "undo_operationgroup":
        # 处理 undo_operationgroup 工具的逻辑
        return f"回滚失败:\n {events.result.error}"
    else:
        return f"run {events.tool_name} failed:\n {events.result.error}"



def refused_return_str(events: toolstatusEvent) -> str:
    if events.tool_name == "edit_file":
        # 处理 edit_file 工具的逻辑
        file_path = events.args.get("file_path")
        return f"拒绝编辑文件 {Path(file_path).name}"
    if events.tool_name == "delete_file":
        # 处理 delete_file 工具的逻辑
        file_path= events.args.get("file_path")
        return f"拒绝删除文件 {Path(file_path).name}"
    if events.tool_name == "create_file":
        # 处理 create_file 工具的逻辑
        file_path= events.args.get("file_path")
        return f"拒绝创建文件 {Path(file_path).name}"
    if events.tool_name == "execute_command":
        # 处理 execute_command 工具的逻辑
        command= events.args.get("command")
        command=command.strip()[0:50] + "..." if len(command)>50 else command.strip()
        return f"拒绝运行 {command} "
    if events.tool_name == "run_code":
        # 处理 run_code 工具的逻辑
        filename= events.args.get("filename")
        return f"拒绝执行 {Path(filename).name} "
    if events.tool_name == "undo_operationgroup":
        # 处理 undo_operationgroup 工具的逻辑
        return f"拒绝回滚..."
    else:
        return f"run {events.tool_name} refused:\n {events.user_prompt}"

def try_return_str(events: toolstatusEvent) -> str:
    if events.tool_name == "edit_file":
        # 处理 edit_file 工具的逻辑
        file_path = events.args.get("file_path")
        return f"尝试编辑文件 {Path(file_path).name}"
    if events.tool_name == "delete_file":
        # 处理 delete_file 工具的逻辑
        file_path= events.args.get("file_path")
        return f"尝试删除文件 {Path(file_path).name}"
    if events.tool_name == "create_file":
        # 处理 create_file 工具的逻辑
        file_path= events.args.get("file_path")
        return f"尝试创建文件 {Path(file_path).name}"
    if events.tool_name == "execute_command":
        # 处理 execute_command 工具的逻辑
        command= events.args.get("command")
        command=command.strip()[0:50] + "..." if len(command)>50 else command.strip()
        return f"尝试运行 {command} "
    if events.tool_name == "run_code":
        # 处理 run_code 工具的逻辑
        filename= events.args.get("filename")
        return f"尝试执行 {Path(filename).name} "
    if events.tool_name == "undo_operationgroup":
        # 处理 undo_operationgroup 工具的逻辑
        return f"尝试回滚..."
    else:
        return f"try run {events.tool_name}"