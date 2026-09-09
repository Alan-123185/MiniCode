
from config.dependencies import create_model, get_db
from config.modelConfig import model_config
from requestcommon.ModelRequest import ModelChooseRequest, ModelUpdateRequest


class modelService:
     def __init__(self,modelmapper):
        self.modelmapper=modelmapper

     def choose_model(self, request: ModelChooseRequest ) -> None:
         model_config["value"] = create_model(
             request
         )


     def old_choose_model(self) -> None:
        config=self.modelmapper.reload_settings()
        model_config["value"]=create_model(
            ModelChooseRequest(base_url=config["base_url"],api_key=config["api_key"],
                               model_name=config["model_name"],is_default=config["is_default"])
        )
