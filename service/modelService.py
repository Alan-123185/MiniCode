
from config.dependencies import create_model, get_db
from config.modelConfig import model_config
from requestcommon.ModelRequest import ModelChooseRequest, ModelUpdateRequest


class modelService:
     def __init__(self,modelmapper):
        self.modelmapper=modelmapper

     def choose_model(self, model_id :int ) -> None:
         model_dict = self.modelmapper.query_model(model_id)
         model_config["value"] = create_model(
             ModelChooseRequest(
                 model_name=model_dict["model_name"],
                 base_url=model_dict["base_url"],
                 api_key=model_dict["api_key"],
                 is_default=model_dict["is_default"]
             ))


     def default_choose_model(self) -> None:
        config=self.modelmapper.reload_settings()
        model_config["value"]=create_model(
            ModelChooseRequest(base_url=config["base_url"],api_key=config["api_key"],
                               model_name=config["model_name"],is_default=config["is_default"])
        )


     def add_model(self, model: ModelChooseRequest) -> None:
        self.modelmapper.add_model(model)

     def  delete_model(self, model_id: int) -> None:
         self.modelmapper.delete_model(model_id)

     def update_model(self, model: ModelUpdateRequest) -> None:
         self.modelmapper.update_model(model)