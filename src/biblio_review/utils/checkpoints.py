"""Checkpoint system for resumable pipeline execution.

Each agent writes a checkpoint upon completion containing:
- agent name, status, timestamp
- input/output file paths and checksums
- key metrics and parameters used
- error info if failed

The orchestrator reads checkpoints to determine where to resume.
"""

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# Canonical pipeline order
PIPELINE_ORDER = [
    "query_optimizer",
    "metadata_processor",
    "corpus_auditor",
    "screener",
    "bibliometric_engine",
    "paper_writer",
    "comparator",
]


class CheckpointManager:
    """Manages pipeline checkpoints for resumability.

    Usage:
        cm = CheckpointManager("data/checkpoints")

        # Save a checkpoint
        cm.save("metadata_processor", AgentStatus.COMPLETED, {
            "input_files": ["wos.bib", "scopus.ris"],
            "output_file": "corpus.bib",
            "records_in": 18838,
            "records_out": 12862,
            "duplicates_removed": 5976,
        })

        # Check pipeline state
        cm.get_resume_point()  # returns "corpus_auditor"

        # Get last checkpoint for an agent
        cp = cm.load("metadata_processor")
    """

    def __init__(self, checkpoint_dir: str | Path = "data/checkpoints"):
        self.dir = Path(checkpoint_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.pipeline_file = self.dir / "pipeline_state.json"

    def save(
        self,
        agent_name: str,
        status: AgentStatus,
        data: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> Path:
        """Save a checkpoint for an agent."""
        checkpoint = {
            "agent": agent_name,
            "status": status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }
        if error:
            checkpoint["error"] = error

        # Add file checksums for any paths in data
        if data:
            for key, value in list(data.items()):
                if isinstance(value, (str, Path)) and len(str(value)) < 260:
                    try:
                        p = Path(value)
                        if p.exists() and p.is_file():
                            checkpoint["data"][f"{key}_checksum"] = (
                                hashlib.md5(p.read_bytes()).hexdigest()[:12]
                            )
                    except OSError:
                        pass

        # Save agent-specific checkpoint
        cp_file = self.dir / f"{agent_name}.json"
        cp_file.write_text(json.dumps(checkpoint, indent=2, default=str), encoding="utf-8")

        # Update pipeline state
        self._update_pipeline_state(agent_name, status)

        return cp_file

    def load(self, agent_name: str) -> dict[str, Any] | None:
        """Load the last checkpoint for an agent."""
        cp_file = self.dir / f"{agent_name}.json"
        if cp_file.exists():
            return json.loads(cp_file.read_text(encoding="utf-8"))
        return None

    def get_status(self, agent_name: str) -> AgentStatus:
        """Get the current status of an agent."""
        cp = self.load(agent_name)
        if cp is None:
            return AgentStatus.PENDING
        return AgentStatus(cp["status"])

    def get_resume_point(self) -> str | None:
        """Determine where to resume the pipeline.

        Returns the name of the first agent that hasn't completed,
        or None if the entire pipeline is done.
        """
        for agent_name in PIPELINE_ORDER:
            status = self.get_status(agent_name)
            if status != AgentStatus.COMPLETED:
                return agent_name
        return None

    def get_pipeline_state(self) -> dict[str, str]:
        """Get the status of all agents in the pipeline."""
        state = {}
        for agent_name in PIPELINE_ORDER:
            state[agent_name] = self.get_status(agent_name).value
        return state

    def clear(self, agent_name: str | None = None) -> None:
        """Clear checkpoint(s). If agent_name is None, clear all."""
        if agent_name:
            cp_file = self.dir / f"{agent_name}.json"
            cp_file.unlink(missing_ok=True)
        else:
            for f in self.dir.glob("*.json"):
                f.unlink()

    def _update_pipeline_state(self, agent_name: str, status: AgentStatus) -> None:
        """Update the combined pipeline state file."""
        state = {}
        if self.pipeline_file.exists():
            state = json.loads(self.pipeline_file.read_text(encoding="utf-8"))

        state[agent_name] = {
            "status": status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        state["last_updated"] = datetime.now(timezone.utc).isoformat()

        self.pipeline_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def verify_input_integrity(self, agent_name: str, input_path: str | Path) -> bool:
        """Verify that the input file hasn't changed since the previous agent ran.

        This catches cases where someone modifies intermediate files manually.
        """
        # Find the agent that produced this file
        for prev_agent in PIPELINE_ORDER:
            if prev_agent == agent_name:
                break
            cp = self.load(prev_agent)
            if cp and cp.get("data", {}).get("output_file") == str(input_path):
                expected_checksum = cp["data"].get("output_file_checksum")
                if expected_checksum:
                    actual = hashlib.md5(Path(input_path).read_bytes()).hexdigest()[:12]
                    return actual == expected_checksum
        return True  # No prior checkpoint to compare against
