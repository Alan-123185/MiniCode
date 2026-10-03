"""
新增当前任务的总结节点
"""

def task_summary_node(task: dict) -> str:
    task_name = task.get('task_name', '未命名任务')
    task_description = task.get('task_description', '无描述')

    summary = f"任务名称: {task_name}\n任务描述: {task_description}"
    return summary