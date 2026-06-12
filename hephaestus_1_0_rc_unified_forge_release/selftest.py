from pathlib import Path
import tempfile,runpy
from hephaestus.unified import seed_demo,UnifiedForge
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["build"]["status"]=="released"
    assert r["status"]["modules"]==8
    assert r["status"]["plugins"]==6
    assert r["status"]["ledger"]["ok"] is True
    assert r["status"]["db_integrity"]=="ok"
    assert r["bundle"]["exists"] is True
    f=UnifiedForge(Path(td)/"rc2.db",Path(td)/"gen2")
    f.build("test build")
    runpy.run_path(str(Path(td)/"gen2/selftest_generated.py"),run_name="__main__")
print("SELFTEST PASS")
