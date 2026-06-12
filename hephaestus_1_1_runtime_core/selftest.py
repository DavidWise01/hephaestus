from pathlib import Path
import tempfile
from hephaestus.runtime import seed_demo,RuntimeCore
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["health"]["services"]==2
    assert r["health"]["online"]==2
    assert r["health"]["complete_jobs"]==2
    assert r["health"]["artifacts"]==1
    assert r["health"]["plugin_runs"]==1
    assert r["health"]["ledger"]["ok"] is True
    assert r["health"]["db_integrity"]=="ok"
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
