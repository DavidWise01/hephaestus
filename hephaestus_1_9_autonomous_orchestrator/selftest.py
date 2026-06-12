from hephaestus.orchestrator import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["health"]["workloads"]==2
    assert r["health"]["scheduled_workloads"]==2
    assert r["health"]["resources"]==2
    assert r["health"]["deployments"]>=2
    assert r["health"]["healing_plans"]>=2
    assert r["health"]["events"]==2
    assert r["health"]["automations"]>=2
    assert r["health"]["risk_scores"]>=2
    assert r["health"]["execution_log"]>=4
    assert r["health"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
