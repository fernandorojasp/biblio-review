"""Tests for the checkpoint system."""

import json
import tempfile
from pathlib import Path

import pytest

from biblio_review.utils.checkpoints import AgentStatus, CheckpointManager, PIPELINE_ORDER


@pytest.fixture
def checkpoint_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def cm(checkpoint_dir):
    return CheckpointManager(checkpoint_dir)


class TestCheckpointManager:
    def test_save_and_load(self, cm):
        cm.save("metadata_processor", AgentStatus.COMPLETED, data={"records": 100})
        cp = cm.load("metadata_processor")
        assert cp is not None
        assert cp["status"] == "completed"
        assert cp["data"]["records"] == 100

    def test_status_pending_when_no_checkpoint(self, cm):
        assert cm.get_status("metadata_processor") == AgentStatus.PENDING

    def test_status_after_save(self, cm):
        cm.save("screener", AgentStatus.RUNNING)
        assert cm.get_status("screener") == AgentStatus.RUNNING

    def test_resume_point_returns_first_incomplete(self, cm):
        cm.save("query_optimizer", AgentStatus.COMPLETED)
        cm.save("metadata_processor", AgentStatus.COMPLETED)
        assert cm.get_resume_point() == "corpus_auditor"

    def test_resume_point_none_when_all_complete(self, cm):
        for agent in PIPELINE_ORDER:
            cm.save(agent, AgentStatus.COMPLETED)
        assert cm.get_resume_point() is None

    def test_pipeline_state(self, cm):
        cm.save("query_optimizer", AgentStatus.COMPLETED)
        cm.save("metadata_processor", AgentStatus.FAILED, error="test error")
        state = cm.get_pipeline_state()
        assert state["query_optimizer"] == "completed"
        assert state["metadata_processor"] == "failed"
        assert state["corpus_auditor"] == "pending"

    def test_clear_single(self, cm):
        cm.save("screener", AgentStatus.COMPLETED)
        cm.clear("screener")
        assert cm.get_status("screener") == AgentStatus.PENDING

    def test_clear_all(self, cm):
        cm.save("screener", AgentStatus.COMPLETED)
        cm.save("corpus_auditor", AgentStatus.COMPLETED)
        cm.clear()
        assert cm.get_status("screener") == AgentStatus.PENDING
        assert cm.get_status("corpus_auditor") == AgentStatus.PENDING

    def test_error_stored_in_checkpoint(self, cm):
        cm.save("screener", AgentStatus.FAILED, error="API timeout")
        cp = cm.load("screener")
        assert cp["error"] == "API timeout"
