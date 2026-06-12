from hephaestus.autonomy import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    h=r["health"]
    assert h["steps"]==4
    assert h["executed"]==3
    assert h["blocked"]==1
    assert h["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
