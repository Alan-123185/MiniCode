class settingMapper:
    def __init__(self, db):
        self.db = db


    def add_setting(self, user_id: int, settings: str) -> None:
        self.db.execute(
            "INSERT INTO settings (user_id, settings) VALUES (?, ?)",
            (user_id, settings),
        )

    # def default_setting(self, key: str) -> None:
