from hephaestus.foundry_os import seed_demo
import tempfile
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
    r=seed_demo(td)
    assert r["boot"]["status"]=="booted"
    assert r["health"]["kernel"] is True
    assert r["health"]["modules"]==17
    assert r["health"]["registry_services"]==4
    assert r["health"]["control_plane_bindings"]==6
    assert r["health"]["scheduler"] is True
    assert r["health"]["governance"] is True
    assert r["health"]["operator_bound"] is True
    assert r["health"]["orchestrator_bound"] is True
    assert r["health"]["ledger"]["ok"] is True
    assert r["bundle"]["exists"] is True
print("SELFTEST PASS")
