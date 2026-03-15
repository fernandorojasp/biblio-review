"""CLI orchestrator for biblio-review.

Entry point for all pipeline commands. Supports running individual agents
or the full pipeline with resume capability.

Usage:
    biblio-review query-optimize --config config.yaml
    biblio-review process --input ./data/raw/
    biblio-review audit --corpus ./data/processed/corpus.bib
    biblio-review screen --corpus ./data/processed/corpus.bib
    biblio-review analyze --corpus ./data/processed/corpus_screened.bib
    biblio-review write-paper --results ./data/outputs/metrics/
    biblio-review compare --mode temporal
    biblio-review run-all --config config.yaml
    biblio-review status
    biblio-review init
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from biblio_review.utils.checkpoints import AgentStatus, CheckpointManager, PIPELINE_ORDER
from biblio_review.utils.config import PipelineConfig, load_config, save_default_config
from biblio_review.utils.logging import init_logging

console = Console()

# ── Shared options ────────────────────────────────────────────────────────


def common_options(f):
    """Shared CLI options for all commands."""
    f = click.option("--config", "-c", default="configs/config.yaml", help="Path to config file")(f)
    f = click.option("--force", is_flag=True, help="Re-run even if already completed")(f)
    f = click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")(f)
    return f


def get_config(config_path: str, verbose: bool = False) -> PipelineConfig:
    """Load config and initialize logging."""
    cfg = load_config(config_path)
    if verbose:
        cfg.verbose = True
    init_logging(cfg.log_dir)
    return cfg


# ── CLI Group ─────────────────────────────────────────────────────────────


@click.group()
@click.version_option(version="0.1.0", prog_name="biblio-review")
def cli():
    """biblio-review — Reproducible bibliometric review pipeline.

    A CLI tool for conducting systematic bibliometric reviews using
    AI-assisted agents with R/Bibliometrix as the analytical engine.

    Run 'biblio-review init' to set up a new project.
    Run 'biblio-review status' to check pipeline progress.
    Run 'biblio-review run-all' to execute the full pipeline.
    """
    pass


# ── Init command ──────────────────────────────────────────────────────────


@cli.command()
@click.option("--dir", "-d", default=".", help="Project directory")
def init(dir: str):
    """Initialize a new bibliometric review project.

    Creates the directory structure, default config, and .env template.
    """
    project_dir = Path(dir).resolve()
    console.print(Panel(f"[bold]Initializing project in {project_dir}[/bold]", border_style="green"))

    # Create directories
    dirs = [
        "data/raw",
        "data/processed",
        "data/checkpoints",
        "data/logs",
        "data/outputs/metrics",
        "data/outputs/viz",
        "data/outputs/reports",
        "configs",
        "docs",
    ]
    for d in dirs:
        (project_dir / d).mkdir(parents=True, exist_ok=True)
        console.print(f"  📁 {d}/")

    # Generate default config
    config_path = project_dir / "configs" / "config.yaml"
    if not config_path.exists():
        save_default_config(config_path)
        console.print(f"  📄 {config_path.relative_to(project_dir)}")
    else:
        console.print(f"  [dim]⏭  configs/config.yaml already exists[/dim]")

    # Generate .env template
    env_path = project_dir / ".env"
    if not env_path.exists():
        env_path.write_text(
            "# biblio-review environment variables\n"
            "ANTHROPIC_API_KEY=sk-ant-...\n",
            encoding="utf-8",
        )
        console.print(f"  📄 .env (add your API key here)")
    else:
        console.print(f"  [dim]⏭  .env already exists[/dim]")

    # Generate .gitignore
    gitignore_path = project_dir / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text(
            "# biblio-review\n"
            ".env\n"
            "data/raw/\n"
            "data/processed/*.bib\n"
            "data/checkpoints/\n"
            "data/logs/\n"
            "data/outputs/\n"
            "__pycache__/\n"
            "*.egg-info/\n"
            ".venv/\n"
            "*.pyc\n",
            encoding="utf-8",
        )
        console.print(f"  📄 .gitignore")

    # Generate objectives template
    objectives_path = project_dir / "docs" / "objectives.md"
    if not objectives_path.exists():
        objectives_path.write_text(
            "# Research objectives\n\n"
            "## General objective\n\n"
            "[Describe the main goal of your bibliometric review]\n\n"
            "## Specific objectives\n\n"
            "- OE1: ...\n"
            "- OE2: ...\n\n"
            "## Research questions\n\n"
            "- RQ1: ...\n"
            "- RQ2: ...\n\n"
            "## Key conceptual domains\n\n"
            "1. [Domain A — e.g., artificial intelligence]\n"
            "2. [Domain B — e.g., multimodal processing]\n"
            "3. [Domain C — e.g., medical diagnosis]\n\n"
            "## Period and scope\n\n"
            "- Period: [start year]–[end year]\n"
            "- Databases: Web of Science, Scopus\n"
            "- Languages: English\n"
            "- Document types: Articles, Reviews, Conference proceedings\n",
            encoding="utf-8",
        )
        console.print(f"  📄 docs/objectives.md")

    console.print("\n[green]✓ Project initialized![/green]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Edit [cyan].env[/cyan] — add your ANTHROPIC_API_KEY")
    console.print("  2. Edit [cyan]configs/config.yaml[/cyan] — adjust settings for your review")
    console.print("  3. Edit [cyan]docs/objectives.md[/cyan] — define your research objectives")
    console.print("  4. Place raw data files (.ris, .bib) in [cyan]data/raw/[/cyan]")
    console.print("  5. Run [cyan]biblio-review run-all[/cyan] or individual agents")


# ── Status command ────────────────────────────────────────────────────────


@cli.command()
@common_options
def status(config: str, force: bool, verbose: bool):
    """Show the current pipeline status."""
    cfg = get_config(config, verbose)
    cm = CheckpointManager(cfg.checkpoint_dir)

    table = Table(title="Pipeline status", show_lines=True)
    table.add_column("#", style="dim")
    table.add_column("Agent", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Last run", style="dim")

    status_styles = {
        "completed": "[green]✓ completed[/green]",
        "running": "[yellow]⏳ running[/yellow]",
        "failed": "[red]✗ failed[/red]",
        "pending": "[dim]○ pending[/dim]",
        "skipped": "[dim]⏭ skipped[/dim]",
    }

    agent_labels = {
        "query_optimizer": "A1 · Query optimizer",
        "metadata_processor": "A2 · Metadata processor",
        "corpus_auditor": "A3 · Corpus auditor",
        "screener": "A4 · Screener",
        "bibliometric_engine": "A5 · Bibliometric engine",
        "paper_writer": "A6 · Paper writer",
        "comparator": "A7 · Comparator",
    }

    for i, agent_name in enumerate(PIPELINE_ORDER, 1):
        st = cm.get_status(agent_name)
        cp = cm.load(agent_name)
        timestamp = cp.get("timestamp", "—") if cp else "—"
        if timestamp != "—":
            timestamp = timestamp[:19].replace("T", " ")

        table.add_row(
            str(i),
            agent_labels.get(agent_name, agent_name),
            status_styles.get(st.value, st.value),
            timestamp,
        )

    console.print(table)

    resume_point = cm.get_resume_point()
    if resume_point:
        label = agent_labels.get(resume_point, resume_point)
        console.print(f"\n[bold]Next step:[/bold] {label}")
        console.print(f"[dim]Run: biblio-review run-all --resume[/dim]")
    else:
        console.print("\n[green]Pipeline complete![/green]")


# ── Individual agent commands ─────────────────────────────────────────────


@cli.command("query-optimize")
@common_options
@click.option("--objectives", "-o", default="", help="Path to objectives file")
def query_optimize(config: str, force: bool, verbose: bool, objectives: str):
    """A1 — Generate and validate search queries for WoS/Scopus."""
    cfg = get_config(config, verbose)
    from biblio_review.agents.query_optimizer import QueryOptimizer

    agent = QueryOptimizer(cfg)
    agent.execute(force=force, objectives=objectives)


@cli.command("process")
@common_options
@click.option("--input", "-i", "input_dir", default="", help="Input directory with raw files")
def process_metadata(config: str, force: bool, verbose: bool, input_dir: str):
    """A2 — Unify, normalize, and deduplicate bibliographic records."""
    cfg = get_config(config, verbose)
    from biblio_review.agents.metadata_processor import MetadataProcessor

    agent = MetadataProcessor(cfg)
    kwargs = {}
    if input_dir:
        kwargs["input_dir"] = input_dir
    agent.execute(force=force, **kwargs)


@cli.command("audit")
@common_options
@click.option("--corpus", default="", help="Path to corpus file")
def audit_corpus(config: str, force: bool, verbose: bool, corpus: str):
    """A3 — Validate corpus quality and generate PRISMA numbers."""
    cfg = get_config(config, verbose)
    from biblio_review.agents.corpus_auditor import CorpusAuditor

    agent = CorpusAuditor(cfg)
    kwargs = {}
    if corpus:
        kwargs["corpus"] = corpus
    agent.execute(force=force, **kwargs)


@cli.command("screen")
@common_options
@click.option("--corpus", default="", help="Path to corpus file")
def screen_records(config: str, force: bool, verbose: bool, corpus: str):
    """A4 — AI-assisted title/abstract screening."""
    cfg = get_config(config, verbose)
    from biblio_review.agents.screener import Screener

    agent = Screener(cfg)
    kwargs = {}
    if corpus:
        kwargs["corpus"] = corpus
    agent.execute(force=force, **kwargs)


@cli.command("analyze")
@common_options
@click.option("--corpus", default="", help="Path to corpus file")
@click.option("--analyses", "-a", multiple=True, help="Specific analyses to run")
@click.option("--no-split", is_flag=True, help="Skip period split analysis")
def analyze(config: str, force: bool, verbose: bool, corpus: str, analyses: tuple, no_split: bool):
    """A5 — Run bibliometric analyses via R/Bibliometrix."""
    cfg = get_config(config, verbose)
    from biblio_review.agents.bibliometric_engine import BibliometricEngine

    agent = BibliometricEngine(cfg)
    kwargs = {}
    if corpus:
        kwargs["corpus"] = corpus
    if analyses:
        kwargs["analyses"] = list(analyses)
    if no_split:
        kwargs["split"] = False
    agent.execute(force=force, **kwargs)


@cli.command("write-paper")
@common_options
@click.option("--results", "-r", default="", help="Path to metrics directory")
@click.option("--journal", "-j", default="", help="Target journal name")
def write_paper(config: str, force: bool, verbose: bool, results: str, journal: str):
    """A6 — Generate journal-adapted manuscript draft."""
    cfg = get_config(config, verbose)
    from biblio_review.agents.paper_writer import PaperWriter

    agent = PaperWriter(cfg)
    kwargs = {}
    if results:
        kwargs["results"] = results
    if journal:
        kwargs["journal"] = journal
    agent.execute(force=force, **kwargs)


@cli.command("compare")
@common_options
@click.option("--mode", "-m", type=click.Choice(["temporal", "cross"]), default="temporal")
@click.option("--dir-a", default="", help="First results directory (cross mode)")
@click.option("--dir-b", default="", help="Second results directory (cross mode)")
def compare(config: str, force: bool, verbose: bool, mode: str, dir_a: str, dir_b: str):
    """A7 — Compare pre/post periods or two corpora."""
    cfg = get_config(config, verbose)
    from biblio_review.agents.comparator import Comparator

    agent = Comparator(cfg)
    agent.execute(force=force, mode=mode, dir_a=dir_a, dir_b=dir_b)


# ── Full pipeline command ─────────────────────────────────────────────────


@cli.command("run-all")
@common_options
@click.option("--resume", is_flag=True, help="Resume from last checkpoint")
@click.option("--from-step", type=click.Choice([
    "query-optimize", "process", "audit", "screen", "analyze", "write-paper", "compare"
]), default=None, help="Start from a specific step")
def run_all(config: str, force: bool, verbose: bool, resume: bool, from_step: str | None):
    """Run the full pipeline (or resume from a checkpoint)."""
    cfg = get_config(config, verbose)
    cm = CheckpointManager(cfg.checkpoint_dir)

    console.print(Panel("[bold]Running full bibliometric review pipeline[/bold]", border_style="blue"))

    # Map CLI step names to agent names
    step_map = {
        "query-optimize": "query_optimizer",
        "process": "metadata_processor",
        "audit": "corpus_auditor",
        "screen": "screener",
        "analyze": "bibliometric_engine",
        "write-paper": "paper_writer",
        "compare": "comparator",
    }

    # Determine starting point
    if from_step:
        start_agent = step_map[from_step]
        start_idx = PIPELINE_ORDER.index(start_agent)
    elif resume:
        resume_point = cm.get_resume_point()
        if resume_point is None:
            console.print("[green]Pipeline already complete![/green]")
            return
        start_idx = PIPELINE_ORDER.index(resume_point)
        console.print(f"Resuming from: {resume_point}")
    else:
        start_idx = 0

    # Agent class imports
    agent_classes = {
        "query_optimizer": "biblio_review.agents.query_optimizer:QueryOptimizer",
        "metadata_processor": "biblio_review.agents.metadata_processor:MetadataProcessor",
        "corpus_auditor": "biblio_review.agents.corpus_auditor:CorpusAuditor",
        "screener": "biblio_review.agents.screener:Screener",
        "bibliometric_engine": "biblio_review.agents.bibliometric_engine:BibliometricEngine",
        "paper_writer": "biblio_review.agents.paper_writer:PaperWriter",
        "comparator": "biblio_review.agents.comparator:Comparator",
    }

    # Execute pipeline
    for i in range(start_idx, len(PIPELINE_ORDER)):
        agent_name = PIPELINE_ORDER[i]
        module_path, class_name = agent_classes[agent_name].rsplit(":", 1)

        # Dynamic import
        import importlib
        module = importlib.import_module(module_path)
        agent_class = getattr(module, class_name)

        agent = agent_class(cfg, cm)

        try:
            agent.execute(force=force)
        except SystemExit:
            console.print(f"\n[yellow]Pipeline paused at {agent_name}[/yellow]")
            console.print("[dim]Fix the issue and run: biblio-review run-all --resume[/dim]")
            sys.exit(0)
        except Exception as e:
            console.print(f"\n[red]Pipeline failed at {agent_name}: {e}[/red]")
            console.print("[dim]Fix the issue and run: biblio-review run-all --resume[/dim]")
            sys.exit(1)

    console.print("\n[green bold]✓ Pipeline complete![/green bold]")


# ── Clean command ─────────────────────────────────────────────────────────


@cli.command("clean")
@common_options
@click.option("--checkpoints", is_flag=True, help="Clear all checkpoints")
@click.option("--logs", is_flag=True, help="Clear all logs")
@click.option("--outputs", is_flag=True, help="Clear all outputs")
@click.option("--all", "all_data", is_flag=True, help="Clear everything")
def clean(config: str, force: bool, verbose: bool, checkpoints: bool, logs: bool, outputs: bool, all_data: bool):
    """Clean generated files and checkpoints."""
    import shutil

    cfg = get_config(config, verbose)

    if all_data:
        checkpoints = logs = outputs = True

    if not (checkpoints or logs or outputs):
        console.print("[yellow]Specify what to clean: --checkpoints, --logs, --outputs, or --all[/yellow]")
        return

    if checkpoints:
        p = Path(cfg.checkpoint_dir)
        if p.exists():
            shutil.rmtree(p)
            p.mkdir(parents=True)
            console.print("[green]✓ Checkpoints cleared[/green]")

    if logs:
        p = Path(cfg.log_dir)
        if p.exists():
            shutil.rmtree(p)
            p.mkdir(parents=True)
            console.print("[green]✓ Logs cleared[/green]")

    if outputs:
        for sub in ["metrics", "viz", "reports", "r_scripts"]:
            p = Path(f"data/outputs/{sub}")
            if p.exists():
                shutil.rmtree(p)
                p.mkdir(parents=True)
        console.print("[green]✓ Outputs cleared[/green]")


if __name__ == "__main__":
    cli()
