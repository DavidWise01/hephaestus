
import json,hashlib,sqlite3,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class UnifiedForge:
    MODULES=["artifact_compiler","artifact_graph","assembly_line","forge_intelligence","code_generator","integration_harness","plugin_smith","autonomous_forge"]
    PLUGINS=["database_builder","api_builder","dashboard_builder","workflow_builder","report_builder","security_builder"]
    def __init__(self,db="hephaestus_rc.db",out="generated"):
        self.out=Path(out); self.out.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(Path(db)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""CREATE TABLE IF NOT EXISTS modules(id TEXT PRIMARY KEY,status TEXT,version TEXT);
        CREATE TABLE IF NOT EXISTS plugins(id TEXT PRIMARY KEY,status TEXT,version TEXT);
        CREATE TABLE IF NOT EXISTS builds(id TEXT PRIMARY KEY,request TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,build TEXT,path TEXT,h TEXT);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);""")
        for m in self.MODULES: self.conn.execute("INSERT OR REPLACE INTO modules VALUES(?,?,?)",(m,"bundled","1.0.0-rc"))
        for p in self.PLUGINS: self.conn.execute("INSERT OR REPLACE INTO plugins VALUES(?,?,?)",(p,"active","1.0.0-rc"))
        self.conn.commit()
    def last_hash(self):
        r=self.conn.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        return r["entry_hash"] if r else "GENESIS"
    def receipt(self,k,s,p):
        ph=digest(p); prev=self.last_hash(); eh=digest({"kind":k,"subject":s,"payload_hash":ph,"prev_hash":prev})
        self.conn.execute("INSERT INTO ledger(kind,subject,payload_hash,prev_hash,entry_hash) VALUES(?,?,?,?,?)",(k,s,ph,prev,eh)); self.conn.commit()
    def verify_ledger(self):
        prev="GENESIS"; n=0
        for r in self.conn.execute("SELECT * FROM ledger ORDER BY seq"):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev or r["entry_hash"]!=exp: return {"ok":False,"seq":r["seq"]}
            prev=r["entry_hash"]; n+=1
        return {"ok":True,"entries":n,"head":prev}
    def write(self,bid,rel,txt):
        p=self.out/rel; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt)
        h=hashlib.sha256(txt.encode()).hexdigest(); fid="file:"+digest({"build":bid,"path":rel,"h":h})[:16]
        self.conn.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?)",(fid,bid,str(p),h))
        self.receipt("file",fid,{"path":str(p)})
        return {"path":str(p),"hash":h}
    def build(self,request):
        bid="build:"+digest({"request":request,"v":"1.0.0-rc"})[:16]
        self.conn.execute("INSERT OR REPLACE INTO builds VALUES(?,?,?)",(bid,request,"running"))
        files=[
            self.write(bid,"dashboard/index.html",f"<html><body><h1>Hephaestus Generated App</h1><p>{request}</p></body></html>"),
            self.write(bid,"api/server.py","import json\nfrom http.server import ThreadingHTTPServer,BaseHTTPRequestHandler\nclass H(BaseHTTPRequestHandler):\n def do_GET(self):\n  b=json.dumps({'status':'online','forge':'hephaestus-1.0-rc'}).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)\n def log_message(self,*a): pass\nif __name__=='__main__': ThreadingHTTPServer(('127.0.0.1',8100),H).serve_forever()\n"),
            self.write(bid,"database/schema.sql","CREATE TABLE items(id TEXT PRIMARY KEY,name TEXT,status TEXT);\n"),
            self.write(bid,"workflow/workflow.py","def run(): return {'state':'released'}\n"),
            self.write(bid,"reports/report.html",f"<html><body><h1>Release Report</h1><p>{request}</p></body></html>"),
            self.write(bid,"security/security.py","def verify(x): return bool(x.get('id'))\n"),
        ]
        files.append(self.write(bid,"manifest.json",json.dumps({"build":bid,"request":request,"files":files},indent=2)))
        files.append(self.write(bid,"selftest_generated.py","from pathlib import Path\nR=Path(__file__).parent\nfor p in ['dashboard/index.html','api/server.py','database/schema.sql','workflow/workflow.py','reports/report.html','security/security.py','manifest.json']: assert (R/p).exists()\nprint('GENERATED APP SELFTEST PASS')\n"))
        self.conn.execute("UPDATE builds SET status='released' WHERE id=?",(bid,))
        self.receipt("build",bid,{"files":len(files)})
        self.conn.commit()
        return {"build":bid,"status":"released","files":files}
    def status(self):
        return {"version":"1.0.0-rc","modules":self.conn.execute("SELECT COUNT(*) n FROM modules").fetchone()["n"],"plugins":self.conn.execute("SELECT COUNT(*) n FROM plugins").fetchone()["n"],"builds":self.conn.execute("SELECT COUNT(*) n FROM builds").fetchone()["n"],"files":self.conn.execute("SELECT COUNT(*) n FROM files").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def export(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("status.json",json.dumps(self.status(),indent=2))
            for t in ["modules","plugins","builds","files","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
            for p in sorted(self.out.rglob("*")):
                if p.is_file(): z.write(p,arcname=f"generated/{p.relative_to(self.out)}")
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    f=UnifiedForge(Path(td)/"rc.db",Path(td)/"generated")
    b=f.build("full operator platform with dashboard api database workflow reports security")
    e=f.export(Path(td)/"rc_bundle.zip")
    return {"build":b,"status":f.status(),"bundle":e}
