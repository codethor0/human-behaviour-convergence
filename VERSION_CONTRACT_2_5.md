# VERSION CONTRACT: Behavior Index v2.5
**Contract Date:** 2025-01-XX
**Contract Authority:** Code Implementation + Documentation
**Status:** ACTIVE

---

## Guarantees

### GUARANTEES FOR v2.5 CONSUMERS

### G1: Sub-Index Count
- **Guarantee:** System supports exactly 9 sub-indices
- **Evidence:** Code `app/core/behavior_index.py` lines 32-42 declare 9 weight parameters
- **Invariant:** `len(sub_indices) = 9` (when all weights > 0)
- **Test:** `tests/test_new_indices.py::test_behavior_index_with_all_indices`

### G2: Backward Compatibility
- **Guarantee:** v2.0 code (5 sub-indices) continues to work
- **Evidence:** Lines 83-90 show conditional inclusion. If new weights = 0.0, only original 5 indices used
- **Test:** `tests/test_new_indices.py::test_behavior_index_without_new_indices`

### G3: Weight Normalization
- **Guarantee:** Weights are normalized to sum = 1.0 before use
- **Evidence:** Lines 92-119 implement normalization
- **Invariant:** `Σ(normalized_weights) = 1.0` (when total_weight > 0)
- **Test:** `tests/test_behavior_index.py::test_compute_behavior_index_weights_normalization`

### G4: Behavior Index Range
- **Guarantee:** behavior_index ∈ [0.0, 1.0]
- **Evidence:** Line 600: `df["behavior_index"] = behavior_index.clip(0.0, 1.0)`
- **Invariant:** `0.0 ≤ behavior_index ≤ 1.0` (always)
- **Test:** `tests/test_behavior_index.py::test_behavior_index_clipping`

### G5: Sub-Index Range
- **Guarantee:** All sub-indices ∈ [0.0, 1.0]
- **Evidence:** Each sub-index computation includes `.clip(0.0, 1.0)`
- **Invariant:** `∀ i: 0.0 ≤ sub_index[i] ≤ 1.0`
- **Test:** Multiple tests validate sub-index ranges

---

## Invalidated Assumptions

### INVALIDATED ASSUMPTIONS FROM v2.0

### A1: Exactly 5 Sub-Indices
- **v2.0 Assumption:** System has exactly 5 sub-indices
- **v2.5 Reality:** System has 9 sub-indices (4 new ones conditionally included)
- **Breaking Change:** If v2.0 code assumes `len(sub_indices) == 5`, it will fail
- **Mitigation:** Use conditional checks: `if weight > 0: include_sub_index()`

### A2: Weights Sum to 1.0 Without Normalization
- **v2.0 Assumption:** Provided weights are used directly
- **v2.5 Reality:** Weights are normalized if sum ≠ 1.0
- **Breaking Change:** If v2.0 code assumes weights are absolute, interpretation changes
- **Mitigation:** Check normalization warning logs, use normalized weights from `_original_weights`

### A3: Fixed Weight Table
- **v2.0 Assumption:** Weights are fixed percentages (25%, 25%, 20%, 15%, 15%)
- **v2.5 Reality:** Default weights sum to 1.55, normalized to different percentages
- **Breaking Change:** Actual contribution percentages differ from raw weights
- **Mitigation:** Use normalized weights for interpretation

---

## Migration Notes

### MIGRATION NOTES

### For v2.0 → v2.5 Migration

**No Code Changes Required:**
- Backward compatibility maintained
- Existing code continues to work
- New sub-indices only included if weights > 0

**Documentation Updates Required:**
- Update references from "5 sub-indices" to "9 sub-indices"
- Update weight interpretation (raw vs normalized)
- Update version number references

**API Changes:**
- None — API remains backward compatible
- New sub-indices appear in responses when weights > 0

**Data Format Changes:**
- None — existing data formats remain valid

---

## FUTURE VERSION COMPATIBILITY

**v3.0 Compatibility:**
- Unknown — depends on changes
- Version contract must be declared before v3.0 release
- Breaking changes must be documented in CHANGELOG
- Migration guide required for v2.5 → v3.0

---

**Contract Status:** ACTIVE
**Enforcement:** CI check G1 (proposed)
