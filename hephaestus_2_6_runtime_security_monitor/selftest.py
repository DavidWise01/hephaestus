from hephaestus.security_monitor import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["status"]["artifacts"]==2
    assert r["status"]["policies"]==2
    assert r["status"]["activity_events"]==2
    assert r["status"]["access_events"]==3
    assert r["status"]["anomalies"]>=2
    assert r["status"]["permission_drift"]>=1
    assert r["status"]["quarantined"]>=1
    assert r["status"]["kill_events"]==1
    assert r["status"]["incidents"]>=1
    assert r["status"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
