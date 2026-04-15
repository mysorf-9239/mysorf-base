"""Disabled/no-op implementation of the SweepRunner protocol."""

from __future__ import annotations

from ..core.interfaces import TrialFn
from ..core.schema import SweepSummary


class NullSweepRunner:
    """No-op sweep runner returned when sweeps are disabled."""

    def __init__(self, skip_reason: str = "sweeps disabled by configuration") -> None:
        self._skip_reason = skip_reason

    def run(
        self,
        override_sets: list[list[str]],
        trial_fn: TrialFn,
    ) -> SweepSummary:
        del override_sets
        del trial_fn
        return SweepSummary(results=[], skip_reason=self._skip_reason)
