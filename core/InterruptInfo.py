from pathlib import Path
from typing import List

from pydantic import BaseModel


class InterruptInfo(BaseModel):
    tool_name: str
    tool_args: dict


def manage_InterruptInfo(interrupt_info: InterruptInfo) -> str:
    if interrupt_info.tool_name == "execute_command":
        command = interrupt_info.tool_args.get("command")
        # 完整下发命令: 前端审批卡片会用等宽字体代码块展示, 让用户批准前看清要执行什么
        return f"我想执行 {command.strip()}"
    if interrupt_info.tool_name == "run_code":
        code = interrupt_info.tool_args.get("code")
        # 完整下发代码: 同上, 用等宽字体代码块展示
        return f"我想运行脚本 {code.strip()}"
    if interrupt_info.tool_name == "edit_file":
        file_path = interrupt_info.tool_args.get("file_path")
        return f"我想编辑 {Path(file_path).name}"
    if interrupt_info.tool_name == "create_file":
        file_path = interrupt_info.tool_args.get("file_path")
        return f"我想创建 {Path(file_path).name}"
    if interrupt_info.tool_name == "delete_file":
        file_path = interrupt_info.tool_args.get("file_path")
        return f"我想删除 {Path(file_path).name}"
    if interrupt_info.tool_name == "undo_operationgroup":
        return f"我将执行回滚操作"
    else:
        return f"我想执行 {interrupt_info.tool_name}"
