import json
from fastapi import APIRouter, Depends, FastAPI, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from langchain_core.messages import BaseMessage
from starlette.responses import StreamingResponse
from config.data import  settings
from config.dependencies import get_session, create_chat_config
from config.sessionManager import sessionmanager
from core.Result import Result
from requestcommon.chatRequest import ChatRequest
from requestcommon.decisionRequst import decisionRequst
from service.chatService import ChatService
from service.dependencies import get_chat_service
from utils.titleCreateTool import new_title

router = APIRouter()

"""
  这是一个测试用的 SSE 接口。
  它会流式传输llm的回复
  """
@router.post("/MiniCode/chat")
async def chat_to_agent(chat_request: ChatRequest,background_tasks:BackgroundTasks , chat_service: ChatService=Depends(get_chat_service)):
    async def event_generator():
        async for interrupt_result in chat_service.chat(chat_request):
            # 情况一：需要用户审批
            if interrupt_result.type == settings.interrupt_type_approve:
                result = Result(message=interrupt_result.message)
            # 情况二：最终结果
            elif interrupt_result.type == settings.interrupt_type_result:
                result = Result(
                    message=interrupt_result.agentResult.answer,
                    response=interrupt_result.agentResult
                )

                if get_session(create_chat_config(chat_request.session_id)).session_name!="新会话":
                    background_tasks.add_task(
                        new_title,
                   chat_request.session_id,
                        [chat_request.message,interrupt_result.agentResult.answer]
                    )
            # 情况三：中间自定义事件
            else:
                result = Result(message=str(interrupt_result.message))

            yield f"data: {json.dumps( jsonable_encoder(result), ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/MiniCode/approve")
async def approve(decision_request:decisionRequst, background_tasks:BackgroundTasks,chat_service: ChatService=Depends(get_chat_service)):
    async def event_generator():
       async for interrupt_result in chat_service.approve(
                decision_request
        ):
            if interrupt_result.type == settings.interrupt_type_approve:
                result = Result(message=interrupt_result.message)

            elif interrupt_result.type == settings.interrupt_type_result:
                result = Result(
                    message=interrupt_result.agentResult.answer,
                    response=interrupt_result.agentResult
                )

            else:
                result = Result(message=str(interrupt_result.message))

            yield f"data: {json.dumps(jsonable_encoder(result), ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/MiniCode/new_chat")
async def new_chat(request: ChatRequest,chat_service: ChatService=Depends(get_chat_service)) -> Result[str]:
    chat_service.new_chat(request)
    return Result(message="已创建新对话")

