from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from config.dependencies import get_session
from config.modelConfig import model_config
from config.sessionManager import sessionmanager
from prompt.title_prompt import TITLE_PROMPT
from states.OverallState import OverAllState
from mapper.sessionMapper import sessionMapper

def title_node(state:OverAllState,config:RunnableConfig) -> OverAllState:
    model = model_config["value"]
    messages = state.messages
    first_message={}
    for message in messages:
        if isinstance(message, HumanMessage):
            first_message["user"] = message
        elif isinstance(message, AIMessage):
            first_message["assistant"] = message
            break
    title_prompt=TITLE_PROMPT.format(first_message=first_message)
    title = model.invoke(SystemMessage(content=title_prompt))
    old_session = get_session(config)
    old_session.session_name=title
    sessionmanager[old_session.session_id] = old_session
    sessionMapper.update_name(session_id=old_session.session_id, name=title)
    return {}