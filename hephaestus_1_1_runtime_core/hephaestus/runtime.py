
import json,hashlib,sqlite3,zipfile,time
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class RuntimeCore:
    def __init__(self,db="runtime.db",state="runtime_state",artifacts="artifacts"):
        self.state=Path(state); self.state.mkdir(parents=True,exist_ok=True)
        self.artifacts=Path(artifacts); self.artifacts.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(Path(db)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""CREATE TABLE IF NOT EXISTS services(id TEXT PRIMARY KEY,name TEXT,kind TEXT,status TEXT,health TEXT);
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,name TEXT,kind TEXT,status TEXT,service TEXT,payload TEXT);
        CREATE TABLE IF NOT EXISTS artifacts(id TEXT PRIMARY KEY,name TEXT,kind TEXT,status TEXT,path TEXT,h TEXT);
        CREATE TABLE IF NOT EXISTS plugin_runs(id TEXT PRIMARY KEY,plugin TEXT,status TEXT,input TEXT,output TEXT);
        CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT,h TEXT);
        CREATE TABLE IF NOT EXISTS metrics(id INTEGER PRIMARY KEY,kind TEXT,name TEXT,value REAL);
        CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,subject TEXT,payload_hash TEXT,prev_hash TEXT,entry_hash TEXT);""")
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
    def service(self,name,kind):
        sid="service:"+digest({"name":name,"kind":kind})[:16]
        self.conn.execute("INSERT OR REPLACE INTO services VALUES(?,?,?,?,?)",(sid,name,kind,"registered","unknown"))
        self.receipt("service",sid,{"name":name}); return {"service":sid}
    def heartbeat(self,sid,health="ok"):
        self.conn.execute("UPDATE services SET status='online',health=? WHERE id=?",(health,sid))
        self.conn.execute("INSERT INTO metrics(kind,name,value) VALUES(?,?,?)",("health",sid,1 if health=="ok" else 0))
        self.receipt("heartbeat",sid,{"health":health}); self.conn.commit()
    def job(self,name,kind,service,payload=None):
        jid="job:"+digest({"name":name,"kind":kind})[:16]
        self.conn.execute("INSERT OR REPLACE INTO jobs VALUES(?,?,?,?,?,?)",(jid,name,kind,"queued",service,json.dumps(payload or {})))
        self.receipt("job",jid,{"service":service}); return {"job":jid}
    def run_jobs(self):
        out=[]
        for j in list(self.conn.execute("SELECT * FROM jobs WHERE status='queued'")):
            self.conn.execute("UPDATE jobs SET status='complete' WHERE id=?",(j["id"],))
            self.conn.execute("INSERT INTO metrics(kind,name,value) VALUES(?,?,?)",("job_complete",j["kind"],1))
            self.receipt("job_complete",j["id"],{"kind":j["kind"]}); out.append({"job":j["id"],"status":"complete"})
        self.conn.commit(); return out
    def set_state(self,key,value):
        h=digest(value); self.conn.execute("INSERT OR REPLACE INTO state VALUES(?,?,?)",(key,json.dumps(value),h))
        (self.state/(key.replace(":","_")+".json")).write_text(json.dumps({"key":key,"value":value,"hash":h},indent=2))
        self.receipt("state",key,{"hash":h}); return {"key":key,"hash":h}
    def artifact(self,name,kind,content):
        h=hashlib.sha256(content.encode()).hexdigest(); aid="artifact:"+digest({"name":name,"h":h})[:16]
        path=self.artifacts/(aid.replace(":","_")+".txt"); path.write_text(content)
        self.conn.execute("INSERT OR REPLACE INTO artifacts VALUES(?,?,?,?,?,?)",(aid,name,kind,"active",str(path),h))
        self.receipt("artifact",aid,{"hash":h}); return {"artifact":aid}
    def plugin(self,name,input_payload):
        rid="pluginrun:"+digest({"name":name,"input":input_payload})[:16]
        output={"plugin":name,"status":"complete","input_hash":digest(input_payload)}
        self.conn.execute("INSERT OR REPLACE INTO plugin_runs VALUES(?,?,?,?,?)",(rid,name,"complete",json.dumps(input_payload),json.dumps(output)))
        self.conn.execute("INSERT INTO metrics(kind,name,value) VALUES(?,?,?)",("plugin_run",name,1))
        self.receipt("plugin",rid,output); return {"plugin_run":rid}
    def health(self):
        return {"services":self.conn.execute("SELECT COUNT(*) n FROM services").fetchone()["n"],"online":self.conn.execute("SELECT COUNT(*) n FROM services WHERE status='online'").fetchone()["n"],"complete_jobs":self.conn.execute("SELECT COUNT(*) n FROM jobs WHERE status='complete'").fetchone()["n"],"artifacts":self.conn.execute("SELECT COUNT(*) n FROM artifacts").fetchone()["n"],"plugin_runs":self.conn.execute("SELECT COUNT(*) n FROM plugin_runs").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def dashboard(self):
        return {"version":"1.1.0","health":self.health(),"services":[dict(r) for r in self.conn.execute("SELECT * FROM services")],"jobs":[dict(r) for r in self.conn.execute("SELECT * FROM jobs")],"artifacts":[dict(r) for r in self.conn.execute("SELECT * FROM artifacts")],"plugin_runs":[dict(r) for r in self.conn.execute("SELECT * FROM plugin_runs")],"metrics":[dict(r) for r in self.conn.execute("SELECT * FROM metrics")]}
    def export(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("runtime_dashboard.json",json.dumps(self.dashboard(),indent=2))
            for t in ["services","jobs","artifacts","plugin_runs","state","metrics","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
            for p in sorted(self.state.glob("*.json")): z.write(p,arcname="runtime_state/"+p.name)
            for p in sorted(self.artifacts.glob("*")):
                if p.is_file(): z.write(p,arcname="artifacts/"+p.name)
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    r=RuntimeCore(Path(td)/"runtime.db",Path(td)/"state",Path(td)/"artifacts")
    s1=r.service("generated-api","api"); s2=r.service("plugin-worker","worker")
    r.heartbeat(s1["service"]); r.heartbeat(s2["service"])
    r.set_state("runtime:mode",{"mode":"active","version":"1.1.0"})
    r.job("health-check","monitor",s1["service"]); r.job("plugin-scan","plugin",s2["service"])
    jobs=r.run_jobs()
    a=r.artifact("demo-artifact","generated","hello runtime")
    p=r.plugin("dashboard_builder",{"request":"build runtime dashboard"})
    b=r.export(Path(td)/"runtime_bundle.zip")
    return {"services":[s1,s2],"jobs":jobs,"artifact":a,"plugin":p,"health":r.health(),"bundle":b}
