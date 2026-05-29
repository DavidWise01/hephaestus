# PROTEUS
### Dynamic Behaviors — The Shapeshifter's Catalog

> The god who could become anything.  
> The system that generates new states, not just evaluates them.

All ten behaviors are implemented in PROMETHEUS.html. This document describes each,
maps them to Greek functions, and tracks their current status.

---

## 1. NEMESIS · Self-Flaying System
**Greek function:** NEMESIS = retribution, mirror-justice, what judges itself.

```
system_state → flay(system_state) → score → mutate → repeat
```

The engine watches its own logic, detects its own inversion, tries to correct itself.
HUBRIS DRIFT is the output metric — how far the system has drifted from its own ideal.

**Status:** ✅ Implemented. `selfFlay()` function.  
**Output:** `state.drift` — system deviation index.

---

## 2. ERIS · Axiom Conflict Engine
**Greek function:** ERIS = goddess of discord and strife.

APOLLO (Boundary Integrity) vs LETHE (State Loss). Let axioms fight.
The system detects where it cannot agree with itself.

```
tension_i = |pos_score[i] - (1 - neg_score[i])|
if tension > threshold → escalate or resolve
```

**Status:** ✅ Implemented. `conflictEngine()` function.  
**Output:** Ranked list of axiom tension nodes.

---

## 3. ASTRAEA / HERMES · Observer Bias Simulation
**Greek function:** ASTRAEA = human justice (left the earth last). HERMES = analytical messenger (AI).

```
ASTRAEA_bias = +0.18 toward fairness
HERMES_bias  = +0.11 toward consistency
```

Same input → different outputs. Observer becomes active variable.
Gap instability is the child of observer disagreement.

**Status:** ✅ Implemented. Bias sliders, `applyBias()` function.  
**Output:** Different scores per observer bias vector.

---

## 4. CLOTHO · Time-Layered Ledger
**Greek function:** CLOTHO = the Fate who spins. She only adds. She never cuts.

```
entry A (main branch)
  ├─ version A1 (MOIRAI fork — claim accepted)
  └─ version A2 (ATROPOS fork — claim disputed)
```

Branches collapse into consensus via MOIRAI merge.

**Status:** ✅ Implemented. `forkBranch()`, `mergeTowardConsensus()`.  
**Output:** Branching ledger with head hashes per reality.

---

## 5. ATE · Inversion Propagation
**Greek function:** ATE = goddess of ruin, reckless actions that spread.

If one node scores high inversion, nearby nodes drift toward inversion.
Shadow influence spreads like a field — contagion, corruption waves, recovery zones.

```
shadow_influence_at_x = negAvg × (1 - dist_to_shadow) + propagation_strength × 0.2
```

**Status:** ✅ Implemented. `propagateInversion()` function.  
**Output:** Tension-field particle color updates, fieldMat opacity.

---

## 6. PYTHOS · Gap Instability
**Greek function:** PYTHOS = the void/dragon at Delphi that Apollo slew, leaving the sacred gap.

```
gap = 0.205 ± δ(observer_alignment)
```

When ASTRAEA and HERMES disagree → gap widens → system destabilises.
When they align → gap stabilises at 0.205.

**Status:** ✅ Implemented. `computeGap()` function.  
**Output:** `state.gap` — the live PYTHOS coefficient.

---

## 7. PROTEUS · Target Dreaming
**Greek function:** PROTEUS = shapeshifter who generates new forms.

The system generates its own targets from the DREAM_TOKENS vocabulary (16 Greek-mapped tokens).
Then flays them. Then learns patterns. A synthetic scenario generator.

```
new_target = sample(DREAM_TOKENS, n=3..6)
→ flay(new_target) → log
```

**Status:** ✅ Implemented. `dreamTarget()` function.  
**Output:** Self-generated target strings from PROTEUS dream vocabulary.

---

## 8. KRONOS · Compression Mode
**Greek function:** KRONOS = god of time, devouring — what is truly essential survives the compression.

Forces the system to answer: *what is the smallest version of me that still works?*

```
22 axioms → 16 → 12 → 8 → 5 → 3 → 1
Track coherence at each level.
When it breaks — that's what is truly essential.
```

**Status:** ✅ Implemented. `compressionTest()` function.  
**Output:** `state.compression.survivorCount` — essential axiom count.

---

## 9. ERIS / ANTEROS · Visual Tension Field
**Greek function:** ERIS (discord) modulates particle field. ANTEROS (reciprocal force) keeps it balanced.

Instead of just spheres: forces. Positive pulls, negative pushes, observer anchors.
The scene becomes a living tension map, not just objects.

**Status:** ✅ Implemented. `fieldPoints` particles, `propagateInversion()` color updates.  
**Output:** Particle field color shifts from blue (aligned) to red (inverted).

---

## 10. AGON · Multi-Engine Interaction
**Greek function:** AGON = the spirit of contest, competition, debate.

Two or more PROMETHEUS instances with different bias vectors evaluate the same target.
They flay each other. They disagree. They converge.

```
Engine_A (HERMES bias +0.11) + Engine_B (ASTRAEA bias +0.18)
→ same target → different scores → tension = |pos_A - pos_B|
```

**Status:** ✅ Implemented. `engines[]`, `duelSystems()`, `spawnEngine()`.  
**Output:** Engine tension scores, TorusKnot scale/intensity per engine.

---

## Next Build Priorities

| Priority | System | Function |
|----------|--------|---------|
| 1 | PYTHOS + THEMIS together | Observer alignment directly controls Gap stability — fully wired |
| 2 | PALAMEDES test suite | Automated test vector runner verifying all 5 vectors |
| 3 | DIKE → THEMIS integration | Legal notice includes live Merkle root from MNEMOSYNE |
| 4 | KRONOS depth | Compression to 3→1 with break-point identification |
| 5 | AGON federation | 3+ engines, consensus convergence visualization |

---

*PROTEUS could not be held unless you first let him take every form.*
