"""FingerprintStrategy — deterministic feedback fingerprinting (SPEC §3.6.1)."""

import hashlib

from harness.models.feedback import Feedback, FeedbackSource


class FingerprintStrategy:
    """Generates deterministic fingerprints for Feedback events.

    Fingerprints are SHA-256 hashes truncated to 16 hex characters,
    computed from source + severity + per-source key_params.
    Volatile fields (timestamp, round, metadata) are excluded.
    """

    @staticmethod
    def generate(feedback: Feedback) -> str:
        key_params = FingerprintStrategy._extract_key_params(feedback)
        raw = f"{feedback.source.value}|{feedback.severity.value}|{key_params}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _extract_key_params(feedback: Feedback) -> str:
        source = feedback.source
        payload = feedback.payload

        if source == FeedbackSource.SHELL:
            return str(payload.get("command", ""))[:80]
        elif source == FeedbackSource.TEST:
            return f"failed={payload.get('failed', 0)}"
        elif source == FeedbackSource.LINT:
            errors = payload.get("errors", [])
            return ",".join(errors) if errors else ""
        elif source == FeedbackSource.DIFF:
            return f"files={payload.get('files_changed', 0)}"
        elif source == FeedbackSource.GUARDRAIL:
            rules = payload.get("triggered_rules", [])
            return ",".join(rules) if rules else ""
        elif source == FeedbackSource.PARSER:
            return str(payload.get("error_type", ""))
        elif source == FeedbackSource.TOOL_EXECUTOR:
            return payload.get("error", "") or ""
        else:
            return ""
