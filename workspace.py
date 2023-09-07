"""Versioned local workspace storage. No accounts or external synchronization."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from engine import validate_listing
from model_adapter import validate_preferences

def text(value,label,limit=120):
    if not isinstance(value,str) or not 1<=len(value.strip())<=limit:
        raise ValueError(label+' must be nonempty text of at most '+str(limit)+' characters')
    return value.strip()

def corpus(value):
    if not isinstance(value,list) or not 1<=len(value)<=50:
        raise ValueError('Provide 1–50 listings')
    result=[validate_listing(item) for item in value]
    if len({x['id'] for x in result})!=len(result):
        raise ValueError('Listing IDs must be unique')
    return result

class Workspace:
    def __init__(self,path,clock=time.time):
        self.path,self.clock=str(path),clock
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS collections(id TEXT PRIMARY KEY,name TEXT NOT NULL,created REAL NOT NULL,archived INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS collection_versions(collection_id TEXT NOT NULL,version INTEGER NOT NULL,created REAL NOT NULL,provenance TEXT NOT NULL,listings TEXT NOT NULL,PRIMARY KEY(collection_id,version));
            CREATE TABLE IF NOT EXISTS saved_searches(id TEXT PRIMARY KEY,name TEXT NOT NULL,preferences TEXT NOT NULL,created REAL NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()
