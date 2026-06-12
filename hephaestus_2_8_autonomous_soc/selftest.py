from hephaestus.autonomous_soc import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    h=r["health"]
    assert h["events"]==3
    assert h["cases"]==1
    assert h["open_cases"]==0
    assert h["critical_cases"]==1
    assert h["contained_cases"]==1
    assert h["recovered_cases"]==1
    assert h["responses"]==1
    assert h["recoveries"]==1
    assert h["evidence_bundles"]==1
    assert h["memory_records"]==1
    assert h["forecasts"]==1
    assert h["simulations"]==1
    assert h["learning_events"]==1
    assert h["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
