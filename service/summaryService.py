from mapper.database import DataBase
from mapper.summaryMapper import summaryMapper
from mappercommon.summary import Summary


class summaryService:

    def add_Tool_summary(self, summary: Summary) -> None:
        db = DataBase()
        try:
            summaryMapper(db).add_Tool_summary(summary)
        finally:
            db.conn.close()

    def add_LLM_summary(self,summary:Summary) -> None:
        """
        添加 LLM 的 summary
        """
        db=DataBase()
        try:
            summaryMapper(db).add_LLM_summary(summary)
        finally:
            db.conn.close()

    def query_tool_summary(self,tool_call_id:str) -> dict:
        """
        查询 tool_call_id 对应的 summary
        """
        db=DataBase()
        try:
            return summaryMapper(db).query_tool_summary(tool_call_id)
        finally:
            db.conn.close()

    def query_LLM_summary(self,memory_id:str) -> dict:
        """
        查询 memory_id 对应的 summary
        """
        db=DataBase()
        try:
            return summaryMapper(db).query_LLM_summary(memory_id)
        finally:
            db.conn.close()


    def get_content_by_compressed_content(self,memory_id: str) -> dict:
        """
        根据压缩后的内容获取对应的 summary
        """
        db=DataBase()
        try:
            return summaryMapper(db).get_content_by_compressed_content(memory_id)
        finally:
            db.conn.close()


    def get_content_by_tool_call_id(self,tool_call_id:str) -> dict:
        """
        根据 tool_call_id 获取对应的 summary
        """
        db=DataBase()
        try:
            return summaryMapper(db).get_content_by_tool_call_id(tool_call_id)
        finally:
            db.conn.close()