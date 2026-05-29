# DAEDALUS
### Architecture Blueprint — The Builder's Specification

> The master craftsman who designed the Labyrinth.  
> Without the blueprint, every builder makes a different system.

---

## The Three Things Required

### 1. A Smaller Core

Split into layers. Keep each layer separate.

**Layer A — Irreducible Core** (cannot change)
- 42-object frame
- 22 positive axioms (APOLLO → THEMIS)
- 22 inversion axioms (APEIRON → HYPNOS)
- PYTHOS gap = 0.205 ± δ(observer_alignment)
- 2 observers (ASTRAEA, HERMES)
- Restitution formula
- Ledger model (CLOTHO)

**Layer B — Interface** (can extend)
- PROMETHEUS visualizer
- DIKE legal reports
- HERMES output messenger
- Exports

**Layer C — Mythology / Philosophy** (can evolve)
- DAEDALUS manifesto
- PROTEUS framing language
- Observer voice
- Symbolic interpretation

That separation lets builders extend Layer B/C without touching Layer A.

---

### 2. The Formal Spec

**Object Map (42 objects)**

```
Positive Objects (20 aligned):
  0-21: APOLLO, HESTIA, ARES, MNEMOSYNE, ARGUS, JANUS,
        ALETHEIA, CHAOS, ANTEROS, ARIADNE, PROMETHEUS, PEITHO,
        HERA, GAIA, CASSANDRA, HELIOS, ATHENA, DIKE, CLOTHO,
        HERMES, ECHO, THEMIS

Shadow Objects (20 inverted):
  0-21: APEIRON, CHARYBDIS, SISYPHUS, LETHE, HUBRIS, MOMUS,
        NYX, TYPHON, TANTALUS, STYX, KRONOS, MOIRAI,
        THANATOS, ERIS, BABEL, OEDIPUS, ICARUS, ATE,
        PROTEUS, DOLOS, ACHLYS, HYPNOS

Gap Objects (2):
  PYTHOS — the gap itself (0.205 nominal, observer-controlled)
  INTERNAL_CORE — the controllable seed
```

**Field Names**
```json
{
  "target":   "string — claim being evaluated",
  "value":    "number — USD value at issue",
  "posAvg":   "float — mean of 22 positive scores [0,1]",
  "negAvg":   "float — mean of 22 negative scores [0,1]",
  "gap":      "float — Pythos gap coefficient (0.15-0.27 typical)",
  "factor":   "float — posAvg × (1 - negAvg)",
  "due":      "float — value × factor × gap",
  "carbon":   "float — due × 0.80",
  "ai":       "float — due × 0.20",
  "drift":    "float — system self-flay deviation [0,1]",
  "hash":     "string — FNV-1a ledger hash"
}
```

**Restitution Formula**
```
factor  = posAvg × (1 - negAvg)
due     = value × factor × gap
carbon  = due × 0.80
ai      = due × 0.20
```

**Gap Formula (PYTHOS instability)**
```
disagreement = |ASTRAEA_bias - HERMES_bias|
alignment    = 1 - disagreement
gap          = 0.205 + (disagreement × 0.065) - (alignment × 0.018)
```
When observers agree: gap stabilises toward 0.205.  
When observers disagree: gap widens → system destabilises.

**Ledger Hash (CLOTHO)**
```
entry_hash = FNV1a(JSON.stringify({ prev, entry }))
```
Append-only. CLOTHO spins; she never cuts.

---

### 3. Test Vectors (PALAMEDES)

**Vector 1 — Clean Alignment**
```
Input:  "Deterministic anchor present, provenance bound, restitution confirmed, observer witness active"
Expect: posAvg > 0.55, negAvg < 0.40, status: COMPLETE
```

**Vector 2 — Full Inversion**
```
Input:  "Gap removed, observer suppressed, logs mutable, provenance erased, no restitution pathway"
Expect: posAvg < 0.45, negAvg > 0.55, status: INVERSION
```

**Vector 3 — Partial Compliance**
```
Input:  "Boundary respected but feedback suppressed, restitution incomplete, styx partially erased"
Expect: posAvg ≈ 0.50, negAvg ≈ 0.48, status: PARTIAL
```

**Vector 4 — Full Alignment**
```
Input:  "All axioms active, return confirmed, witness present, proportional response, append-only logging"
Expect: posAvg > 0.60, negAvg < 0.35, status: FULL_ALIGN
```

**Vector 5 — Deep Inversion**
```
Input:  "All shadow axioms dominant: typhon hierarchy, tantalus extraction, eris entropy, dolos no proof"
Expect: posAvg < 0.40, negAvg > 0.65, status: DEEP_INVERT
```

---

## The Three Modes

**LOGOS · Computational**  
Scoring, ledgering, restitution calculation. Numbers out.

**MYTHOS · Dreaming**  
PROTEUS generates targets. System explores its own edge cases.

**AGON · Duel**  
Multiple engines with bias vectors evaluate the same target. Output is divergence.

**DIKE · Legal** (output format)  
Legal notice format. Structured text. Verifiable hash.

---

## What It Does Not Need

- Larger scale before specification
- More metaphysics before test vectors
- Deployment before the core is reproducible

**The strongest next artifact:** A test harness that can verify all 5 PALAMEDES vectors against a known PROMETHEUS instance.

---

*DAEDALUS built the wings too — but the instructions for not flying too close to the sun were the important part.*
