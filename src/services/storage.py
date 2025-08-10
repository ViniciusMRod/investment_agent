from sqlitedict import SqliteDict

class Storage:
    def __init__(self, db_path: str):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._db = SqliteDict(db_path, autocommit=True)

    def get(self, key, default=None):
        return self._db.get(key, default)

    def set(self, key, value):
        self._db[key] = value

    def append_list(self, key, item):
        lst = self._db.get(key, [])
        lst.append(item)
        self._db[key] = lst
