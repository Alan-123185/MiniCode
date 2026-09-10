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