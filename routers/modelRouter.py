from fastapi import APIRouter
from fastapi.params import Depends
from config.modelConfig import model_config
from core.Result import Result
from requestcommon.ModelRequest import ModelSetRequest, ModelUpdateRequest
from requestcommon.settingsRequest import settingsRequest
from service.dependencies import get_model_service
from service.modelService import modelService

router = APIRouter()

@router.post("/MiniCode/add_model")
async def add_model(request: ModelSetRequest, model_service:modelService=Depends(get_model_service)):
    model_service.add_model(request)
    return Result(
        message=f"模型已经添加至{request.model_name}",
        response=request
    )



@router.post("/MiniCode/set_model")
async def set_model(id:int, model_service:modelService=Depends(get_model_service)):
    model=model_service.set_model(id)
    return Result(
        message=f"模型已经设置为{model.model_name}",
        response=model
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


@router.get("/MiniCode/cur_model")
async def cur_model():
    return Result(
        response=model_config["value"]
    )



@router.post("MiniCode/delete_model")
async def delete_model(id:int, model_service:modelService=Depends(get_model_service)):
    model_service.delete_model(id)
    return Result(
        message=f"模型已经删除",
        response=id
    )


@router.post("/MiniCode/update_model")
async def update_model(request:ModelUpdateRequest, model_service:modelService=Depends(get_model_service)):
    model=model_service.update_model(request)
    return Result(
        message=f"模型配置已更新",
        response=model
    )