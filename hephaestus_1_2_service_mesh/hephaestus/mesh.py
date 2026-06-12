
import json,hashlib,sqlite3,zipfile
from pathlib import Path
def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,default=str).encode()).hexdigest()
class Mesh:
    def __init__(self,db="mesh.db"):
        self.conn=sqlite3.connect(Path(db)); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""CREATE TABLE IF NOT EXISTS services(id TEXT PRIMARY KEY,name TEXT,kind TEXT,endpoint TEXT,status TEXT,health TEXT);
        CREATE TABLE IF NOT EXISTS contracts(id TEXT PRIMARY KEY,service TEXT,route TEXT,method TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS deps(id TEXT PRIMARY KEY,src TEXT,dst TEXT,relation TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS routes(id TEXT PRIMARY KEY,path TEXT,target TEXT,policy TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS failover(id TEXT PRIMARY KEY,primary_service TEXT,fallback_service TEXT,status TEXT);
        CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,path TEXT,target TEXT,status TEXT);
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
    def service(self,name,kind,endpoint):
        sid="service:"+digest({"n":name,"k":kind,"e":endpoint})[:16]
        self.conn.execute("INSERT OR REPLACE INTO services VALUES(?,?,?,?,?,?)",(sid,name,kind,endpoint,"registered","unknown"))
        self.receipt("service",sid,{"name":name}); return {"service":sid}
    def heartbeat(self,sid,health="ok"):
        self.conn.execute("UPDATE services SET status=?,health=? WHERE id=?",("online" if health=="ok" else "degraded",health,sid))
        self.receipt("heartbeat",sid,{"health":health})
    def contract(self,sid,route,method="GET"):
        cid="contract:"+digest({"s":sid,"r":route,"m":method})[:16]
        self.conn.execute("INSERT OR REPLACE INTO contracts VALUES(?,?,?,?,?)",(cid,sid,route,method,"active"))
        self.receipt("contract",cid,{"route":route}); return {"contract":cid}
    def dep(self,src,dst,relation="calls"):
        did="dep:"+digest({"src":src,"dst":dst,"rel":relation})[:16]
        self.conn.execute("INSERT OR REPLACE INTO deps VALUES(?,?,?,?,?)",(did,src,dst,relation,"active"))
        self.receipt("dep",did,{"src":src,"dst":dst}); return {"dep":did}
    def route(self,path,target,policy="primary"):
        rid="route:"+digest({"p":path,"t":target})[:16]
        self.conn.execute("INSERT OR REPLACE INTO routes VALUES(?,?,?,?,?)",(rid,path,target,policy,"active"))
        self.receipt("route",rid,{"path":path}); return {"route":rid}
    def failover(self,primary,fallback):
        fid="failover:"+digest({"p":primary,"f":fallback})[:16]
        self.conn.execute("INSERT OR REPLACE INTO failover VALUES(?,?,?,?)",(fid,primary,fallback,"active"))
        self.receipt("failover",fid,{"primary":primary}); return {"failover":fid}
    def resolve(self,path):
        r=self.conn.execute("SELECT * FROM routes WHERE path=? AND status='active'",(path,)).fetchone()
        if not r: return None
        target=r["target"]; svc=self.conn.execute("SELECT * FROM services WHERE id=?",(target,)).fetchone()
        if svc and svc["health"]!="ok":
            f=self.conn.execute("SELECT * FROM failover WHERE primary_service=? AND status='active'",(target,)).fetchone()
            if f: target=f["fallback_service"]
        return target
    def request(self,path):
        target=self.resolve(path); status="routed" if target else "not_found"
        rid="request:"+digest({"p":path,"t":target})[:16]
        self.conn.execute("INSERT OR REPLACE INTO requests VALUES(?,?,?,?)",(rid,path,target or "",status))
        self.receipt("request",rid,{"path":path,"status":status}); self.conn.commit()
        return {"request":rid,"path":path,"target":target,"status":status}
    def health(self):
        return {"services":self.conn.execute("SELECT COUNT(*) n FROM services").fetchone()["n"],"online":self.conn.execute("SELECT COUNT(*) n FROM services WHERE status='online'").fetchone()["n"],"degraded":self.conn.execute("SELECT COUNT(*) n FROM services WHERE status='degraded'").fetchone()["n"],"routes":self.conn.execute("SELECT COUNT(*) n FROM routes").fetchone()["n"],"contracts":self.conn.execute("SELECT COUNT(*) n FROM contracts").fetchone()["n"],"dependencies":self.conn.execute("SELECT COUNT(*) n FROM deps").fetchone()["n"],"failovers":self.conn.execute("SELECT COUNT(*) n FROM failover").fetchone()["n"],"ledger":self.verify_ledger(),"db_integrity":self.conn.execute("PRAGMA integrity_check").fetchone()[0]}
    def dashboard(self):
        return {"version":"1.2.0","health":self.health(),"services":[dict(r) for r in self.conn.execute("SELECT * FROM services")],"contracts":[dict(r) for r in self.conn.execute("SELECT * FROM contracts")],"dependencies":[dict(r) for r in self.conn.execute("SELECT * FROM deps")],"routes":[dict(r) for r in self.conn.execute("SELECT * FROM routes")],"failover":[dict(r) for r in self.conn.execute("SELECT * FROM failover")],"requests":[dict(r) for r in self.conn.execute("SELECT * FROM requests")]}
    def export(self,out):
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            z.writestr("mesh_dashboard.json",json.dumps(self.dashboard(),indent=2))
            for t in ["services","contracts","deps","routes","failover","requests","ledger"]:
                z.writestr(f"{t}.json",json.dumps([dict(r) for r in self.conn.execute(f"SELECT * FROM {t} ORDER BY 1")],indent=2))
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    m=Mesh(Path(td)/"mesh.db")
    db=m.service("database","storage","sqlite://app.db"); api=m.service("api","service","http://127.0.0.1:8100"); dash=m.service("dashboard","ui","/dashboard"); rep=m.service("report","report","/api/report"); fb=m.service("api-fallback","service","http://127.0.0.1:8101")
    for s in [db,api,dash,rep,fb]: m.heartbeat(s["service"],"ok")
    m.heartbeat(api["service"],"degraded")
    m.contract(api["service"],"/api/status"); m.contract(rep["service"],"/api/report"); m.contract(dash["service"],"/dashboard")
    m.dep(dash["service"],api["service"]); m.dep(api["service"],db["service"]); m.dep(rep["service"],db["service"])
    m.route("/api/status",api["service"]); m.route("/api/report",rep["service"]); m.route("/dashboard",dash["service"])
    m.failover(api["service"],fb["service"])
    req=[m.request("/api/status"),m.request("/dashboard"),m.request("/missing")]
    return {"requests":req,"health":m.health(),"bundle":m.export(Path(td)/"mesh_bundle.zip")}
