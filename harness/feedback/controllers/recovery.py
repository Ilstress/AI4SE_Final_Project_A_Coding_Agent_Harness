"""RecoveryController — table-driven state machine for self-healing (SPEC §3.6.3, PLAN T8.6)."""

from enum import Enum

from harness.models.feedback import Feedback


class RecoveryState(Enum):
    """States of the RecoveryController state machine."""

    IDLE = "IDLE"
    CONTINUE = "CONTINUE"
    RETRY = "RETRY"
    REPLAN = "REPLAN"
    WAIT = "WAIT"


class RecoveryEvent(Enum):
    """Events that trigger state transitions."""

    FEEDBACK_RECEIVED = "FEEDBACK_RECEIVED"
    SAME_ERROR = "SAME_ERROR"
    FEEDBACK_RESOLVED = "FEEDBACK_RESOLVED"
    RETRY_THRESHOLD = "RETRY_THRESHOLD"


class RecoveryDecision(Enum):
    """Decisions produced by the RecoveryController."""

    CONTINUE = "CONTINUE"
    RETRY = "RETRY"
    REPLAN = "REPLAN"
    WAIT = "WAIT"
    UPGRADE = "UPGRADE"


# Transition: (current_state, event, next_state, decision)
_Transition = tuple[RecoveryState, RecoveryEvent, RecoveryState, RecoveryDecision]

_TRANSITIONS: list[_Transition] = [
    (RecoveryState.IDLE, RecoveryEvent.FEEDBACK_RECEIVED, RecoveryState.CONTINUE, RecoveryDecision.CONTINUE),
    (RecoveryState.CONTINUE, RecoveryEvent.FEEDBACK_RECEIVED, RecoveryState.CONTINUE, RecoveryDecision.CONTINUE),
    (RecoveryState.CONTINUE, RecoveryEvent.SAME_ERROR, RecoveryState.RETRY, RecoveryDecision.RETRY),
    (RecoveryState.RETRY, RecoveryEvent.SAME_ERROR, RecoveryState.RETRY, RecoveryDecision.RETRY),
    (RecoveryState.RETRY, RecoveryEvent.FEEDBACK_RESOLVED, RecoveryState.CONTINUE, RecoveryDecision.CONTINUE),
    (RecoveryState.RETRY, RecoveryEvent.RETRY_THRESHOLD, RecoveryState.REPLAN, RecoveryDecision.REPLAN),
    (RecoveryState.REPLAN, RecoveryEvent.FEEDBACK_RECEIVED, RecoveryState.CONTINUE, RecoveryDecision.CONTINUE),
    (RecoveryState.REPLAN, RecoveryEvent.SAME_ERROR, RecoveryState.IDLE, RecoveryDecision.UPGRADE),
]


class RecoveryController:
    """Table-driven state machine for feedback-driven self-correction.

    RETRY_THRESHOLD = 3 consecutive same-fingerprint Feedback events.
    SAME_ERROR detection uses fingerprint matching.
    """

    RETRY_THRESHOLD = 3

    def __init__(self) -> None:
        self._state = RecoveryState.IDLE
        self._last_fingerprint: str = ""
        self._consecutive_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> RecoveryState:
        return self._state

    @property
    def consecutive_count(self) -> int:
        return self._consecutive_count

    def process(self, feedback: Feedback) -> RecoveryDecision:
        """Process a Feedback event and return a RecoveryDecision."""
        event = self._classify_event(feedback)
        return self._apply_transition(event, feedback)

    # ------------------------------------------------------------------
    # Event classification
    # ------------------------------------------------------------------

    def _classify_event(self, feedback: Feedback) -> RecoveryEvent:
        fingerprint = feedback.fingerprint

        if fingerprint == self._last_fingerprint and self._last_fingerprint != "":
            if (
                self._state == RecoveryState.RETRY
                and self._consecutive_count >= self.RETRY_THRESHOLD
            ):
                return RecoveryEvent.RETRY_THRESHOLD
            return RecoveryEvent.SAME_ERROR

        if self._state == RecoveryState.RETRY:
            return RecoveryEvent.FEEDBACK_RESOLVED
        return RecoveryEvent.FEEDBACK_RECEIVED

    # ------------------------------------------------------------------
    # Transition lookup & side effects
    # ------------------------------------------------------------------

    def _apply_transition(
        self, event: RecoveryEvent, feedback: Feedback
    ) -> RecoveryDecision:
        for current_state, evt, next_state, decision in _TRANSITIONS:
            if current_state == self._state and evt == event:
                self._execute_side_effects(event, next_state, feedback)
                self._state = next_state
                return decision

        # Fallback: stay in current state, return WAIT
        return RecoveryDecision.WAIT

    def _execute_side_effects(
        self,
        event: RecoveryEvent,
        next_state: RecoveryState,
        feedback: Feedback,
    ) -> None:
        fingerprint = feedback.fingerprint

        if event == RecoveryEvent.SAME_ERROR:
            self._consecutive_count += 1
            self._last_fingerprint = fingerprint
        elif event == RecoveryEvent.RETRY_THRESHOLD:
            self._consecutive_count = 0
        elif event in (RecoveryEvent.FEEDBACK_RESOLVED, RecoveryEvent.FEEDBACK_RECEIVED):
            self._last_fingerprint = fingerprint
            self._consecutive_count = 1
        # UPGRADE decision: reset to IDLE
        if next_state == RecoveryState.IDLE:
            self._last_fingerprint = ""
            self._consecutive_count = 0
