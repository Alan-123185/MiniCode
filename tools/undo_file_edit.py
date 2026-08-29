from langchain_core.tools import tool
from loguru import logger
from config.dependencies import get_db
from core.toolResult import toolResult
from mapper.OperationGroupMapper import operatinoGroupMapper
from mapper.fileMapper import FileOperationMapper
from utils.editFileTools import file_edit_tool, create_file_tool, delete_file_tool


@tool
def undo_operationgroup(target_group_id: str, session_id: str) -> toolResult:
    """
    回滚到传入的操作组id的版本。
    会撤销从当前版本到目标版本之间的所有操作组。

    :param target_group_id: 需要回退到的操作组id
    :param session_id: 当前会话id
    :return: 返回一个工具调用结果类
    """
    db = get_db()
    file_operation_mapper = FileOperationMapper(db)
    operation_group_mapper = operatinoGroupMapper(db)
    current_group_id = operation_group_mapper.query_current_operation(session_id=session_id)["id"]
    try:
        # 1. 查出需要撤销的操作组列表（从新到旧）
        list_to_undo = operation_group_mapper.list_group_to_undo(
            session_id=session_id,
            current_group_id=current_group_id,
            target_group_id=target_group_id
        )

        if not list_to_undo:
            return toolResult(
                success=False,
                message="没有需要回滚的操作",
                content="",
                tool_name="undo_operationgroup"
            )

        errors = []

        # 2. 从新到旧，逐个操作组回滚
        for group in list_to_undo:
            group_id = group["id"]
            operation_list = file_operation_mapper.list_operations_by_group(group_id)
            for operation in operation_list:
                try:
                    op_type = operation['operation_type']

                    if op_type == 'file_edit':
                        new_content = operation.get("new_content", "")
                        new_line_count = len(new_content.splitlines())

                        if new_line_count == 0:
                            # new_content 为空（删除行操作），回滚就是插入
                            end_line = operation["start_line"] - 1
                        else:
                            end_line = operation["start_line"] + new_line_count - 1

                        file_edit_tool(
                            file_path=operation['file_path'],
                            start_line=operation['start_line'],
                            end_line=end_line,
                            new_content=operation['old_snippet']
                        )

                    elif op_type == 'delete_file':
                        # 撤销删除：重新创建文件
                        create_file_tool(
                            file_path=operation['file_path'],
                            content=operation['old_snippet']
                        )

                    elif op_type == 'create_file':
                        # 撤销创建：删除文件
                        delete_file_tool(
                            file_path=operation['file_path']
                        )

                except Exception as e:
                    errors.append(
                        f"操作组 {group_id}，文件 {operation.get('file_path', '未知')}："
                        f"{type(e).__name__}",
                    )
            operation_group_mapper.update_group_undo(group_id)

        if errors:
            logger.error(errors)
            return toolResult(
                success=False,
                error=f"部分回滚失败：{'; '.join(errors)}",
                tool_name="undo_operationgroup"
            )

        return toolResult(
            success=True,
            message="回滚成功",
            content=f"已回滚到操作组 {target_group_id} 的版本",
            tool_name="undo_operationgroup"
        )
    finally:
        db.close()

@tool
def query_operationgroup(session_id:str) -> toolResult:
    """
    当用户需要回滚或者复原代码时，必须先调用这个工具拿到操作组id和session_id，然后传入undo_operationgroup这个工具函数实现回滚
    根据会话id查询它的所有操作组，llm可以根据返回的操作组列表内容判断用户需要回滚的具体版本是哪个group_id
    :param session_id: 会话id
    :return: 返回一个工具调用结果类
    """
    db=get_db()
    operation_group_mapper = operatinoGroupMapper(db)
    group_list = operation_group_mapper.query_operation_by_session(session_id)
    return toolResult(success=True, message=f"当前会话{session_id}下的操作组：",content=str(group_list),tool_name="query_operationgroup")