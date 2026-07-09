"""FeedbackGenerator ABC — SPEC §3.6.1."""

from abc import ABC, abstractmethod
from typing import Any

from harness.models.feedback import Feedback


class FeedbackGenerator(ABC):
    """Abstract base for feedback generators.

    Each generator inspects raw execution data and produces a Feedback
    event.  Generators do NOT set the fingerprint (that is done centrally
    by FingerprintStrategy), do NOT route, and do NOT make decisions.
    """

    @abstractmethod
    def generate(self, raw_data: Any) -> Feedback:
        """Produce a Feedback event from *raw_data*."""
        ...
