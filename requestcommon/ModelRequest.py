from typing import Optional

from pydantic import BaseModel

from config.data import settings


class ModelSetRequest(BaseModel):
    base_url: str = settings.DEFAULT_BASE_URL
    api_key: str = settings.DEFAULT_API_KEY
    model_name: str = settings.DEFAULT_MODEL
    is_default: bool = False


class ModelGetRequest(BaseModel):
    id: int
    base_url: str
    api_key: str
    model_name: str
    is_default: bool


class ModelUpdateRequest(BaseModel):
    id: int
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    is_default: Optional[bool] = None
