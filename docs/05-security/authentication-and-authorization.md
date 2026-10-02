# Two-Factor Identity Binding Mechanics

**Document ID:** `DOC-05-2FA`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Authentication vs. Authorization

DualKey distinguishes clearly between three security phases:
1. **Identification:** "Who claims to be presenting?" $\to$ Indicated by the RFID Card UID.
2. **Authentication:** "Is the presenter genuinely the registered owner of this credential?" $\to$ Proven by verifying that the live facial biometric matches the enrolled identity of the card owner.
3. **Authorization:** "Is this authenticated identity permitted access under current system conditions?" $\to$ Evaluated by the `AuthorizationPolicy` (checking active status, window validity, stable matches, and healthy system state).

```text
Presented RFID Card UID ──> [Database Lookup] ──> Expected Identity (Person A)
                                                           │
                                                           ▼
Live Camera Frame       ──> [LBPH Inference]  ──> Observed Identity (Person A)
                                                           │
                                                           ▼
                                            [Identity Correlation Gate]
                                            Expected == Observed ?
                                                   │
                                     ┌─────────────┴─────────────┐
                                    YES                          NO
                                     │                           │
                                     ▼                           ▼
                              [ACCESS_GRANTED]            [ACCESS_DENIED]
```

---

## 2. Why Single Factors Are Insufficient

### Vulnerability of RFID-Only (Factor 1 Alone)
* **Threat:** Lost, stolen, or borrowed RFID cards.
* **Failure Mode:** Anyone holding Person A's card can unlock the door without Person A being present.
* **Mitigation:** The card only acts as an index to establish an expected identity; possession alone cannot trigger an access grant.

### Vulnerability of Face-Only (Factor 2 Alone)
* **Threat:** False match across large populations, accidental triggers by passersby, and slow 1:N database searches.
* **Failure Mode:** A camera continuously running 1:N matching across a large database suffers higher False Acceptance Rates (FAR) and significant computational overhead.
* **Mitigation:** The RFID card reduces the biometric problem from a complex 1:N classification to a highly constrained 1:1 verification problem ("Is this face Person A?").

---

## 3. Two-Factor Binding Invariant

The access controller enforces that an identity grant requires simultaneous convergence of both factors within the temporal boundary:

$$\text{Factor}_1(\text{RFID} = \text{UID}_A) \;\land\; \text{Factor}_2(\text{Biometric} = \text{Face}_A) \;\land\; \Delta t \le 10.0\text{ s}$$

If Card B is presented and Person A looks at the camera, the system rejects the attempt with reason `FACE_MISMATCH` because $\text{Face}_A \ne \text{Owner}(\text{UID}_B)$.
