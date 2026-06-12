from hephaestus.marketplace import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["status"]["packages"]==3
    assert r["status"]["versioned_names"]==3
    assert r["status"]["installed"]==0
    assert r["status"]["trust_scores"]==3
    assert r["status"]["compatibility_checks"]==1
    assert r["install"]["status"]=="installed"
    assert r["uninstall"]["status"]=="uninstalled"
    assert len(r["search"]["results"])>=1
    assert r["status"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
