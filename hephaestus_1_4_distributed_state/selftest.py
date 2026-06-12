from hephaestus.distributed_state import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["health"]["nodes"]==3
    assert r["health"]["online"]==3
    assert r["health"]["keys"]==2
    assert r["health"]["journal_entries"]==3
    assert r["health"]["replications"]==4
    assert r["health"]["conflicts"]==1
    assert r["health"]["locks"]==1
    assert r["consensus"]["committed"] is True
    assert r["health"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
