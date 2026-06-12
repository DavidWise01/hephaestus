from hephaestus.doctrine import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    h=r["health"]
    assert h["doctrines"]==4
    assert h["compiled"]==4
    assert h["conflicts"]==1
    assert h["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
