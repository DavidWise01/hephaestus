from hephaestus.sovereign import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    h=r["health"]
    assert h["root_authorities"]==5
    assert h["bound_subsystems"]==5
    assert h["sovereign_decisions"]==2
    assert h["enacted"]==1
    assert h["rejected"]==1
    assert h["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
