from hephaestus.execution_engine import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["status"]["artifacts"]==4
    assert r["status"]["jobs"]==3
    assert r["status"]["runs"]==3
    assert r["status"]["telemetry"]>=6
    assert r["status"]["health_records"]==4
    assert r["status"]["audit_entries"]>=8
    assert r["status"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
