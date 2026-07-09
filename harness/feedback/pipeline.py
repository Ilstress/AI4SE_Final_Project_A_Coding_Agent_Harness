"""FeedbackPipeline — 4-layer pipeline integration (SPEC §3.6, PLAN T8.9)."""

import dataclasses
from dataclasses import dataclass

from harness.feedback.controllers.governance import (
    GovernanceController,
    GovernanceDecision,
    GovernanceEvent,
)
from harness.feedback.controllers.recovery import RecoveryController, RecoveryDecision
from harness.feedback.coordination import CoordinationLayer, EscalationEvent, RecoverySignal
from harness.feedback.fingerprint import FingerprintStrategy
from harness.feedback.generators.diff_gen import DiffGen
from harness.feedback.generators.guard_gen import GuardGen
from harness.feedback.generators.lint_gen import LintGen
from harness.feedback.generators.parser_gen import ParserGen
from harness.feedback.generators.shell_gen import ShellGen
from harness.feedback.generators.test_gen import TestGen
from harness.feedback.generators.tool_exec_gen import ToolExecGen
from harness.feedback.router import FeedbackRouter, Track
from harness.models.feedback import Feedback, FeedbackMetadata, FeedbackSource, Severity


@dataclass(frozen=True)
class PipelineResult:
    """Result of processing a feedback event through the full pipeline.

    Contains the generated Feedback, routing decision, controller decisions,
    and any coordination events.
    """

    feedback: Feedback
    track: Track
    recovery_decision: RecoveryDecision | None = None
    governance_decision: GovernanceDecision | None = None
    escalation_event: EscalationEvent | None = None
    recovery_signal: RecoverySignal | None = None


# Generator dispatch table
_GENERATORS: dict[FeedbackSource, ShellGen | TestGen | LintGen | DiffGen | GuardGen | ParserGen | ToolExecGen] = {
    FeedbackSource.SHELL: ShellGen(),
    FeedbackSource.TEST: TestGen(),
    FeedbackSource.LINT: LintGen(),
    FeedbackSource.DIFF: DiffGen(),
    FeedbackSource.GUARDRAIL: GuardGen(),
    FeedbackSource.PARSER: ParserGen(),
    FeedbackSource.TOOL_EXECUTOR: ToolExecGen(),
}


# Map CoordinationLayer escalation events to GovernanceController events
_ESCALATION_TO_GOVERNANCE: dict[EscalationEvent, GovernanceEvent] = {
    EscalationEvent.CONVERGENCE_FAILURE: GovernanceEvent.CONVERGENCE_FAILURE,
    EscalationEvent.GUARDRAIL_TRIGGER: GovernanceEvent.GUARD_BLOCKED,
    EscalationEvent.PRIVILEGE_ESCALATION: GovernanceEvent.PRIVILEGE_ESCALATION,
}


class FeedbackPipeline:
    """Stateless orchestrator that coordinates the 4-layer feedback pipeline.

    The Pipeline itself holds no state — all state is held by the Controllers
    and CoordinationLayer, which are injected at construction time.

    Call order:
        Generator → FingerprintStrategy → Router → Controller → CoordinationLayer
    """

    def __init__(
        self,
        recovery: RecoveryController,
        governance: GovernanceController,
        coordination: CoordinationLayer,
    ) -> None:
        self._recovery = recovery
        self._governance = governance
        self._coordination = coordination

    def process(self, source: FeedbackSource, raw_data: dict) -> PipelineResult:
        """Process raw execution data through the full 4-layer pipeline.

        Args:
            source: Which FeedbackSource the raw_data belongs to.
            raw_data: Generator-specific raw data dict.

        Returns:
            PipelineResult with feedback, track, decisions, and coordination events.
        """
        # Layer 1: Generate Feedback
        feedback = self._generate(source, raw_data)

        # Layer 1b: Assign fingerprint
        feedback = self._assign_fingerprint(feedback)

        # Layer 2: Route to track
        track = FeedbackRouter.route(feedback)

        # Layer 3: Process in controller
        recovery_decision: RecoveryDecision | None = None
        governance_decision: GovernanceDecision | None = None

        if track == Track.RECOVERY:
            recovery_decision = self._recovery.process(feedback)
        else:
            governance_decision = self._governance.process(feedback)

        # Layer 4: Coordinate
        escalation_event: EscalationEvent | None = None
        recovery_signal: RecoverySignal | None = None

        if track == Track.RECOVERY:
            self._coordination.record(feedback)
            escalation_event = self._coordination.evaluate_escalation(
                self._recovery.state, feedback
            )
            if escalation_event is not None:
                governance_event = _ESCALATION_TO_GOVERNANCE[escalation_event]
                self._governance.process_event(governance_event)

        return PipelineResult(
            feedback=feedback,
            track=track,
            recovery_decision=recovery_decision,
            governance_decision=governance_decision,
            escalation_event=escalation_event,
            recovery_signal=recovery_signal,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate(source: FeedbackSource, raw_data: dict) -> Feedback:
        generator = _GENERATORS.get(source)
        if generator is None:
            # Fallback: return a SYSTEM-level error feedback
            return Feedback(
                fingerprint="",
                source=FeedbackSource.SYSTEM,
                severity=Severity.ERROR,
                payload={"error": f"No generator for source: {source.value}"},
                metadata=FeedbackMetadata(provider="", latency_ms=0, retry_count=0, trace_id=None),
                round=0,
                timestamp=0.0,
                tool_call=None,
                correlation_id=None,
            )
        return generator.generate(raw_data)

    @staticmethod
    def _assign_fingerprint(feedback: Feedback) -> Feedback:
        fp = FingerprintStrategy.generate(feedback)
        return dataclasses.replace(feedback, fingerprint=fp)
