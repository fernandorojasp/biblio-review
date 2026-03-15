# biblio-review

**Reproducible bibliometric review pipeline with AI-assisted agents.**

A CLI tool that orchestrates the entire lifecycle of a bibliometric review: from search query design to manuscript generation. Built for researchers who want rigorous, documented, and reproducible bibliometric analyses publishable in Q1 journals.

## Features

- **7 specialized agents** covering the full review pipeline
- **Hybrid architecture**: Python orchestration + R/Bibliometrix for validated calculations
- **AI-assisted screening** with Anthropic API (batch processing, human validation, Cohen's kappa)
- **Full reproducibility**: structured JSON logging, prompt hashing, file checksums
- **Resumable pipeline**: checkpoint system allows stopping and restarting at any point
- **Batch processing**: handles corpora of 10,000+ records within LLM token limits
- **Pre/post analysis**: built-in temporal comparison (e.g., pre/post GenAI disruption)
- **Journal-adapted output**: generates manuscript drafts tailored to target journal format

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Orchestrator CLI                            │
│              biblio-review [command]                         │
├─────────┬──────────┬──────────┬──────────┬─────────────────┤
│ A1      │ A2       │ A3       │ A4       │ A5              │
│ Query   │ Metadata │ Corpus   │ Screener │ Bibliometric    │
│ Optim.  │ Process. │ Auditor  │ (AI)     │ Engine (R)      │
│         │          │          │          │ ├─ Performance   │
│         │          │          │          │ ├─ Co-citation   │
│         │          │          │          │ ├─ Co-authorship │
│         │          │          │          │ ├─ Keywords      │
│         │          │          │          │ └─ Viz engine    │
├─────────┴────┬─────┴──────────┴──────────┴─────────────────┤
│ A6           │ A7                                           │
│ Paper Writer │ Comparator (pre/post or cross-corpus)        │
└──────────────┴─────────────────────────────────────────────-┘
```

## Requirements

### System requirements

| Component       | Version   | Purpose                                  |
|-----------------|-----------|------------------------------------------|
| Python          | ≥ 3.11    | Pipeline orchestration, data processing  |
| R               | ≥ 4.3     | Bibliometric calculations                |
| bibliometrix    | ≥ 5.0     | R package for science mapping            |
| Git             | ≥ 2.30    | Version control                          |
| Claude Code     | latest    | Development and execution environment    |

### API keys

| Service    | Required for         | Get it at                              |
|------------|----------------------|----------------------------------------|
| Anthropic  | A4 Screening, A6 Paper Writer | https://console.anthropic.com   |

## Installation

### Step 1 — Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/biblio-review.git
cd biblio-review
```

### Step 2 — Create Python virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate    # macOS/Linux
# .venv\Scripts\activate     # Windows
```

### Step 3 — Install the package

```bash
pip install -e ".[dev,viz]"
```

### Step 4 — Install R and bibliometrix

**macOS:**
```bash
brew install r
Rscript -e 'install.packages("bibliometrix", repos="https://cran.r-project.org")'
```

**Ubuntu/Debian:**
```bash
sudo apt-get install r-base r-base-dev
Rscript -e 'install.packages("bibliometrix", repos="https://cran.r-project.org")'
```

**Windows:**
- Download R from https://cran.r-project.org/
- Run: `Rscript -e 'install.packages("bibliometrix")'`

### Step 5 — Verify installation

```bash
# Check Python package
biblio-review --version

# Check R
Rscript -e 'cat(packageVersion("bibliometrix"))'
```

### Step 6 — Initialize your project

```bash
biblio-review init
```

This creates:
```
.
├── configs/
│   └── config.yaml          # Main configuration
├── data/
│   ├── raw/                 # Place your .ris/.bib files here
│   ├── processed/           # Unified corpus after dedup
│   ├── checkpoints/         # Pipeline state (auto-managed)
│   ├── logs/                # Structured JSON logs
│   └── outputs/
│       ├── metrics/         # CSV files with computed metrics
│       ├── viz/             # Figures (PNG 300dpi + HTML)
│       └── reports/         # Audit, screening, comparison reports
├── docs/
│   └── objectives.md        # Your research objectives
├── .env                     # API keys (not committed)
└── .gitignore
```

### Step 7 — Configure

Edit `.env`:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Edit `configs/config.yaml` to match your review:
```yaml
project_name: my_bibliometric_review
search:
  databases: [wos, scopus]
  period_start: 2020
  period_end: 2025
screening:
  model: claude-sonnet-4-20250514
  batch_size: 30
analysis:
  split_period: true
  split_year: 2023
```

Edit `docs/objectives.md` with your research questions.

## Usage

### Full pipeline

```bash
# Run everything from start to finish
biblio-review run-all --config configs/config.yaml

# Resume after an interruption
biblio-review run-all --resume

# Start from a specific step
biblio-review run-all --from-step screen
```

### Individual agents

```bash
# A1: Generate search queries
biblio-review query-optimize --objectives docs/objectives.md

# A2: Process raw metadata files
biblio-review process --input data/raw/

# A3: Audit corpus quality
biblio-review audit --corpus data/processed/corpus.bib

# A4: AI-assisted screening
biblio-review screen --corpus data/processed/corpus.bib

# A5: Run bibliometric analyses
biblio-review analyze --corpus data/processed/corpus_screened.bib
biblio-review analyze --corpus data/processed/corpus.bib --no-split
biblio-review analyze -a performance -a co_citation  # specific analyses only

# A6: Generate manuscript draft
biblio-review write-paper --journal "Scientometrics"

# A7: Compare periods
biblio-review compare --mode temporal
```

### Pipeline management

```bash
# Check status
biblio-review status

# Clean and restart
biblio-review clean --all
biblio-review clean --checkpoints    # only checkpoints
biblio-review clean --outputs        # only outputs

# Force re-run a completed step
biblio-review analyze --force
```

## Using with Claude Code

This project is designed to be developed and run inside [Claude Code](https://docs.anthropic.com/en/docs/claude-code). The `CLAUDE.md` file at the project root provides Claude Code with all the context it needs.

### Typical Claude Code workflow

```bash
# Open the project in Claude Code
cd biblio-review
claude

# Inside Claude Code, you can ask:
# "Run the screening agent on my corpus"
# "Show me the pipeline status"
# "Fix the R script error in co-citation analysis"
# "Add burst detection to the keyword analysis"
```

## Reproducibility

Every operation is logged in structured JSON format:

```json
{
  "timestamp": "2026-03-15T10:23:45.123Z",
  "level": "INFO",
  "agent": "screener",
  "action": "screen_batch",
  "data": {
    "model": "claude-sonnet-4-20250514",
    "prompt_hash": "a1b2c3d4e5f6g7h8",
    "tokens_in": 4521,
    "tokens_out": 892
  }
}
```

For publication, include in your Methods section:
- The `configs/config.yaml` used
- The `data/logs/` session files
- The `data/outputs/r_scripts/` generated R scripts
- The `data/outputs/reports/` audit and screening reports

## Validation

The screening agent (A4) includes a built-in validation workflow:

1. AI screens all records in batches
2. A random 5% sample is exported for manual classification
3. You classify the sample independently (fill in the `human_decision` column)
4. Compute Cohen's kappa using the provided R code:

```r
library(irr)
data <- read.csv("data/outputs/reports/validation_sample.csv")
kappa2(data[, c("decision", "human_decision")])
```

A kappa ≥ 0.70 is considered acceptable for bibliometric screening.

## Contributing

This is an open-source tool designed for the research community. Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request with tests

## License

MIT License — see [LICENSE](LICENSE) for details.

## Citation

If you use this tool in your research, please cite:

```bibtex
@software{biblio_review,
  title = {biblio-review: Reproducible bibliometric review pipeline},
  author = {[Your Name]},
  year = {2026},
  url = {https://github.com/YOUR_USERNAME/biblio-review},
  version = {0.1.0}
}
```

## Acknowledgments

- [Bibliometrix](https://www.bibliometrix.org/) by Aria & Cuccurullo (2017)
- [Anthropic Claude API](https://docs.anthropic.com/)
- [VOSviewer](https://www.vosviewer.com/) by van Eck & Waltman
