from hephaestus.console import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["health"]["nodes"]==2
    assert r["health"]["healthy_nodes"]==2
    assert r["health"]["services"]==3
    assert r["health"]["healthy_services"]==3
    assert r["health"]["artifacts"]==1
    assert r["health"]["deployments"]==1
    assert r["health"]["state_objects"]==1
    assert r["health"]["commands"]>=5
    assert r["health"]["events"]>=10
    assert r["health"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
