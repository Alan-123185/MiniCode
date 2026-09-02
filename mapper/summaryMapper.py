from mappercommon.summary import Summary


class summaryMapper:
    def __init__(self,db):
        self.db = db

    def get_content_by_tool_call_id(self, tool_call_id: str):
        """
        根据 tool_call_id 获取对应的 summary
        """
        self.db.execute("SELECT content FROM summary WHERE tool_call_id = ?", (tool_call_id,))


    def get_content_by_compressed_content(self, compressed_content: str):
        """
        根据压缩后的内容获取对应的 summary
        """
        self.db.execute(
        "SELECT content FROM summary WHERE compressed_content LIKE ?",
        (f"%{compressed_content}%",)
        )

    def add_summary(self,summary:Summary):
        """
        添加 summary
        """
        self.db.execute(
            "INSERT INTO summary (session_id, tool_call_id, message_type, compressed_content, content) VALUES (?, ?, ?, ?, ?)",
            (summary.session_id, summary.tool_call_id, summary.message_type, summary.compressed_content, summary.content),
        )
