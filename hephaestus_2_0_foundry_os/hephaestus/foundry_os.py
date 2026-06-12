
import json, hashlib, zipfile
from pathlib import Path

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

class FoundryOS:
    MODULES = [
        "artifact_compiler","artifact_graph","assembly_line","forge_intelligence",
        "code_generator","integration_harness","plugin_smith","autonomous_forge",
        "runtime_core","service_mesh","multi_node_cluster","distributed_state",
        "self_healing_runtime","fabric_layer","operator_console",
        "policy_governance_kernel","autonomous_orchestrator"
    ]
    def __init__(self, state="os_state", release="release"):
        self.state_dir=Path(state); self.release_dir=Path(release)
        self.state_dir.mkdir(parents=True, exist_ok=True); self.release_dir.mkdir(parents=True, exist_ok=True)
        self.kernel={}; self.boot_log=[]; self.registry={}; self.config={}; self.modules={}
        self.control_plane={}; self.scheduler={}; self.governance={}; self.bindings={}
        self.events=[]; self.ledger=[]
    def receipt(self, kind, subject, payload):
        prev=self.ledger[-1]["entry_hash"] if self.ledger else "GENESIS"
        ph=digest(payload); eh=digest({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev})
        self.ledger.append({"kind":kind,"subject":subject,"payload_hash":ph,"prev_hash":prev,"entry_hash":eh})
    def verify_ledger(self):
        prev="GENESIS"
        for i,r in enumerate(self.ledger,1):
            exp=digest({"kind":r["kind"],"subject":r["subject"],"payload_hash":r["payload_hash"],"prev_hash":prev})
            if r["prev_hash"]!=prev or r["entry_hash"]!=exp: return {"ok":False,"seq":i}
            prev=r["entry_hash"]
        return {"ok":True,"entries":len(self.ledger),"head":prev}
    def emit(self, kind, subject, payload):
        e={"id":"event:"+digest({"kind":kind,"subject":subject,"n":len(self.events)})[:16],"kind":kind,"subject":subject,"payload":payload}
        self.events.append(e); self.receipt("event",e["id"],e); return e
    def boot(self):
        self.kernel={"name":"Hephaestus Foundry OS","version":"2.0.0","status":"gold_master","modules":self.MODULES,"kernel_hash":digest(self.MODULES)}
        self.boot_log.append("kernel manifest")
        self.config={"mode":"baseline","governance":True,"scheduler":True,"healing":True,"operator_console":True,"orchestrator":True}
        (self.state_dir/"unified_config.json").write_text(json.dumps(self.config,indent=2))
        self.boot_log.append("unified config")
        self.modules={("module:"+digest(m)[:16]):{"name":m,"version":"2.0.0","status":"loaded"} for m in self.MODULES}
        self.boot_log.append("module loader")
        self.registry={"services":["foundry-api","operator-console","orchestrator","governance-kernel"],"modules":list(self.modules.values())}
        self.boot_log.append("system registry")
        self.control_plane={"runtime":"bound","mesh":"bound","cluster":"bound","state":"bound","healing":"bound","fabric":"bound"}
        self.scheduler={"name":"fabric_scheduler","status":"active","queues":["deployments","repairs","workloads","events"]}
        self.governance={"status":"active","hooks":["command_authorization","deployment_gate","repair_gate","state_mutation_gate"],"risk_scoring":"enabled"}
        self.bindings={"operator_console":{"status":"bound"},"autonomous_orchestrator":{"status":"bound"}}
        self.boot_log += ["control plane","scheduler","governance hooks","operator/orchestrator bindings","complete"]
        self.emit("os.boot.complete","foundry_os",{"steps":len(self.boot_log)})
        return {"status":"booted","steps":self.boot_log}
    def health(self):
        return {"version":"2.0.0","kernel":bool(self.kernel),"modules":len(self.modules),"registry_services":len(self.registry.get("services",[])),"control_plane_bindings":len(self.control_plane),"scheduler":self.scheduler.get("status")=="active","governance":self.governance.get("status")=="active","operator_bound":self.bindings.get("operator_console",{}).get("status")=="bound","orchestrator_bound":self.bindings.get("autonomous_orchestrator",{}).get("status")=="bound","events":len(self.events),"ledger":self.verify_ledger()}
    def dashboard(self):
        return {"version":"2.0.0","health":self.health(),"kernel":self.kernel,"boot_log":self.boot_log,"registry":self.registry,"config":self.config,"modules":list(self.modules.values()),"control_plane":self.control_plane,"scheduler":self.scheduler,"governance":self.governance,"bindings":self.bindings,"events":self.events}
    def gold_manifest(self):
        m={"name":"Hephaestus v2.0 Foundry OS","status":"gold_master","health":self.health(),"kernel_hash":self.kernel.get("kernel_hash"),"release_hash":digest(self.dashboard())}
        p=self.release_dir/"gold_master_manifest.json"; p.write_text(json.dumps(m,indent=2,default=str))
        self.emit("gold_master.manifest.written","release",m); return {"path":str(p),"manifest":m}
    def export(self,out):
        self.gold_manifest()
        out=Path(out)
        with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
            for name,obj in {
                "foundry_os_dashboard.json":self.dashboard(),"health.json":self.health(),"kernel_manifest.json":self.kernel,
                "boot_log.json":self.boot_log,"system_registry.json":self.registry,"unified_config.json":self.config,
                "modules.json":list(self.modules.values()),"control_plane.json":self.control_plane,
                "scheduler.json":self.scheduler,"governance_hooks.json":self.governance,
                "bindings.json":self.bindings,"events.json":self.events,"ledger.json":self.ledger}.items():
                z.writestr(name,json.dumps(obj,indent=2,default=str))
            for p in sorted(self.state_dir.glob("*.json")): z.write(p,arcname="os_state/"+p.name)
            for p in sorted(self.release_dir.glob("*.json")): z.write(p,arcname="release/"+p.name)
        return {"bundle":str(out),"exists":out.exists()}
def seed_demo(td):
    os=FoundryOS(Path(td)/"os_state",Path(td)/"release")
    boot=os.boot(); manifest=os.gold_manifest(); bundle=os.export(Path(td)/"foundry_os_bundle.zip")
    return {"boot":boot,"manifest":manifest,"health":os.health(),"bundle":bundle}
