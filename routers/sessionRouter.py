from fastapi import APIRouter, Depends
from langchain_core.messages import BaseMessage

from core.Result import Result
from service.sessionService import sessionService
from service.dependencies import get_session_service

router = APIRouter()

@router.get("/MiniCode/sessions")
async def list_session(user_id: str, session_service:sessionService = Depends(get_session_service)):
    return Result(response=session_service.list_session(user_id=user_id))


@router.post("/MiniCode/history")
async def get_history(session_id: str, session_service: sessionService = Depends(get_session_service)) -> Result[list[BaseMessage]]:
    history_messages = await session_service.get_history(session_id)
    return Result(response=history_messages)


@router.post("/MiniCode/deleteChat")
async def delete_chat(session_id: str, session_service: sessionService = Depends(get_session_service)):
    await session_service.delete_chat(session_id)
    return Result.success()
