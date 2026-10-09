history_Summary_pro:str="""
本次会话是从之前一段超出上下文的对话继续而来的。
以下摘要覆盖了对话较早的部分。
摘要：
{history_summary}
如果你需要压缩之前的某些具体细节（例如确切的代码片段、错误消息或你生成的内容），请阅读完整对话记录：{transcript_path}

[如果近期消息被原样保留，会说明：Recent messages are preserved verbatim（近期消息按原文保留）。]

请从我们上次中断的地方继续对话，不要再向用户提出任何进一步的问题。
继续处理你最后被要求执行的任务。

"""