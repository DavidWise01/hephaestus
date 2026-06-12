from hephaestus.pipeline import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["status"]["artifacts"]==2
    assert r["status"]["pipeline_runs"]==2
    assert r["status"]["policy_gates"]>=4
    assert r["status"]["trust_checks"]==2
    assert r["status"]["install_records"]==2
    assert r["status"]["execution_approvals"]==2
    assert r["status"]["risk_scores"]==2
    assert r["status"]["promoted"]==1
    assert r["status"]["quarantined"]==1
    assert r["good_run"]["final"]["status"]=="promoted"
    assert r["bad_run"]["final"]["status"]=="quarantined"
    assert r["status"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
