# -*- coding: utf-8 -*-
import os, sqlite3, time

class Database(object):
    def __init__(self, path):
        folder=os.path.dirname(path)
        if not os.path.isdir(folder): os.makedirs(folder)
        self.path=path
        self._init()
    def _connect(self):
        c=sqlite3.connect(self.path, timeout=10)
        c.execute('PRAGMA journal_mode=WAL')
        return c
    def _init(self):
        with self._connect() as c:
            c.execute('CREATE TABLE IF NOT EXISTS prayer_cache (day TEXT PRIMARY KEY, payload TEXT NOT NULL, created INTEGER NOT NULL)')
            c.execute('CREATE TABLE IF NOT EXISTS fired_events (event_key TEXT PRIMARY KEY, fired INTEGER NOT NULL)')
    def get_day(self, day):
        import json
        with self._connect() as c:
            row=c.execute('SELECT payload FROM prayer_cache WHERE day=?',(day,)).fetchone()
        return json.loads(row[0]) if row else None
    def put_day(self, day, payload):
        import json
        with self._connect() as c:
            c.execute('INSERT OR REPLACE INTO prayer_cache(day,payload,created) VALUES(?,?,?)',(day,json.dumps(payload,ensure_ascii=False),int(time.time())))
    def mark_fired(self, key):
        with self._connect() as c:
            cur=c.execute('INSERT OR IGNORE INTO fired_events(event_key,fired) VALUES(?,?)',(key,int(time.time())))
            return cur.rowcount == 1
