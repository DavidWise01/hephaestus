from hephaestus.recovery import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    h=r["health"]
    assert h["repair_plans"]==3
    assert h["doctrine_resyncs"]==1
    assert h["quorum_recoveries"]==1
    assert h["policy_rollbacks"]==1
    assert h["remediations"]==3
    assert h["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
