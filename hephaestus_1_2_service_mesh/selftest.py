from hephaestus.mesh import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["health"]["services"]==5
    assert r["health"]["online"]==4
    assert r["health"]["degraded"]==1
    assert r["health"]["routes"]==3
    assert r["health"]["contracts"]==3
    assert r["health"]["dependencies"]==3
    assert r["health"]["failovers"]==1
    assert r["requests"][0]["status"]=="routed"
    assert r["requests"][2]["status"]=="not_found"
    assert r["health"]["ledger"]["ok"] is True
    assert r["health"]["db_integrity"]=="ok"
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
