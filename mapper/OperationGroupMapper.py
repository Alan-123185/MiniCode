from typing import Optional
from mappercommon.operationGroup import OperationGroup

class operatinoGroupMapper:
    def __init__(self, db):
        self.db = db
    def select_group_by_prompt(self, prompt: str) -> str:
       return self.db.fetch_one("SELECT id FROM operation_groups WHERE user_prompt like ? and 1=1", (prompt,))

    def get_operation_group_by_id(self, session_id: int) -> Optional[dict]:
        return self.db.fetch_all("SELECT * FROM operation_groups WHERE session_id = ? and 1=1", (session_id,))

    def update_group_undo(self, group_id:  int) -> None:
        self.db.execute("UPDATE operation_groups SET is_undone =  1 WHERE id = ? and 1=1", (group_id,))


    def add_operation_group(self, operation_group: OperationGroup) -> None:
        self.db.execute("INSERT INTO operation_groups (session_id, user_prompt, created_at, is_undone) VALUES (?, ?, ? ,?)",
                   params=(operation_group.session_id, operation_group.user_prompt,operation_group.created_at, operation_group.is_undone)
                   )

    def query_operation_by_session(self, session_id: str) -> list[dict] :
        return self.db.fetch_all("SELECT * FROM operation_groups WHERE session_id = ? and 1=1 order by created_at desc", (session_id,))

    def query_current_operation(self, session_id: str) -> Optional[dict]:
        return self.db.fetch_one("SELECT id FROM operation_groups WHERE session_id = ? and is_undone==0 order by created_at desc limit 1", (session_id,))


    def list_group_to_undo(self, session_id: str,current_group_id:str,target_group_id:str) -> list[dict]:
        return self.db.fetch_all("SELECT id FROM operation_groups WHERE session_id = ? and created_at between "
                                 "(select created_at from operation_groups where id=? , select created_at from operation_groups where id=?)  "
                                 " order by created_at desc",params=(session_id,current_group_id,target_group_id,))

    def delete_operation_group(self, session_id: str) -> None:
        self.db.execute("DELETE FROM operation_groups WHERE session_id = ?", (session_id,))


