from fastapi import APIRouter
from fastapi.params import Depends
from core.Result import Result
from requestcommon.ModelRequest import ModelChooseRequest
from service.dependencies import get_model_service
from service.modelService import modelService

router = APIRouter()

@router.post("/MiniCode/model")
async def choose_model(request: ModelChooseRequest,model_service:modelService=Depends(get_model_service)):
    model_service.choose_model(request)
    return Result(
        message=f"模型已经切换至{request.model}"
    )


@router.get("/MiniCode/old_model")
async def get_model(model_service:modelService=Depends(get_model_service)):
    model_service.old_choose_model()
    return Result()