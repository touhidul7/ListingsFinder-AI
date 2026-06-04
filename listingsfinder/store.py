import sqlite3,json
from .config import DB_PATH
from .sources import DEFAULT_SOURCES
def connect():
    con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; return con
def init_db():
    con=connect(); cur=con.cursor(); cur.execute('create table if not exists sources (name text primary key,data text not null)'); cur.execute('create table if not exists runs (run_id text primary key,data text not null,created_at text default current_timestamp)'); cur.execute('create table if not exists listings (listing_id text primary key,data text not null)')
    if cur.execute('select count(*) c from sources').fetchone()['c']==0:
        for s in DEFAULT_SOURCES: cur.execute('insert or replace into sources values (?,?)',(s['Source Name'],json.dumps(s)))
    con.commit(); con.close()
def get_sources(): init_db(); con=connect(); rows=con.execute("select data from sources order by json_extract(data,'$.Priority'), name").fetchall(); con.close(); return [json.loads(r['data']) for r in rows]
def replace_sources(sources):
    init_db(); con=connect(); con.execute('delete from sources')
    for src in sources:
        con.execute('insert or replace into sources values (?,?)',(src.get('Source Name') or src.get('name'),json.dumps(src)))
    con.commit(); con.close()
def save_source(src): init_db(); con=connect(); con.execute('insert or replace into sources values (?,?)',(src.get('Source Name') or src.get('name'),json.dumps(src))); con.commit(); con.close()
def save_run(run_id,data): init_db(); con=connect(); con.execute('insert or replace into runs values (?, ?, current_timestamp)',(run_id,json.dumps(data,default=str))); con.commit(); con.close()
def save_listings(listings):
    init_db(); con=connect()
    for l in listings:
        d=l.to_dict() if hasattr(l,'to_dict') else l; con.execute('insert or replace into listings values (?,?)',(d.get('listing_id'),json.dumps(d,default=str)))
    con.commit(); con.close()
def list_runs(limit=25):
    init_db(); con=connect(); rows=con.execute('select data from runs order by created_at desc limit ?',(limit,)).fetchall(); con.close(); return [json.loads(r['data']) for r in rows]
def list_listings(limit=500):
    init_db(); con=connect(); rows=con.execute('select data from listings limit ?',(limit,)).fetchall(); con.close(); return [json.loads(r['data']) for r in rows]
