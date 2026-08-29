from typing import List, Optional


from mappercommon.FileOperation import FileOperation


class FileOperationMapper:
    def __init__(self, db):
        self.db = db

    def add_operation(self, group_id: str, operation: FileOperation) -> int:
        """Insert a new file_operations row. Returns the inserted row id."""
        sql = (
            "INSERT INTO file_operations (group_id, file_path, operation_type, start_line, end_line, old_snippet, new_snippet, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        )
        params = (
            group_id,
            operation.file_path,
            operation.operation_type,
            operation.start_line,
            operation.end_line,
            operation.old_snippet,
            operation.new_snippet,
            operation.created_at,
        )
        return self.db.execute(sql, params)

    def get_operation_by_id(self, op_id: int) -> Optional[dict]:
        """Fetch a single file operation by id."""
        return self.db.fetch_one("SELECT * FROM file_operations WHERE id = ?", (op_id,))


    def list_operations_by_group(self, group_id: str) -> List[dict]:
        """List all file operations for a group."""
        return self.db.fetch_all(
            "SELECT * FROM file_operations WHERE group_id = ? order by created_at desc ",
            (group_id,),
        )


    def delete_operation(self, op_id: int) -> int:
        """Delete a file operation by id."""
        return self.db.execute("DELETE FROM file_operations WHERE id = ?", (op_id,))


    def query_operatons_by_session(self, session_id: str) -> List[dict]:
        """Query all file operations for a session."""
        return self.db.fetch_all("SELECT * FROM file_operations WHERE group_id in  (SELECT id FROM operation_groups WHERE session_id = ?)", (session_id,))

    def delete_operation_by_session(self, session_id: str) -> None:
        self.db.execute("DELETE FROM file_operations WHERE group_id in (select id from operation_groups where session_id=?)", (session_id,))







