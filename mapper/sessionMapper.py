from mappercommon.Session import Session

class sessionMapper:
    def __init__(self,db):
        self.db = db

    def add_session(self, session: Session):
        # Specify columns explicitly to avoid mismatched column count; adjust names if your table differs
        self.db.execute(
            "INSERT INTO session (id, name, workplace, user_id,created_at) VALUES (? ,?, ?, ?,?)",
            (session.session_id, session.session_name , session.workplace, session.user_id,session.create_time,),
        )

    def delete_session(self, session_id: int):
        # Use standard placeholder and pass a single-element tuple for parameters
        self.db.execute("DELETE FROM session WHERE id = ?", (session_id,))

    def query_session_by_workplace(self, workplace: str) -> list[dict] | None:
        return  self.db.fetch_all("SELECT * FROM session WHERE workplace = ?", (workplace,))

    def query_session_by_user_id(self, user_id: int) -> list[dict] | None:
        return  self.db.fetch_all("SELECT * FROM session WHERE user_id = ?", (user_id,))

    def query_session_by_session_id(self, session_id: int) -> dict | None:
        return self.db.fetch_one("SELECT * FROM session WHERE id = ?", (session_id,))

    def update_workplace(self, session_id: int, workplace: str) -> None:
        self.db.execute(
            "UPDATE session SET workplace = ? WHERE id = ?",
            (workplace, session_id,),
        )


    def update_name(self, session_id: int, name: str) -> None:
        self.db.execute("UPDATE session SET name = ? WHERE id = ?", (name, session_id,))

    # def query_session_by_keyword(self, keyword: str) -> list[dict] | None:
    #     # Use LIKE operator with wildcards for partial matching
    #     return self.db.fetch_all("SELECT * FROM session WHERE name LIKE ?", (f"%{keyword}%",))
    #
