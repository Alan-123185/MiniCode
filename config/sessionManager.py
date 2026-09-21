from typing import Dict

from mappercommon.Session import Session
from sandbox_executor.MXCExecutor import MxcExecutor


class Sessionmanager:
   def __init__(self) :
    self.session: Dict[str, Session] = {}
    self.executor: Dict[str, MxcExecutor] = {}

sessionmanager = Sessionmanager()