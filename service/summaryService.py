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

    def query_tool_summary(self,tool_call_id:str):
        """
        查询 tool_call_id 对应的 summary
        """
        db=DataBase()
        try:
            return summaryMapper(db).query_tool_summary(tool_call_id)
        finally:
            db.conn.close()

    def query_LLM_summary(self,memory_id:str):
        """
        查询 memory_id 对应的 summary
        """
        db=DataBase()
        try:
            return summaryMapper(db).query_LLM_summary(memory_id)
        finally:
            db.conn.close()