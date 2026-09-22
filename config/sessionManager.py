from typing import Dict

from mappercommon.Session import Session
from sandbox_executor.MXCExecutor import MxcExecutor


class Sessionmanager:
   def __init__(self) :
    self.session: Dict[str, Session] = {}
    self.executor: Dict[str, MxcExecutor] = {}


   def add_session(self, session_id: str, session: Session):
       self.session[session_id] = session

   def add_executor(self, session_id: str, executor: MxcExecutor):
         self.executor[session_id] = executor

   def get_session(self, session_id: str) -> Session | None:
         return self.session.get(session_id)

   def get_executor(self, session_id: str) -> MxcExecutor | None:
         return self.executor.get(session_id)


sessionmanager = Sessionmanager()