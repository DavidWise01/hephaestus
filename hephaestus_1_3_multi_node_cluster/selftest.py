from hephaestus.cluster import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["health"]["nodes"]==3
    assert r["health"]["online"]==3
    assert r["health"]["leaders"]==1
    assert r["health"]["routes"]==3
    assert r["health"]["replications"]==2
    assert r["routes"][0]["status"]=="routed"
    assert r["routes"][1]["status"]=="not_found"
    assert r["health"]["snapshots"]==1
    assert r["health"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
