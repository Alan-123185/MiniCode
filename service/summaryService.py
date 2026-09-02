from mapper.summaryMapper import summaryMapper


class summaryService:
    def __init__(self, summaryMapper: summaryMapper):
        self.summaryMapper = summaryMapper

    def get_tool_content(self, tool_call_id: str):
        """
        根据 tool_call_id 获取对应的 summary
        """
        return self.summaryMapper.get_content_by_tool_call_id(tool_call_id)


    def get_summary_by_compressed_content(self, compressed_content: str):
        """
        根据压缩后的内容获取对应的 summary
        """
        return self.summaryMapper.get_content_by_compressed_content(compressed_content)