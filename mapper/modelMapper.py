import json

from config.data import settings
from exceptions import BizException
from requestcommon.ModelRequest import ModelChooseRequest, ModelUpdateRequest
from requestcommon.settingsRequest import settingsRequest, Settings


class modelMapper:

    def __init__(self,db):
        self.db=db

    def add_model(self, model:ModelChooseRequest) -> None:
        try:
            self.db.conn.execute("BEGIN TRANSACTION")
            if self.db.fetch_one("SELECT COUNT(*) FROM model")["COUNT(*)"]>=settings.MAX_MODEL_COUNT:
                raise BizException(message=f"最多只能添加{settings.MAX_MODEL_COUNT}个模型")

            model_dict=self.db.fetch_one("SELECT * FROM model WHERE model_name = ? AND api_key = ? AND base_url = ?", (model.model_name, model.api_key, model.base_url))
            if model_dict:
                raise BizException(message="模型已存在，请勿重复添加")
            self.db.execute(
                "INSERT INTO model (model_name,api_key,base_url,is_default) VALUES (?, ?, ?, ?)",
                (model.model_name, model.api_key, model.base_url, model.is_default),
            )
            self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise BizException(message=f"Failed to add model: {e}")


    def delete_model(self,id:int) -> None:
        self.db.execute("DELETE FROM model WHERE id = ?", (id,))



    def update_model(self,model: ModelUpdateRequest) -> None:
        try:
            self.db.conn.execute("BEGIN TRANSACTION")
            if model.is_default:
                self.db.conn.execute("UPDATE model SET is_default = 0 WHERE is_default = 1")
                self.db.conn.execute(
                    "UPDATE model SET is_default = 1 WHERE id = ?",(model.id,)
                )
            if model.api_key:
                self.db.conn.execute("UPDATE model SET api_key = ? WHERE id = ?",(model.api_key,model.id))
            if model.base_url:
                self.db.conn.execute("UPDATE model SET base_url = ? WHERE id = ?",(model.base_url,model.id))
            if model.model_name:
                self.db.conn.execute("UPDATE model SET model_name = ? WHERE id = ?",(model.model_name,model.id))
            self.db.conn.commit()
        except Exception as e:
            self.db.conn.rollback()
            raise BizException(message=f"Failed to update model to default: {e}")

    def reload_model_config(self) -> dict:
        model_dict = self.db.fetch_all("select * from model where is_default = 1")
        if not model_dict:
            model_dict = self.db.fetch_one("select * from model order by id desc limit 1")
        if not model_dict:
            raise BizException(message="No default model found")
        return model_dict


    def query_model(self,id:int) -> dict:
        return self.db.fetch_one("select * from model where id = ?", (id,))


    def add_settings(self,settingsrequest:settingsRequest) -> None:
        settings_json = settingsrequest.settings.model_dump_json()
        self.db.execute(
            "INSERT INTO settings (settings, user_id) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET settings = excluded.settings;",
            (settings_json,settingsrequest.user_id),
        )


    def reolad_settings(self,user_id:str) -> Settings:
        settings_json = self.db.fetch_one("select * from settings where user_id = ?", (user_id,))["settings"]
        if not settings_json:
            return Settings()
        sts = Settings.model_validate_json(settings_json)
        return sts

    def reload_all_models(self) -> list[ModelChooseRequest]:
        model_dicts = self.db.fetch_all("select * from model")
        models = [ModelChooseRequest.model_validate(model_dict) for model_dict in model_dicts]
        return models




