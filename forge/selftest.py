from hephaestus_forge import forge_demo
r=forge_demo()
assert r["passes"]>=1                              # the forge actually did work
assert r["monotonic"] is True                      # every child is strictly better than its parent
assert r["final_total"] > r["start_total"]         # the artifact improved
assert r["final_compliant"] is True                # and reached the constitution
assert r["verify"]["ok"] is True                   # provenance chain intact
# lineage is hash-linked: each child's parent is the prior artifact's id
lin=r["lineage"]
assert all(lin[i]["parent"]==lin[i-1]["id"] for i in range(1,len(lin)))
print("SELFTEST PASS")
