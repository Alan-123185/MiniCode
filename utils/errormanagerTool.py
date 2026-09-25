#错误堆栈压缩函数
def compress_error(error_msg: str, max_length: int = 200) -> str:
    """
    压缩错误信息，只保留 LLM 需要的核心内容。
    """
    error_msg = str(error_msg).strip()
    lines = error_msg.split('\n')

    if len(lines) <= 3:
        # 短错误，直接返回
        return error_msg
    # 只保留最后 2 行（通常是错误类型 + 错误描述）
    # 例如：
    #   FileNotFoundError: [Errno 2] No such file or directory: '/src/main.py'
    #   PermissionError: [Errno 13] Permission denied: '/etc/config'
    core_error = '\n'.join(lines[-2:])

    # 防止极端情况（最后一行特别长）
    if len(core_error) > max_length:
        core_error = core_error[:max_length] + "..."

    return core_error
