
from config.data import settings
from config.dependencies import create_model
from config.modelConfig import model_config
from exceptions import BizException
from requestcommon.ModelRequest import ModelGetRequest, ModelSetRequest
from requestcommon.settingsRequest import settingsRequest, Settings


class modelService:
    def __init__(self,modelmapper):
        self.modelmapper=modelmapper


    def add_model(self,request: ModelSetRequest ) -> None:
        self.modelmapper.add_model(request)
        model_config["value"] = create_model(
             request
        )

    def set_model(self,id:int) -> ModelSetRequest:
        model=self.modelmapper.query_model(id)
        if model:
            model_config["value"] = create_model(
                model
            )
            return model
        else:
            raise BizException(message="模型不存在")







    def old_choose_model(self) -> ModelSetRequest:
        config=self.modelmapper.reload_model_config()
        model = ModelSetRequest(base_url=config["base_url"], api_key=config["api_key"],
                                     model_name=config["model_name"], is_default=config["is_default"])
        model_config["value"]=create_model(
           model
        )
        return model

    def settings(self,settingrequest:settingsRequest) -> None:

        settings.DEFAULT_TEMPERATURE=settingrequest.settings.temperature
        settings.DEFAULT_THEME=settingrequest.settings.theme
        settings.DEFAULT_THINK_LEVEL=settingrequest.settings.think_level
        #把这个设置存入sqlite
        self.modelmapper.add_settings(settingrequest)
        self.old_choose_model()


    def old_settings(self) -> None:
        user_id=self.modelmapper.reload_user_model()
        sts= self.modelmapper.reolad_settings(user_id)
        settings.DEFAULT_THINK_LEVEL = sts.think_level
        settings.DEFAULT_TEMPERATURE = sts.temperature
        settings.DEFAULT_THEME = sts.theme



    def get_settings(self,user_id:str) -> Settings:
        sts= self.modelmapper.reolad_settings(user_id)
        return sts

    def get_model(self) -> list[ModelGetRequest]:
        models=self.modelmapper.reload_all_models()
        return models