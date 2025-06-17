import json
import sqlitedict
import logging

class Db(sqlitedict.SqliteDict):
    def __init__(self, *args, **argv) -> None:
        super().__init__(*args, **argv)
        logging.basicConfig(level = logging.INFO)

    def __setitem__(self, key, item):
        
        if type(item) is not str:
            item = json.dumps(item)
        
        if len(item) > 10000:
            raise Exception('Max len in write to database!')

        super().__setitem__(key, item)

    def __getitem__(self, key):
        parent = super()
        value = parent.__getitem__(key)
        try:
            value = json.loads(value)
        except:
            pass
        if value == '':
            return []
        return value

    def __repr__(self):
        return '<Sqlite DB>'

