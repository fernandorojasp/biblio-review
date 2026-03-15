# CLAUDE.md — Project instructions for Claude Code

## Project overview

**biblio-review** is a CLI tool for conducting reproducible bibliometric reviews using a pipeline of AI-assisted agents. It orchestrates Python (for data processing, screening, visualization) and R/Bibliometrix (for validated bibliometric calculations).

## Architecture

The system has 7 agents + 1 orchestrator:

- **A1 · Query Optimizer** — Generates and validates search queries for WoS/Scopus
- **A2 · Metadata Processor** — Unifies, normalizes, and deduplicates bibliographic records
- **A3 · Corpus Auditor** — Validates corpus quality and generates PRISMA numbers
- **A4 · Screener** — AI-assisted title/abstract screening with IC/EC criteria
- **A5 · Bibliometric Engine** — Orchestrates R/Bibliometrix for analysis (5 sub-agents)
- **A6 · Paper Writer** — Generates journal-adapted manuscript drafts
- **A7 · Comparator** — Compares two corpora or two time periods

## Tech stack

- **Python 3.11+** with Click CLI, pandas, networkx, rispy, bibtexparser
- **R 4.x** with bibliometrix package (called via subprocess)
- **Anthropic API** for screening (A4) and paper writing (A6)
- JSON-based checkpoints and structured logging throughout

## Key commands

```bash
# Install
pip install -e ".[dev]"

# Run individual agents
biblio-review query-optimize --config config.yaml
biblio-review process --input ./data/raw/ --output ./data/processed/
biblio-review audit --corpus ./data/processed/corpus.bib
biblio-review screen --corpus ./data/processed/corpus.bib
biblio-review analyze --corpus ./data/processed/corpus_screened.bib
biblio-review write-paper --results ./data/outputs/metrics/
biblio-review compare --a results_pre/ --b results_post/

# Full pipeline
biblio-review run-all --config config.yaml

# Resume from checkpoint
biblio-review run-all --config config.yaml --resume
```

## Development conventions

- All agents inherit from `BaseAgent` in `src/biblio_review/agents/base.py`
- Every agent writes a checkpoint after completion via `CheckpointManager`
- All operations are logged to `data/logs/` in structured JSON format
- R scripts are generated from templates in `src/biblio_review/templates/r_scripts/`
- Batch processing splits data into chunks when exceeding token limits
- Configuration lives in `configs/` as YAML files

## Testing

```bash
pytest tests/ -v
pytest tests/test_agents/ -v --agent=metadata  # single agent
```

## File conventions

- Input formats: `.ris`, `.bib`, `.csv`, `.txt` (WoS/Scopus exports)
- Internal format: `.bib` (BibTeX) for Bibliometrix compatibility
- Output formats: `.csv` (metrics), `.png`/`.html` (visualizations), `.docx` (reports)
- Checkpoints: `.json` in `data/checkpoints/`
- Logs: `.jsonl` in `data/logs/`
