from hephaestus.constitution import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td); h=r["health"]
    assert h["constitutional_registry"]==6
    assert h["delegated_authorities"]==5
    assert h["constitutional_audits"]==3
    assert h["compliant_actions"]==1          # only the first action is fully compliant
    assert h["ratified_amendments"]==1
    assert h["appeals"]==1
    assert h["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
