from hephaestus.trust_authority import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["verify"]["verified"] is True
    assert r["install"]["decision"]=="allow"
    assert r["execute"]["decision"]=="allow"
    assert r["clean"]["tampered"] is False
    assert r["tampered"]["tampered"] is True
    assert r["status"]["publishers"]==1
    assert r["status"]["artifacts"]==1
    assert r["status"]["signatures"]==1
    assert r["status"]["tamper_events"]==1
    assert r["status"]["provenance_receipts"]==1
    assert r["status"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
