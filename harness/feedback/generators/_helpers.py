"""Private helpers for Feedback generators — not part of the public API."""

import time
from typing import Any

from harness.models.feedback import Feedback, FeedbackMetadata, FeedbackSource, Severity


def _build_feedback(
    source: FeedbackSource,
    severity: Severity,
    payload: dict[str, Any],
    duration_ms: int,
) -> Feedback:
    """Build a Feedback with Pipeline-placeholder fields set to defaults.

    Fields filled later by the Pipeline:
        fingerprint, provider, retry_count, trace_id, round, tool_call, correlation_id
    """
    return Feedback(
        fingerprint="",
        source=source,
        severity=severity,
        payload=payload,
        metadata=FeedbackMetadata(
            provider="",
            latency_ms=duration_ms,
            retry_count=0,
            trace_id=None,
        ),
        round=0,
        timestamp=time.time(),
        tool_call=None,
        correlation_id=None,
    )
