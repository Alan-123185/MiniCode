
from config.data import settings
from config.dependencies import create_model
from config.modelConfig import model_config
from requestcommon.ModelRequest import ModelChooseRequest
from requestcommon.settingsRequest import settingsRequest


class modelService:
    def __init__(self,modelmapper):
        self.modelmapper=modelmapper


    def choose_model(self,request: ModelChooseRequest ) -> None:
         model_config["value"] = create_model(
             request
         )
         self.modelmapper.add_model(request)



    def old_choose_model(self) -> None:
        config=self.modelmapper.reload_model_config()
        model_config["value"]=create_model(
            ModelChooseRequest(base_url=config["base_url"],api_key=config["api_key"],
                               model_name=config["model_name"],is_default=config["is_default"])
        )

    def settings(self,settingrequest:settingsRequest) -> None:

        settings.DEFAULT_TEMPERATURE=settingrequest.settings.temperature
        settings.DEFAULT_THEME=settingrequest.settings.theme
        settings.DEFAULT_THINK_LEVEL=settingrequest.settings.think_level
        #把这个设置存入sqlite
        self.modelmapper.add_settings(settingrequest)
        self.old_choose_model()


    def old_settings(self) -> None:
        self.modelmapper.reolad_settings()
