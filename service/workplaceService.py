from config.dependencies import create_chat_config
from config.sessionManager import sessionmanager
from exceptions import BizException
from mappercommon.Session import Session
from requestcommon import workplaceRequest

class WorkplaceService:

    def __init__(self,graph,sessionMappper):
        self.graph = graph
        self.sessionMapper = sessionMappper

    async def choose_workplace(self,request: workplaceRequest) -> None:
        config=create_chat_config(thread_id=request.session_id)
        session_dict=self.sessionMapper.query_session_by_session_id(request.session_id)
        new_session = Session(
            session_id=request.session_id,
            session_name=session_dict["name"] if session_dict else "新会话",
            user_id=request.user_id,
            workplace=request.workplace
        )

        if not session_dict:
            self.sessionMapper.add_session(
                new_session
            )

        elif not session_dict["workplace"]:
            self.sessionMapper.update_workplace(workplace=request.workplace,session_id=request.session_id)

        else:
            raise BizException(message="已经选定目录，无法更改，请创建新对话")

        sessionmanager[request.session_id]=new_session

