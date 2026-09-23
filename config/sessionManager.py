from typing import Dict

from mappercommon.Session import Session


class Sessionmanager:
   def __init__(self) :
    self.session: Dict[str, Session] = {}


   def add_session(self, session_id: str, session: Session):
       self.session[session_id] = session

   def get_session(self, session_id: str) -> Session | None:
         return self.session.get(session_id)


sessionmanager = Sessionmanager()