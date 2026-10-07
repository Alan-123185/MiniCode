from langchain_core.messages import BaseMessage, AIMessage, ToolMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from config.data import settings
from context.compressMessage import snip_message
from context.degradeWindows import degrade_windows_l1, degrade_windows_l2
from states.OverallState import OverAllState
from utils.MessageTool import count_tokens


def pre_call_func(state: OverAllState,config:RunnableConfig) -> list[BaseMessage]:
    # 先把窗口内消息拿出来
    system_prompt = config["configurable"]["system_prompt"].format(history_summary=state.summary_state)
    system_message = [SystemMessage(content=system_prompt)]
    windows_message = state.messages[state.last_summary_pos:]
    windows_message = snip_message(windows_message)  # 先把低价值消息丢掉
    """
    10.2 我决定放开豁免最新的用户消息的限制，统一处理，无论是否最新
    """
    current_message=[]
    for i in range(len(windows_message) - 1, -1, -1):
        if isinstance(windows_message[i], HumanMessage):
            current_message = windows_message[i:]   #这一部分消息是最新的用户消息，必须保留
            windows_message = windows_message[:i]   #这一部分消息是窗口内的历史消息，可能需要降级
            break
    latest_message=[]
    msg_len = len(current_message)
    i=msg_len-1
    c=0
    while i>=0 and c< settings.KEEP_RECENT_COUNT:
        msg = current_message[i]
        latest_message.insert(0, msg)
        current_message.pop(i)
        if isinstance(msg, ToolMessage):
            c+=1
        i-=1
    system_tokens=count_tokens(system_message)
    windows_tokens = count_tokens(windows_message)
    current_tokens = count_tokens(current_message)
    all_tokens=windows_tokens+current_tokens+system_tokens+settings.TOOL_SCHEMA_TOKENS
    delta_tokens = all_tokens - settings.LLM_MAX_UP_MESSAGE_TOKEN
    #如果超过了最大限制，先降级窗口内的消息，再降级当前消息
    if delta_tokens>0:
        windows_message, delta_tokens = degrade_windows_l1(windows_message, delta_tokens, config)
    if delta_tokens>0:
        current_message, delta_tokens = degrade_windows_l1(current_message, delta_tokens, config)
    if delta_tokens>0:
        windows_message , delta_tokens = degrade_windows_l2(windows_message, delta_tokens)
    if delta_tokens>0:
        current_message , delta_tokens = degrade_windows_l2(current_message, delta_tokens)
    return system_message+windows_message+current_message+latest_message

