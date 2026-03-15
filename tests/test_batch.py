"""Tests for the batch processor."""

import tempfile
from pathlib import Path

import pytest

from biblio_review.utils.batch import BatchConfig, BatchProcessor, BatchResult


@pytest.fixture
def batch_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


class TestBatchProcessor:
    def test_split_into_batches(self, batch_dir):
        processor = BatchProcessor(
            config=BatchConfig(max_records_per_batch=10, max_tokens_per_batch=100_000),
            checkpoint_dir=batch_dir,
        )
        records = [{"title": f"Record {i}", "abstract": "x" * 100} for i in range(25)]
        batches = processor.split_into_batches(records)
        assert len(batches) >= 2
        total = sum(len(b) for b in batches)
        assert total == 25

    def test_process_all_batches(self, batch_dir):
        processor = BatchProcessor(
            config=BatchConfig(max_records_per_batch=5, max_tokens_per_batch=100_000),
            checkpoint_dir=batch_dir,
        )
        records = [{"title": f"Record {i}", "abstract": "test"} for i in range(12)]

        def process_fn(batch, idx, total):
            return BatchResult(
                batch_index=idx,
                total_batches=total,
                records_processed=len(batch),
                results=[{"id": r["title"], "ok": True} for r in batch],
            )

        def merge_fn(results):
            return [item for br in results for item in br.results]

        merged = processor.process(records, process_fn, merge_fn, resume=False)
        assert len(merged) == 12
        assert all(r["ok"] for r in merged)

    def test_resume_skips_completed(self, batch_dir):
        processor = BatchProcessor(
            config=BatchConfig(max_records_per_batch=5, max_tokens_per_batch=100_000),
            checkpoint_dir=batch_dir,
        )

        # Simulate a completed batch
        import json
        cp_file = Path(batch_dir) / "batch_0000.json"
        cp_file.write_text(json.dumps({
            "batch_index": 0, "total_batches": 3,
            "records_processed": 5, "status": "completed",
            "result_count": 5, "errors": [],
        }))

        assert processor._get_resume_batch() == 1

    def test_batch_config_defaults(self):
        cfg = BatchConfig()
        assert cfg.max_records_per_batch == 50
        assert cfg.max_tokens_per_batch == 80_000
        assert cfg.retry_failed_batches == 2
