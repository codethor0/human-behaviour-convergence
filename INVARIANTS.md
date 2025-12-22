# INVARIANTS
**Status:** AUTHORITATIVE
**Date:** 2025-01-XX
**Authority:** Governance Rules

---

## INVARIANT DEFINITIONS

### I1: Normalized Weight Sum

**Statement:** After normalization, all weights sum to exactly 1.0

**Formal:** `Σ(normalized_weight[i]) = 1.0` (when total_weight > 0)

**Proof:** By construction in `app/core/behavior_index.py` lines 99-119

**Test:** `tests/test_behavior_index.py::test_compute_behavior_index_weights_normalization`

**Violation Detection:** Test failure if normalization doesn't produce sum = 1.0

---

### I2: Relative Proportions Preserved

**Statement:** Normalization preserves relative proportions between weights

**Formal:** `∀ i, j: normalized_weight[i] / normalized_weight[j] = raw_weight[i] / raw_weight[j]`

**Proof:** Mathematical (division by same constant)

**Test:** None (mathematical proof sufficient)

**Violation Detection:** Would require test comparing ratios

---

### I3: Zero Weight Exclusion

**Statement:** Sub-indices with zero weight are excluded from computation

**Formal:** `If raw_weight[i] = 0, then normalized_weight[i] = 0 AND sub_index[i] excluded`

**Proof:** Code lines 83-90, 104-118, 584-597 show conditional inclusion

**Test:** `tests/test_new_indices.py::test_behavior_index_without_new_indices`

**Violation Detection:** Test failure if zero-weight sub-index included

---

### I4: Sub-Index Count Consistency

**Statement:** Number of sub-indices in code equals documented count

**Formal:** `count(code_sub_indices) = count(documented_sub_indices) = 9`

**Proof:** Manual verification (code has 9 weight parameters, docs state 9)

**Test:** CI check G2 (proposed)

**Violation Detection:** CI failure if counts mismatch

---

### I5: Behavior Index Range

**Statement:** behavior_index is always in range [0.0, 1.0]

**Formal:** `0.0 ≤ behavior_index ≤ 1.0` (always)

**Proof:** Code line 600: `df["behavior_index"] = behavior_index.clip(0.0, 1.0)`

**Test:** `tests/test_behavior_index.py::test_behavior_index_clipping`

**Violation Detection:** Test failure if value outside range

---

### I6: Sub-Index Range

**Statement:** All sub-indices are in range [0.0, 1.0]

**Formal:** `∀ i: 0.0 ≤ sub_index[i] ≤ 1.0`

**Proof:** Each sub-index computation includes `.clip(0.0, 1.0)` (e.g., lines 258, 303, 313)

**Test:** Multiple tests validate sub-index ranges

**Violation Detection:** Test failure if sub-index outside range

---

### I7: No Sub-Index Without Weight

**Statement:** Every sub-index used in computation has a corresponding weight > 0

**Formal:** `∀ sub_index[i] used: ∃ weight[i] > 0`

**Proof:** Conditional checks in lines 584-597

**Test:** None (structural guarantee)

**Violation Detection:** Would require static analysis

---

### I8: No Weight Without Sub-Index

**Statement:** Every weight parameter has a corresponding sub-index computation

**Formal:** `∀ weight[i]: ∃ sub_index[i] computation`

**Proof:** One-to-one mapping enforced by code structure

**Test:** None (structural guarantee)

**Violation Detection:** Would require static analysis

---

### I9: No Division by Zero

**Statement:** Normalization never divides by zero

**Formal:** `total_weight > 0` before division

**Proof:** Code line 93: `if total_weight > 0:` guard

**Test:** None (edge case)

**Violation Detection:** Would require test with total_weight = 0

---

### I10: No NaN from Normalization

**Statement:** Normalization never produces NaN (when inputs are valid)

**Formal:** `If ∀ i: isfinite(raw_weight[i]), then ∀ i: isfinite(normalized_weight[i])`

**Proof:** Conditional (requires input validation)

**Test:** None (requires input validation)

**Violation Detection:** Would require test with NaN inputs

---

## INVARIANT ENFORCEMENT

**Tested Invariants:** I1, I3, I5, I6
**CI-Enforced Invariants:** I4 (proposed)
**Structurally Guaranteed:** I7, I8
**Edge Cases:** I9, I10 (require additional tests)

**Status:** Partial enforcement — critical invariants tested, consistency invariants require CI
