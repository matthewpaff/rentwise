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
            CREATE TABLE IF NOT EXISTS comparison_snapshots(id TEXT PRIMARY KEY,name TEXT NOT NULL,created REAL NOT NULL,payload TEXT NOT NULL);
            ''')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()

    def create_collection(self,name,listings,provenance):
        name=text(name,'Collection name')
        provenance=text(provenance,'Import provenance',2000)
        listings=corpus(listings)
        key=uuid.uuid4().hex
        now=self.clock()
        with self.connect() as db:
            db.execute('INSERT INTO collections(id,name,created) VALUES(?,?,?)',(key,name,now))
            db.execute('INSERT INTO collection_versions VALUES(?,?,?,?,?)',(key,1,now,provenance,json.dumps(listings)))
        return self.collection(key)

    def collection(self,key,version=None):
        key=text(key,'Collection ID')
        if version is not None and (type(version) is not int or version<1):
            raise ValueError('Version must be a positive integer')
        with self.connect() as db:
            metadata=db.execute('SELECT * FROM collections WHERE id=?',(key,)).fetchone()
            if not metadata:raise ValueError('Unknown collection')
            row=db.execute('SELECT * FROM collection_versions WHERE collection_id=? AND (? IS NULL OR version=?) ORDER BY version DESC LIMIT 1',(key,version,version)).fetchone()
            if not row:raise ValueError('Unknown collection version')
        return {**dict(metadata),'version':row['version'],'version_created':row['created'],'provenance':row['provenance'],'listings':json.loads(row['listings'])}

    def revise_collection(self,key,listings,provenance,expected_version):
        key=text(key,'Collection ID')
        listings=corpus(listings)
        provenance=text(provenance,'Revision provenance',2000)
        if type(expected_version) is not int or expected_version<1:
            raise ValueError('expected_version must be a positive integer')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            metadata=db.execute('SELECT * FROM collections WHERE id=?',(key,)).fetchone()
            if not metadata or metadata['archived']:raise ValueError('Collection missing or archived')
            latest=db.execute('SELECT MAX(version) FROM collection_versions WHERE collection_id=?',(key,)).fetchone()[0]
            if latest!=expected_version:raise ValueError('Collection changed; reload before saving a revision')
            db.execute('INSERT INTO collection_versions VALUES(?,?,?,?,?)',(key,latest+1,self.clock(),provenance,json.dumps(listings)))
        return self.collection(key)

    def versions(self,key):
        self.collection(key)
        with self.connect() as db:
            rows=db.execute('SELECT version,created,provenance FROM collection_versions WHERE collection_id=? ORDER BY version DESC',(key,)).fetchall()
        return [dict(row) for row in rows]

    def collections(self,include_archived=False):
        if type(include_archived) is not bool:raise ValueError('include_archived must be boolean')
        with self.connect() as db:
            rows=db.execute('SELECT c.*,MAX(v.version) AS version FROM collections c JOIN collection_versions v ON v.collection_id=c.id WHERE (?=1 OR c.archived=0) GROUP BY c.id ORDER BY c.created DESC,c.id',(include_archived,)).fetchall()
        return [dict(row) for row in rows]

    def archive_collection(self,key,archived=True):
        key=text(key,'Collection ID')
        if type(archived) is not bool:raise ValueError('archived must be boolean')
        with self.connect() as db:
            if not db.execute('UPDATE collections SET archived=? WHERE id=?',(archived,key)).rowcount:
                raise ValueError('Unknown collection')
        return self.collection(key)

    def save_search(self,name,preferences):
        name=text(name,'Search name')
        preferences=validate_preferences(preferences)
        key=uuid.uuid4().hex
        with self.connect() as db:
            db.execute('INSERT INTO saved_searches VALUES(?,?,?,?)',(key,name,json.dumps(preferences),self.clock()))
        return {'id':key,'name':name,'preferences':preferences}

    def searches(self):
        with self.connect() as db:
            rows=db.execute('SELECT * FROM saved_searches ORDER BY created DESC,id').fetchall()
        return [{**dict(row),'preferences':json.loads(row['preferences'])} for row in rows]

    def delete_search(self,key):
        key=text(key,'Search ID')
        with self.connect() as db:
            if not db.execute('DELETE FROM saved_searches WHERE id=?',(key,)).rowcount:
                raise ValueError('Unknown saved search')
        return {'deleted':key}

    def diff(self,key,before,after):
        old=self.collection(key,before);new=self.collection(key,after)
        old_items={x['id']:x for x in old['listings']};new_items={x['id']:x for x in new['listings']}
        changed=[]
        for item_id in sorted(old_items.keys() & new_items.keys()):
            fields={field:{'before':old_items[item_id].get(field),'after':new_items[item_id].get(field)} for field in sorted(old_items[item_id].keys()|new_items[item_id].keys()) if old_items[item_id].get(field)!=new_items[item_id].get(field)}
            if fields:changed.append({'id':item_id,'fields':fields})
        return {'id':key,'before_version':old['version'],'after_version':new['version'],'added':sorted(new_items.keys()-old_items.keys()),'removed':sorted(old_items.keys()-new_items.keys()),'changed':changed}

    def save_snapshot(self,name,listings,preferences):
        from decision import evaluate
        name=text(name,'Snapshot name')
        result=evaluate(listings,preferences)
        if not result['results']:raise ValueError('A snapshot requires at least one matching listing')
        key=uuid.uuid4().hex
        payload={'schema':'rentwise.snapshot.v1','sandbox':True,**result}
        with self.connect() as db:
            db.execute('INSERT INTO comparison_snapshots VALUES(?,?,?,?)',(key,name,self.clock(),json.dumps(payload)))
        return self.snapshot(key)

    def snapshot(self,key):
        key=text(key,'Snapshot ID')
        with self.connect() as db:
            row=db.execute('SELECT * FROM comparison_snapshots WHERE id=?',(key,)).fetchone()
        if not row:raise ValueError('Unknown comparison snapshot')
        return {'id':row['id'],'name':row['name'],'created':row['created'],'payload':json.loads(row['payload'])}

    def snapshots(self):
        with self.connect() as db:
            rows=db.execute('SELECT id,name,created FROM comparison_snapshots ORDER BY created DESC,id').fetchall()
        return [dict(row) for row in rows]
