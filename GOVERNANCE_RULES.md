# GOVERNANCE RULES
**Status:** PERMANENT / NON-REVERSIBLE
**Authority:** Controller
**Effective Date:** 2025-01-XX
**Master Prompt:** v4 (Maximum Strength / Future-Proof)

---

## ACCEPTANCE DECISION

**Decision:** ACCEPT (WITH GOVERNANCE LOCKS)
**Date:** 2025-01-XX
**Verification Level:** Master Prompt v3 → v4

**Acceptance Basis:**
- All blocking conditions satisfied
- Silent normalization eliminated
- Weight semantics explicitly defined
- Invariants formally stated and proven
- Counterfactual misuse analyzed
- Version semantics contractual
- No undocumented behavior
- No code-doc divergence
- No scientific misinterpretation risk

**Acceptance Scope:**
- Current system is internally coherent
- Current system is semantically explicit
- Current system is safe against silent misinterpretation

**Acceptance Limitations:**
- Does NOT mean system is perfect
- Does NOT mean edge cases fully mitigated
- Does NOT mean future changes are safe by default
- Only means current state passes formal verification

---

## PERMANENT RULES (NON-REVERSIBLE)

### Rule A — No Silent Mathematics

**Statement:** Any mathematical transformation (normalization, scaling, clipping, smoothing) must be:
- Named
- Explained
- Warned
- Tested
- Documented

**Enforcement:** If math happens and readers aren't told → BLOCKED

**Examples:**
- Weight normalization explicitly documented
- Clipping operations documented in code comments
- Silent scaling without documentation → BLOCKED

---

### Rule B — Documentation Is Part of the System

**Statement:** Documentation is treated as:
- A first-class artifact
- A correctness surface
- A potential failure mode

**Enforcement:** Docs subject to same verification discipline as code

**Implications:**
- Documentation bugs are system bugs
- Documentation divergence is code-doc divergence
- Documentation ambiguity is semantic ambiguity

---

### Rule C — Version Numbers Are Legal Contracts

**Statement:** Any version change requires:
- Explicit guarantees
- Explicit invalidated assumptions
- Explicit migration notes (even if "none required")

**Enforcement:** No "minor" version bumps without explanation

**Required Elements:**
- Version contract declaration
- Backward compatibility guarantees
- Breaking change documentation
- Migration guide (if applicable)

---

### Rule D — Agents Never Decide Acceptance

**Statement:** Agents may:
- Verify
- Prove
- Analyze
- Recommend

**Agents may NEVER:**
- Declare ACCEPT
- Merge without approval
- Collapse verification steps

**Enforcement:** Acceptance authority permanently reserved to Controller

---

### Rule E — No Bugs Means No Ambiguity

**Statement:** "Zero bugs" includes:
- Semantic bugs
- Interpretive bugs
- Documentation-induced bugs
- Scientific inference bugs

**Enforcement:** If a user can misunderstand something reasonably, that is treated as a bug

**Prime Directive:** "If a reasonable expert could misunderstand it, the system is wrong."

---

## MASTER PROMPT v4 — CANONICAL RULES

**Trust Level:** ZERO
**Bug Tolerance:** ZERO (including semantic bugs)
**Authority:** Controller-supervised
**Assumption Budget:** NONE

**Operating Principle:** System treats misinterpretation as failure

### Prime Directive

**"If a reasonable expert could misunderstand it, the system is wrong."**

### Non-Negotiable Constraints

1. **Every transformation must be explicit**
2. **Every number must have semantics**
3. **Every version must have a contract**
4. **Every invariant must be testable**
5. **Every agent claim must be provable**
6. **Every fix must reduce ambiguity**
7. **Every change must be reversible**
8. **Every acceptance requires controller review**

---

## NEW MANDATORY CHECKS

### Check 11 — Semantic Drift Detection

**Requirement:** Prove that meaning today == meaning yesterday, OR explicitly document the difference

**Enforcement:** If meaning changes silently → BLOCK

**Verification Method:**
- Compare current semantics to previous version
- Document any semantic changes
- Ensure changes are explicit, not implicit

---

### Check 12 — External Reader Simulation

**Requirement:** Answer: "How could a competent but non-author reader misunderstand this?"

**Enforcement:** If an answer exists:
- Mitigate, OR
- Warn, OR
- Redesign

**Verification Method:**
- Simulate reader perspective
- Identify potential misinterpretations
- Address each identified risk

---

### Check 13 — Downstream Misuse Containment

**Assumptions:**
- Someone will copy tables
- Someone will quote weights
- Someone will publish results

**Requirements:** Ensure:
- Misuse is detectable
- Misuse is warned against
- Misuse does not silently corrupt conclusions

**Verification Method:**
- Identify misuse scenarios
- Add warnings/guards
- Test misuse detection

---

## ACCEPTANCE BAR (FINAL FORM)

Acceptance is only possible when:

- No silent behavior exists
- No ambiguous math exists
- No undocumented semantics exist
- No agent assertion is unverified
- No reasonable expert can be misled

**All conditions must be satisfied simultaneously.**

---

## VERIFICATION ARTIFACTS

**Current Verification Status:**
- **Formal Verification Report:** `FORMAL_VERIFICATION_REPORT.md`
- **Zero-Trust Audit:** `ZERO_TRUST_AUDIT_REPORT.md`
- **Zero-Trust Evidence:** `ZERO_TRUST_VERIFICATION_EVIDENCE.md`
- **Documentation:** `docs/BEHAVIOR_INDEX.md` (updated with normalization)

**Verification Level Achieved:**
- High-integrity research systems
- Safety-critical analytics
- Long-lived public-facing platforms

---

## CHANGE MANAGEMENT

**For Future Changes:**

1. **Code Changes:**
   - Must pass all mandatory checks (1-13)
   - Must maintain invariants
   - Must update documentation if semantics change

2. **Documentation Changes:**
   - Must be verified against code
   - Must not introduce ambiguity
   - Must pass external reader simulation

3. **Version Changes:**
   - Must declare version contract
   - Must document breaking changes
   - Must provide migration guide

4. **Acceptance Process:**
   - Agent verifies → recommends
   - Controller reviews → decides
   - No agent self-acceptance

---

## GOVERNANCE HISTORY

**2025-01-XX:** Master Prompt v4 established, governance rules codified
**2025-01-XX:** Behavior Index v2.5 formal verification completed
**2025-01-XX:** Weight normalization semantics explicitly documented
**2025-01-XX:** Version contract declared for v2.5

---

**This document is permanent and non-reversible.**
**These rules apply to all future work on this repository.**
