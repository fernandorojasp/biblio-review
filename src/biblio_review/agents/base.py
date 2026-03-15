"""Base agent class providing common functionality for all pipeline agents.

Every agent inherits from BaseAgent and gets:
- Structured logging
- Checkpoint save/load
- Configuration access
- Standard execute() interface
- User interaction helpers
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from biblio_review.utils.checkpoints import AgentStatus, CheckpointManager
from biblio_review.utils.config import PipelineConfig
from biblio_review.utils.logging import AgentLogger


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents.

    Subclasses must implement:
        - name: str property (unique identifier)
        - description: str property (human-readable description)
        - _run(self, **kwargs) -> dict: core logic
        - _validate_inputs(self, **kwargs) -> bool: input validation

    The execute() method handles:
        1. Input validation
        2. Checkpoint checking (skip if already done)
        3. Calling _run()
        4. Saving checkpoint on success
        5. Error handling and checkpoint on failure
    """

    def __init__(self, config: PipelineConfig, checkpoint_mgr: CheckpointManager | None = None):
        self.config = config
        self.console = Console()
        self.log = AgentLogger(self.name)
        self.checkpoints = checkpoint_mgr or CheckpointManager(config.checkpoint_dir)

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this agent (e.g., 'metadata_processor')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description shown in CLI output."""
        ...

    @abstractmethod
    def _run(self, **kwargs: Any) -> dict[str, Any]:
        """Core agent logic. Returns a dict of results to checkpoint."""
        ...

    @abstractmethod
    def _validate_inputs(self, **kwargs: Any) -> bool:
        """Validate that all required inputs are available."""
        ...

    def execute(self, force: bool = False, **kwargs: Any) -> dict[str, Any]:
        """Execute the agent with full lifecycle management.

        Args:
            force: If True, re-run even if checkpoint shows completed.
            **kwargs: Agent-specific arguments.

        Returns:
            Dict of results from the agent's _run() method.
        """
        self.console.print(
            Panel(f"[bold]{self.description}[/bold]", title=f"Agent: {self.name}", border_style="blue")
        )

        # Check checkpoint
        if not force:
            status = self.checkpoints.get_status(self.name)
            if status == AgentStatus.COMPLETED:
                cp = self.checkpoints.load(self.name)
                self.console.print("[green]✓ Already completed. Use --force to re-run.[/green]")
                self.log.info("Skipped (already completed)", action="skip")
                return cp.get("data", {}) if cp else {}

        # Validate inputs
        self.log.info("Validating inputs", action="validate_start")
        if not self._validate_inputs(**kwargs):
            self.log.error("Input validation failed", action="validate_fail")
            self.checkpoints.save(self.name, AgentStatus.FAILED, error="Input validation failed")
            raise ValueError(f"Agent {self.name}: input validation failed")

        # Mark as running
        self.checkpoints.save(self.name, AgentStatus.RUNNING)
        self.log.info("Starting execution", action="execute_start")

        try:
            with self.log.timed(self.name):
                results = self._run(**kwargs)

            # Save success checkpoint
            self.checkpoints.save(self.name, AgentStatus.COMPLETED, data=results)
            self.console.print(f"[green]✓ {self.name} completed successfully[/green]")
            self.log.info("Execution completed", action="execute_end", data=results)
            return results

        except Exception as e:
            self.checkpoints.save(self.name, AgentStatus.FAILED, error=str(e))
            self.log.error(f"Execution failed: {e}", action="execute_error")
            self.console.print(f"[red]✗ {self.name} failed: {e}[/red]")
            raise

    # ── User interaction helpers ──────────────────────────────────────────

    def ask_confirm(self, message: str, default: bool = True) -> bool:
        """Ask the user for yes/no confirmation."""
        return Confirm.ask(message, default=default, console=self.console)

    def ask_text(self, message: str, default: str = "") -> str:
        """Ask the user for text input."""
        return Prompt.ask(message, default=default, console=self.console)

    def present_for_review(
        self,
        title: str,
        items: list[dict[str, str]],
        columns: list[str] | None = None,
    ) -> bool:
        """Present a table of items for user review and confirmation.

        Returns True if user approves, False otherwise.
        """
        table = Table(title=title, show_lines=True)
        cols = columns or list(items[0].keys()) if items else []
        for col in cols:
            table.add_column(col, style="cyan" if col == cols[0] else "")
        for item in items:
            table.add_row(*[str(item.get(c, "")) for c in cols])

        self.console.print(table)
        return self.ask_confirm("Do you approve these items?")

    def present_criteria(
        self,
        inclusion: list[dict[str, str]],
        exclusion: list[dict[str, str]],
        edge_cases: list[dict[str, str]],
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Present IC/EC criteria for user review and modification.

        Returns possibly-modified (inclusion, exclusion, edge_cases).
        """
        self.console.print("\n[bold]Proposed inclusion criteria:[/bold]")
        for ic in inclusion:
            self.console.print(f"  [green]✓[/green] {ic['id']}: {ic['description']}")

        self.console.print("\n[bold]Proposed exclusion criteria:[/bold]")
        for ec in exclusion:
            self.console.print(f"  [red]✗[/red] {ec['id']}: {ec['description']}")

        self.console.print("\n[bold]Edge cases:[/bold]")
        for edge in edge_cases:
            marker = "[green]include[/green]" if edge["decision"] == "include" else "[red]exclude[/red]"
            self.console.print(f"  [yellow]?[/yellow] {edge['case']} → {marker}")

        if self.ask_confirm("\nDo you approve these criteria?"):
            return inclusion, exclusion, edge_cases

        # Let user modify
        self.console.print("[yellow]Please edit configs/config.yaml and re-run.[/yellow]")
        raise SystemExit("Criteria not approved — edit config and retry")

    # ── File helpers ──────────────────────────────────────────────────────

    def ensure_dir(self, path: str | Path) -> Path:
        """Create directory if it doesn't exist."""
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def resolve_path(self, path: str | Path) -> Path:
        """Resolve a path relative to the project directory."""
        p = Path(path)
        if not p.is_absolute():
            p = Path(self.config.project_dir) / p
        return p.resolve()
