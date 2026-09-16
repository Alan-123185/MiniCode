from pydantic import BaseModel, Field
from config.data import settings



class Settings(BaseModel):
    temperature: float = Field(default=settings.DEFAULT_TEMPERATURE,description="模型温度，范围0~2，越大越随机，越小越确定")
    theme: bool = Field(default=settings.DEFAULT_THEME, description="主题，True为浅色模式，False为深色模式")
    think_level: int = Field(default=settings.DEFAULT_THINK_LEVEL,description="思考等级，范围1~3，越大越深度思考，越小越快速响应")


class settingsRequest(BaseModel):
    user_id:str
    settings:Settings