"""In-memory batch deduplication for gateway uploads."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class BatchState:
    last_committed_end_offset: int = 0
    last_batch_hashes: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class DedupeDecision:
    decision: str
    effective_start_offset: int
    should_forward: bool


class BatchDeduper:
    """Track per-source upload batches in process memory.

    This is intentionally simple for prototype step 1. State is lost on process
    restart and should be replaced by durable storage before production use.
    """

    def __init__(self) -> None:
        self._states: dict[str, BatchState] = {}
        self._lock = Lock()

    @staticmethod
    def make_key(tenant_id: str, source_id: str, file_epoch: str) -> str:
        return f"{tenant_id}:{source_id}:{file_epoch}"

    def evaluate(
        self,
        *,
        tenant_id: str,
        source_id: str,
        file_epoch: str,
        start_offset: int,
        end_offset: int,
        batch_hash: str,
    ) -> DedupeDecision:
        key = self.make_key(tenant_id, source_id, file_epoch)
        with self._lock:
            state = self._states.setdefault(key, BatchState())
            last_end = state.last_committed_end_offset

            if batch_hash in state.last_batch_hashes:
                return DedupeDecision(
                    decision="drop_duplicate",
                    effective_start_offset=start_offset,
                    should_forward=False,
                )

            if end_offset <= last_end:
                return DedupeDecision(
                    decision="drop_stale",
                    effective_start_offset=start_offset,
                    should_forward=False,
                )

            if start_offset < last_end < end_offset:
                decision = DedupeDecision(
                    decision="trim_overlap",
                    effective_start_offset=last_end,
                    should_forward=True,
                )
            else:
                decision = DedupeDecision(
                    decision="forward",
                    effective_start_offset=start_offset,
                    should_forward=True,
                )

            state.last_batch_hashes.add(batch_hash)
            state.last_committed_end_offset = max(last_end, end_offset)
            return decision
