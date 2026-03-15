"""Structured logging system for reproducibility documentation.

Every agent operation is logged as a JSON line with:
- timestamp, agent, action, parameters, result, duration
- prompt hashes for LLM calls (reproducibility)
- data checksums for input/output files
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_DIR: Path | None = None
_LOGGER: logging.Logger | None = None


def init_logging(log_dir: str | Path = "data/logs") -> logging.Logger:
    """Initialize the structured logging system."""
    global _LOG_DIR, _LOGGER

    _LOG_DIR = Path(log_dir)
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = _LOG_DIR / f"session_{session_id}.jsonl"

    _LOGGER = logging.getLogger("biblio_review")
    _LOGGER.setLevel(logging.DEBUG)

    # Clear existing handlers
    _LOGGER.handlers.clear()

    # File handler: structured JSON lines
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_JsonFormatter())
    _LOGGER.addHandler(fh)

    # Console handler: human-readable
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _LOGGER.addHandler(ch)

    _LOGGER.info(f"Logging initialized: {log_file}")
    return _LOGGER


def get_logger() -> logging.Logger:
    """Get or create the logger."""
    if _LOGGER is None:
        return init_logging()
    return _LOGGER


class _JsonFormatter(logging.Formatter):
    """Format log records as JSON lines for structured analysis."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "agent": getattr(record, "agent", None),
            "action": getattr(record, "action", None),
            "message": record.getMessage(),
        }
        # Include extra structured data if present
        if hasattr(record, "data"):
            entry["data"] = record.data
        return json.dumps(entry, ensure_ascii=False, default=str)


class AgentLogger:
    """Context-aware logger for a specific agent.

    Usage:
        log = AgentLogger("metadata_processor")
        log.info("Starting deduplication", action="dedup", data={"records": 18838})
        with log.timed("dedup_pass_1"):
            # ... operation ...
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = get_logger()

    def _log(self, level: int, msg: str, **kwargs: Any) -> None:
        extra = {"agent": self.agent_name}
        if "action" in kwargs:
            extra["action"] = kwargs.pop("action")
        if "data" in kwargs:
            extra["data"] = kwargs.pop("data")
        self.logger.log(level, msg, extra=extra)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, **kwargs)

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, **kwargs)

    def timed(self, action: str) -> "_TimedContext":
        """Context manager that logs duration of an operation."""
        return _TimedContext(self, action)

    def log_llm_call(
        self,
        prompt: str,
        response: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        action: str = "llm_call",
    ) -> None:
        """Log an LLM API call with prompt hash for reproducibility."""
        self.info(
            f"LLM call: {model}",
            action=action,
            data={
                "model": model,
                "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
                "prompt_length": len(prompt),
                "response_length": len(response),
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
            },
        )

    def log_file_io(self, path: str | Path, operation: str, record_count: int = 0) -> None:
        """Log a file read/write with checksum."""
        p = Path(path)
        checksum = None
        if p.exists():
            checksum = hashlib.md5(p.read_bytes()).hexdigest()[:12]
        self.info(
            f"File {operation}: {p.name}",
            action=f"file_{operation}",
            data={
                "path": str(p),
                "checksum": checksum,
                "size_bytes": p.stat().st_size if p.exists() else 0,
                "records": record_count,
            },
        )


class _TimedContext:
    """Context manager for timing operations."""

    def __init__(self, agent_logger: AgentLogger, action: str):
        self.log = agent_logger
        self.action = action
        self.start: float = 0

    def __enter__(self) -> "_TimedContext":
        self.start = time.perf_counter()
        self.log.info(f"Started: {self.action}", action=f"{self.action}_start")
        return self

    def __exit__(self, *exc: Any) -> None:
        duration = time.perf_counter() - self.start
        self.log.info(
            f"Completed: {self.action} ({duration:.2f}s)",
            action=f"{self.action}_end",
            data={"duration_seconds": round(duration, 3)},
        )
