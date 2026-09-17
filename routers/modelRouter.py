from fastapi import APIRouter
from fastapi.params import Depends
from core.Result import Result
from requestcommon.ModelRequest import ModelChooseRequest
from requestcommon.settingsRequest import settingsRequest
from service.dependencies import get_model_service
from service.modelService import modelService

router = APIRouter()

@router.post("/MiniCode/model")
async def choose_model(request: ModelChooseRequest,model_service:modelService=Depends(get_model_service)):
    model_service.choose_model(request)
    return Result(
        message=f"模型已经切换至{request.model_name}",
        response=request
    )


@router.post("/MiniCode/settings")
async def settings( settingsrequest:settingsRequest, model_service:modelService=Depends(get_model_service)):
    model_service.settings(settingsrequest)
    return Result(
        message=f"设置成功",
        response=settingsrequest
    )


@router.get("/MiniCode/get_settings/{user_id}")
async def get_settings(user_id: str, model_service:modelService=Depends(get_model_service)):
    return Result(
        response=model_service.get_settings(user_id)
    )


@router.get("/MiniCode/get_model")
async def get_model(model_service:modelService=Depends(get_model_service)):
    return Result(
        response=model_service.get_model()
    )
