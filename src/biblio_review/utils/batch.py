"""Batch processor for handling datasets that exceed LLM context limits.

Splits records into chunks, processes each chunk, and merges results.
Supports progress tracking and resume from partial completion.
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TypeVar

from biblio_review.utils.logging import AgentLogger

T = TypeVar("T")


@dataclass
class BatchConfig:
    """Configuration for batch processing."""

    max_records_per_batch: int = 50
    max_tokens_per_batch: int = 80_000  # Conservative estimate for Claude context
    avg_tokens_per_record: int = 500  # Title + abstract + metadata
    overlap_records: int = 0  # Records to repeat between batches for context
    retry_failed_batches: int = 2


@dataclass
class BatchResult:
    """Result of processing a single batch."""

    batch_index: int
    total_batches: int
    records_processed: int
    results: list[Any] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    status: str = "completed"


class BatchProcessor:
    """Process large datasets in chunks with progress tracking.

    Usage:
        processor = BatchProcessor(
            config=BatchConfig(max_records_per_batch=50),
            logger=AgentLogger("screener"),
            checkpoint_dir="data/checkpoints/screener_batches"
        )

        results = processor.process(
            records=all_records,
            process_fn=screen_batch,
            merge_fn=merge_screening_results,
        )
    """

    def __init__(
        self,
        config: BatchConfig | None = None,
        logger: AgentLogger | None = None,
        checkpoint_dir: str | Path = "data/checkpoints/batches",
    ):
        self.config = config or BatchConfig()
        self.log = logger or AgentLogger("batch_processor")
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def calculate_batch_size(self, records: list[dict]) -> int:
        """Calculate optimal batch size based on record content."""
        if not records:
            return 0

        # Sample first 20 records to estimate average token count
        sample = records[: min(20, len(records))]
        avg_tokens = 0
        for rec in sample:
            text = json.dumps(rec, default=str)
            avg_tokens += len(text) // 4  # ~4 chars per token approximation

        avg_tokens = avg_tokens // len(sample) if sample else self.config.avg_tokens_per_record

        # Calculate how many records fit in the token budget
        batch_size = self.config.max_tokens_per_batch // max(avg_tokens, 1)

        # Clamp to configured limits
        batch_size = min(batch_size, self.config.max_records_per_batch)
        batch_size = max(batch_size, 5)  # Minimum 5 per batch

        self.log.info(
            f"Batch size calculated: {batch_size} records "
            f"(~{avg_tokens} tokens/record, {self.config.max_tokens_per_batch} budget)",
            action="batch_size_calc",
            data={"batch_size": batch_size, "avg_tokens_per_record": avg_tokens},
        )
        return batch_size

    def split_into_batches(self, records: list[T]) -> list[list[T]]:
        """Split records into batches with optional overlap."""
        batch_size = self.calculate_batch_size(
            records if isinstance(records[0], dict) else [{"r": r} for r in records]
        )
        batches = []
        step = batch_size - self.config.overlap_records
        step = max(step, 1)

        for i in range(0, len(records), step):
            batch = records[i : i + batch_size]
            if batch:
                batches.append(batch)
            if i + batch_size >= len(records):
                break

        self.log.info(
            f"Split {len(records)} records into {len(batches)} batches",
            action="batch_split",
            data={"total_records": len(records), "num_batches": len(batches), "batch_size": batch_size},
        )
        return batches

    def process(
        self,
        records: list[T],
        process_fn: Callable[[list[T], int, int], BatchResult],
        merge_fn: Callable[[list[BatchResult]], Any] | None = None,
        resume: bool = True,
    ) -> Any:
        """Process all records in batches with checkpointing.

        Args:
            records: All records to process.
            process_fn: Function(batch, batch_index, total_batches) -> BatchResult
            merge_fn: Function to merge all BatchResults into final output.
            resume: If True, skip already-completed batches.

        Returns:
            Merged results from merge_fn, or list of BatchResults.
        """
        batches = self.split_into_batches(records)
        results: list[BatchResult] = []
        start_batch = 0

        # Resume from last completed batch if requested
        if resume:
            start_batch = self._get_resume_batch()
            if start_batch > 0:
                self.log.info(
                    f"Resuming from batch {start_batch}/{len(batches)}",
                    action="batch_resume",
                )
                # Load previous results
                for i in range(start_batch):
                    prev = self._load_batch_result(i)
                    if prev:
                        results.append(prev)

        for i in range(start_batch, len(batches)):
            batch = batches[i]
            self.log.info(
                f"Processing batch {i + 1}/{len(batches)} ({len(batch)} records)",
                action="batch_process",
                data={"batch_index": i, "batch_size": len(batch)},
            )

            retries = 0
            while retries <= self.config.retry_failed_batches:
                try:
                    result = process_fn(batch, i, len(batches))
                    results.append(result)
                    self._save_batch_result(i, result)
                    break
                except Exception as e:
                    retries += 1
                    self.log.error(
                        f"Batch {i + 1} failed (attempt {retries}): {e}",
                        action="batch_error",
                        data={"batch_index": i, "retry": retries, "error": str(e)},
                    )
                    if retries > self.config.retry_failed_batches:
                        results.append(
                            BatchResult(
                                batch_index=i,
                                total_batches=len(batches),
                                records_processed=0,
                                errors=[str(e)],
                                status="failed",
                            )
                        )

        # Merge results
        if merge_fn:
            return merge_fn(results)
        return results

    def _save_batch_result(self, batch_index: int, result: BatchResult) -> None:
        """Save a batch result checkpoint."""
        cp_file = self.checkpoint_dir / f"batch_{batch_index:04d}.json"
        data = {
            "batch_index": result.batch_index,
            "total_batches": result.total_batches,
            "records_processed": result.records_processed,
            "status": result.status,
            "errors": result.errors,
            # Don't save full results — they can be large
            "result_count": len(result.results),
        }
        cp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_batch_result(self, batch_index: int) -> BatchResult | None:
        """Load a batch result from checkpoint."""
        cp_file = self.checkpoint_dir / f"batch_{batch_index:04d}.json"
        if cp_file.exists():
            data = json.loads(cp_file.read_text(encoding="utf-8"))
            return BatchResult(
                batch_index=data["batch_index"],
                total_batches=data["total_batches"],
                records_processed=data["records_processed"],
                status=data["status"],
                errors=data.get("errors", []),
            )
        return None

    def _get_resume_batch(self) -> int:
        """Find the first incomplete batch."""
        i = 0
        while True:
            cp_file = self.checkpoint_dir / f"batch_{i:04d}.json"
            if not cp_file.exists():
                return i
            data = json.loads(cp_file.read_text(encoding="utf-8"))
            if data.get("status") != "completed":
                return i
            i += 1
