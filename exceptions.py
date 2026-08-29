class BizException(Exception):
    """业务异常基类"""
    def __init__(self, code: int = 400, message: str = "业务异常"):
        self.code = code
        self.message = message
        super().__init__(self.message)


class NotFoundException(BizException):
    """资源不存在"""
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=404, message=message)


class UnauthorizedException(BizException):
    """未授权"""
    def __init__(self, message: str = "未授权，请先登录"):
        super().__init__(code=401, message=message)


class ForbiddenException(BizException):
    """无权限"""
    def __init__(self, message: str = "无权限访问"):
        super().__init__(code=403, message=message)


class BadRequestException(BizException):
    """参数错误"""
    def __init__(self, message: str = "参数错误"):
        super().__init__(code=400, message=message)


class InternalErrorException(BizException):
    """服务器内部错误"""
    def __init__(self, message: str = "服务器异常"):
        super().__init__(code=500, message=message)

