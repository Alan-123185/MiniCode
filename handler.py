# app/handlers.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from exceptions import BizException


def register_exception_handlers(app: FastAPI):
    """注册所有异常处理器"""

    # 1. 服务异常
    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException):
        return JSONResponse(
            status_code=exc.code if exc.code < 500 else 500,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": None
            }
        )

    # 2. HTTP 异常（如 FastAPI 内置的 HTTPException）
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "message": str(exc.detail),
                "data": None
            }
        )

    # 3. 参数校验异常（Pydantic 校验失败）
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"]
            })
        return JSONResponse(
            status_code=422,
            content={
                "code": 422,
                "message": "参数校验失败",
                "data": errors
            }
        )

    # 4. 未知异常（兜底）
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "message": "服务器异常",
                "data": None
            }
        )