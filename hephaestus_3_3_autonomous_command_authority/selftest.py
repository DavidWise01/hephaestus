from hephaestus.command_authority import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    h=r["health"]
    assert h["hierarchy_defined"] is True
    assert h["objectives"]==1
    assert h["resources"]==3
    assert h["missions"]==1
    assert h["campaigns"]==1
    assert h["orchestrations"]==1
    assert h["simulations"]==1
    assert h["execution_log"]==1
    assert h["audit_entries"]==1
    assert h["ledger"]["ok"] is True
    assert r["execution"]["status"]=="executed"
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
