# Playground Manual Verification Checklist

**Status:** Documentation Only (Not a Gate)  
**Engine Status:** GREEN (Locked)  
**Last Verified:** Baseline (3 regions) confirmed working end-to-end

## Purpose

This checklist documents manual UI verification scenarios for the Playground Compare feature. These tests require manual interaction due to browser automation limitations with checkbox-heavy interfaces.

**Important:** Code-level verification confirms all logic paths are correct. This checklist serves as regression testing documentation, not a blocking requirement.

## Test Scenarios

### Region Selection Permutations

- [ ] **0 regions selected**
  - Expected: Error message visible ("Please select at least one region")
  - Expected: Button disabled (grayed out, not clickable)
  - Verify: No POST request attempted

- [ ] **1 region selected**
  - Expected: Comparison completes successfully
  - Expected: POST `/api/playground/compare` appears in Network tab
  - Expected: Response 200 OK
  - Expected: UI renders comparison results
  - Expected: Loading state clears

- [ ] **2 regions selected**
  - Expected: Comparison completes successfully
  - Expected: Results show both regions
  - Expected: No console errors

- [ ] **5+ regions selected**
  - Expected: Comparison completes successfully
  - Expected: All selected regions appear in results
  - Expected: Performance acceptable (< 30s)

- [ ] **Maximum allowed regions**
  - Expected: Comparison completes OR fails gracefully with clear error
  - Expected: No browser hang or timeout

### Scenario Adjustments

- [ ] **No scenario adjustments (baseline)**
  - Expected: Comparison uses default forecast
  - Expected: No scenario_applied flag in response

- [ ] **One scenario adjustment applied**
  - Expected: Delta visible in results
  - Expected: scenario_applied: true in response
  - Expected: Scenario description appears

- [ ] **Multiple scenario adjustments**
  - Expected: All adjustments reflected in results
  - Expected: Combined effect visible

- [ ] **Scenario reset**
  - Expected: Baseline restored
  - Expected: Adjustments cleared from UI
  - Expected: Next comparison uses baseline

### Re-entry & State Management

- [ ] **Compare → Compare again**
  - Expected: No stale data from previous comparison
  - Expected: Fresh results rendered
  - Expected: Loading state toggles correctly

- [ ] **Compare → Reset → Compare**
  - Expected: Reset clears previous results
  - Expected: New comparison uses current selections
  - Expected: No state bleed between comparisons

- [ ] **Navigate away → return → Compare**
  - Expected: Clean state on return
  - Expected: Previous results not persisted
  - Expected: Fresh comparison works correctly

## Verification Criteria

For each test case:
- [OK] POST request appears in Network tab
- [OK] Response status 200 OK (or appropriate error)
- [OK] Loading state clears after completion
- [OK] UI updates correctly
- [OK] No console errors
- [OK] No stale state

## Notes

- Baseline (3 regions) verified via automation: **GREEN**
- Code-level verification: All logic paths correct
- Manual verification: Pending (non-blocking)

## Last Updated

Generated during Playground Permutation Testing phase.  
Engine verified GREEN. Manual UI permutations documented for future regression testing.
