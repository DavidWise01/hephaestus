from hephaestus.healing import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["health"]["nodes"]==3
    assert r["health"]["online_nodes"]==3
    assert r["health"]["services"]==3
    assert r["health"]["running_services"]==3
    assert r["health"]["failures"]==2
    assert r["health"]["repairs"]>=2
    assert r["health"]["healing_events"]>=4
    assert r["health"]["checkpoints"]==1
    assert r["health"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
