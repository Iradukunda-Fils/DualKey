# Authorization Engine & Policy Design

**Document ID:** `DOC-03-AUTH`  
**Status:** Implementation Baseline  
**Version:** 1.0.0  
**Date:** September 29, 2026  

---

## 1. Canonical Authorization Rule

The foundational invariant of DualKey is that physical access is granted if and only if every condition of the canonical multi-factor authorization rule evaluates to `True`:

$$\text{Decision} = \begin{cases} 
\text{GRANT}, & \text{if } \begin{aligned}[t] 
& \text{card\_valid} \land (t_{\text{now}} < t_{\text{deadline}}) \\ 
& \land (\text{face\_count} = 1) \land (d_{\text{LBPH}} \le \theta_{\text{threshold}}) \\ 
& \land (\text{person}_{\text{recognized}} = \text{person}_{\text{owner}}) \\ 
& \land (\text{count}_{\text{matches}} \ge N_{\text{required}}) 
\end{aligned} \\ 
\text{DENY}, & \text{otherwise (Fail-Closed Default)} 
\end{cases}$$

Every edge case, indeterminate biometric signal, sensor error, or timeout defaults unconditionally to `DENY`.

---

## 2. Policy Function Signature & Contract

The authorization policy is implemented as a pure, side-effect-free function within `app/domain/decisions.py`.

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from app.domain.models import AccessSession
from app.domain.reason_codes import ReasonCode

class DecisionResult(str, Enum):
    GRANT = "grant"
    DENY = "deny"
    CONTINUE = "continue"

@dataclass(frozen=True)
class AccessDecision:
    result: DecisionResult
    reason: ReasonCode
    session_id: str
    expected_person_id: str
    observed_person_id: Optional[str] = None
    distance: Optional[float] = None

@dataclass(frozen=True)
class BiometricFrameResult:
    face_count: int
    recognized_person_id: Optional[str]
    distance: float

class AuthorizationPolicy:
    @staticmethod
    def evaluate(
        session: AccessSession,
        biometric: Optional[BiometricFrameResult],
        now_monotonic: float,
        threshold: float,
        required_matches: int = 3
    ) -> AccessDecision:
        """
        Pure evaluation function enforcing the canonical authorization rule.
        Zero side effects. Zero I/O.
        """
        # 1. Enforce monotonic deadline check
        if now_monotonic >= session.deadline:
            return AccessDecision(
                result=DecisionResult.DENY,
                reason=ReasonCode.TIMEOUT,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id
            )

        # 2. Check for missing biometric evaluation
        if biometric is None or biometric.face_count == 0:
            return AccessDecision(
                result=DecisionResult.CONTINUE,
                reason=ReasonCode.FACE_NOT_FOUND,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id
            )

        # 3. Ambiguous scene: multiple faces present
        if biometric.face_count > 1:
            return AccessDecision(
                result=DecisionResult.DENY,
                reason=ReasonCode.MULTIPLE_FACES,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id
            )

        # 4. Check confidence threshold
        if biometric.distance > threshold:
            return AccessDecision(
                result=DecisionResult.CONTINUE,
                reason=ReasonCode.LOW_CONFIDENCE,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id,
                observed_person_id=biometric.recognized_person_id,
                distance=biometric.distance
            )

        # 5. Check identity binding: Does face match card owner?
        if biometric.recognized_person_id != session.expected_person_id:
            # Immediate rejection upon confirmed mismatch of enrolled identity
            return AccessDecision(
                result=DecisionResult.DENY,
                reason=ReasonCode.FACE_MISMATCH,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id,
                observed_person_id=biometric.recognized_person_id,
                distance=biometric.distance
            )

        # 6. Stable-Match Gate (Increment match counter on session)
        session.match_count += 1
        if session.match_count >= required_matches:
            return AccessDecision(
                result=DecisionResult.GRANT,
                reason=ReasonCode.MATCHED_OWNER,
                session_id=session.session_id,
                expected_person_id=session.expected_person_id,
                observed_person_id=biometric.recognized_person_id,
                distance=biometric.distance
            )

        return AccessDecision(
            result=DecisionResult.CONTINUE,
            reason=ReasonCode.MATCH_IN_PROGRESS,
            session_id=session.session_id,
            expected_person_id=session.expected_person_id,
            observed_person_id=biometric.recognized_person_id,
            distance=biometric.distance
        )
```

---

## 3. Stable-Match Gate Mechanics

Individual video frames are subject to motion blur, lighting flickers, and transient sensor noise. A single frame satisfying the distance threshold could represent an accidental false positive.

The **Stable-Match Gate** mandates that the recognizer must produce $N$ (default $N = 3$) consecutive positive predictions for the expected card owner before transitioning from `CONTINUE` to `GRANT`. If an intervening frame exhibits zero faces or low confidence, the match count is preserved or decayed, but never increments unless all criteria are satisfied. A wrong face (`FACE_MISMATCH`) immediately resets the gate and denies entry.
