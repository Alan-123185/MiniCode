from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from handler import register_exception_handlers
from mapper.database import init_tables
from routers.sessionRouter import router as session_router
from graphs.chat_graph import initialize_graph, close_graph
from routers.workplaceRouter import router as workplace_router
from routers.modelRouter import router as model_router
from routers.chatRouter import router as chat_router
import log
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_tables()
    #  启动时：初始化 LangGraph 和异步数据库
    await initialize_graph()

    yield  # 🏃 保持应用运行，处理请求

    # 🛑 关闭时：清理资源
    await close_graph()

   # ← 就缺这一行
# 将 lifespan 绑定到 FastAPI
app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)
app.include_router(chat_router)
app.include_router(workplace_router)
app.include_router(model_router)
app.include_router(session_router)
"""
the first version, a basical chat robot with some easy tools  2026.8.13
"""
# swagger-ui 静态资源本地化,不依赖外网 CDN
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/docs", include_in_schema=False)
async def swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/static/swagger/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger/swagger-ui.css",
    )


@app.get("/")
async def root():
    return {"message": "Hello World"}



if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)