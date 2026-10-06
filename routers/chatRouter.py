import asyncio
import json
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from loguru import logger
from starlette.responses import StreamingResponse
from config.data import  settings
from config.dependencies import get_session, create_chat_config
from core.Result import Result
from requestcommon.chatRequest import ChatRequest
from requestcommon.decisionRequst import decisionRequst
from requestcommon.editMessageRequest import editMessageRequest
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
            try:
                async for interrupt_result in chat_service.chat(chat_request):
                    # 情况一：需要用户审批
                    if interrupt_result.type == settings.interrupt_type_approve:
                        result = Result(message=interrupt_result.message)
                    # 情况二：最终结果
                    elif interrupt_result.type == settings.interrupt_type_result:
                        result = Result(
                            message=(interrupt_result.agentResult.answer if interrupt_result.agentResult else "") or "",
                            response=interrupt_result.agentResult
                        )

                        if get_session(create_chat_config(chat_request.session_id)).session_name=="新会话":
                            background_tasks.add_task(
                                new_title,
                           chat_request.session_id,
                                [chat_request.message,interrupt_result.agentResult.answer]
                            )
                    # 情况三：中间自定义事件
                    else:
                        result = Result(message=str(interrupt_result.message))

                    yield f"data: {json.dumps( jsonable_encoder(result), ensure_ascii=False)}\n\n"

            except asyncio.CancelledError:
                raise
            # except Exception as e:
            #     err = Result(message=f"服务异常：{e}")
            #     logger.exception(f"服务异常：{e}")  # 关键：把 traceback 打进日志
            #     yield f"data: {json.dumps(jsonable_encoder(err), ensure_ascii=False)}\n\n"

        return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/MiniCode/approve")
async def approve(decision_request:decisionRequst,chat_service: ChatService=Depends(get_chat_service)):
    async def event_generator():
        try:
           async for interrupt_result in chat_service.approve(decision_request):
            if interrupt_result.type == settings.interrupt_type_approve:
                result = Result(message=interrupt_result.message)

            elif interrupt_result.type == settings.interrupt_type_result:
                result = Result(
                    message=(interrupt_result.agentResult.answer if interrupt_result.agentResult else "") or "",
                    response=interrupt_result.agentResult
                )

            else:
                result = Result(message=str(interrupt_result.message))
            yield f"data: {json.dumps(jsonable_encoder(result), ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            raise
        # except Exception as e:
        #     err = Result(message=f"服务异常：{e}")
        #     logger.exception(f"服务异常：{e}")  # 关键：把 traceback 打进日志
        #     yield f"data: {json.dumps(jsonable_encoder(err), ensure_ascii=False)}\n\n"



    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

@router.post("/MiniCode/new_chat")
async def new_chat(request: ChatRequest,chat_service: ChatService=Depends(get_chat_service)) -> Result[str]:
    chat_service.new_chat(request)
    return Result(message="已创建新对话")


#新增一个时间旅行接口
@router.post("/MiniCode/editMessage")
async def edit_message(edit_message_request: editMessageRequest, chat_service: ChatService=Depends(get_chat_service)):

    async def event_generator():
        try:
            async for interrupt_result in chat_service.edit_message(
                session_id=edit_message_request.session_id,
                message_id=edit_message_request.message_id,
                new_content=edit_message_request.new_content
            ):
                if interrupt_result.type == settings.interrupt_type_approve:
                    result = Result(message=interrupt_result.message)

                elif interrupt_result.type == settings.interrupt_type_result:
                    result = Result(
                        message=interrupt_result.agentResult.answer if interrupt_result.agentResult else "",
                        response=interrupt_result.agentResult
                    )
                else:
                    result = Result(message=str(interrupt_result.message))

                yield f"data: {json.dumps(jsonable_encoder(result), ensure_ascii=False)}\n\n"

        except asyncio.CancelledError:
            raise
        # except Exception as e:
        #     err = Result(message=f"服务异常：{e}")
        #     logger.exception(f"服务异常：{e}")  # 关键：把 traceback 打进日志
        #     yield f"data: {json.dumps(jsonable_encoder(err), ensure_ascii=False)}\n\n"

    return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )

#会话因为异常中断的恢复接口
@router.post("/MiniCode/continue")
async def continue_chat(session_id: str, chat_service: ChatService=Depends(get_chat_service)):

    async def event_generator():
        try:
            async for interrupt_result in  chat_service.refresh_chat(session_id):
                if interrupt_result.type == settings.interrupt_type_approve:
                    result = Result(message=interrupt_result.message)

                elif interrupt_result.type == settings.interrupt_type_result:
                    result = Result(
                        message=(interrupt_result.agentResult.answer if interrupt_result.agentResult else "") or "",
                        response=interrupt_result.agentResult
                    )

                else:
                    result = Result(message=str(interrupt_result.message))
                yield f"data: {json.dumps(jsonable_encoder(result), ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            raise
        # except Exception as e:
        #     err = Result(message=f"服务异常：{e}")
        #     logger.exception(f"服务异常：{e}")  # 关键：把 traceback 打进日志
        #     yield f"data: {json.dumps(jsonable_encoder(err), ensure_ascii=False)}\n\n"
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.post("/MiniCode/stop")
async def stop_chat(session_id: str, chat_service: ChatService=Depends(get_chat_service)) -> Result[str]:
    res = await chat_service.stop_chat(session_id)
    if res:
        return Result(message="已停止对话")
    else:
        return Result(message="终止失败")


