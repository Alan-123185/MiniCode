from fastapi import APIRouter, Depends
from core.Result import Result
from requestcommon.workplaceRequest import WorksplaceRequest
from service import workplaceService
from service.dependencies import get_workplace_service

router = APIRouter()

@router.post("/MiniCode/workplace")
async def choose_workplace(request: WorksplaceRequest,workplace_service:workplaceService=Depends(get_workplace_service)):
    await workplace_service.choose_workplace(request)
    return Result(
        message=f"工作目录已经移至{request.workplace}",
        response=request
    )


