"""Configuration management for the bibliometric review pipeline."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass
class SearchConfig:
    """Configuration for search query optimization (A1)."""

    databases: list[str] = field(default_factory=lambda: ["wos", "scopus"])
    period_start: int = 2020
    period_end: int = 2025
    language: str = "english"
    document_types: list[str] = field(
        default_factory=lambda: ["article", "review", "conference paper"]
    )
    objectives_file: str = ""


@dataclass
class MetadataConfig:
    """Configuration for metadata processing (A2)."""

    input_dir: str = "data/raw"
    output_dir: str = "data/processed"
    dedup_thresholds: list[float] = field(default_factory=lambda: [1.0, 0.97, 0.95])
    dedup_fields: list[str] = field(
        default_factory=lambda: ["doi", "title", "year", "authors"]
    )
    manual_review_threshold: float = 0.90
    output_format: str = "bib"  # bib, ris, csv


@dataclass
class ScreeningConfig:
    """Configuration for AI-assisted screening (A4)."""

    model: str = "claude-sonnet-4-20250514"
    batch_size: int = 30
    inclusion_criteria: list[dict[str, str]] = field(default_factory=list)
    exclusion_criteria: list[dict[str, str]] = field(default_factory=list)
    edge_cases: list[dict[str, str]] = field(default_factory=list)
    validation_sample_pct: float = 0.05
    kappa_threshold: float = 0.70


@dataclass
class AnalysisConfig:
    """Configuration for bibliometric analysis (A5)."""

    r_executable: str = "Rscript"
    bibliometrix_version: str = "5.2.1"
    analyses: list[str] = field(
        default_factory=lambda: [
            "performance",
            "co_citation",
            "co_authorship",
            "keyword_cooccurrence",
            "thematic_map",
            "thematic_evolution",
        ]
    )
    split_period: bool = True
    split_year: int = 2023  # Pre/post GenAI cutpoint
    min_citations_cocitation: int = 5
    min_coauthorships: int = 2
    min_keyword_frequency: int = 5
    viz_dpi: int = 300
    viz_format: str = "png"


@dataclass
class PaperConfig:
    """Configuration for paper generation (A6)."""

    target_journal: str = ""
    author_guidelines_url: str = ""
    citation_style: str = "apa7"
    language: str = "english"
    max_words: int = 8000


@dataclass
class PipelineConfig:
    """Master configuration for the entire pipeline."""

    project_name: str = "bibliometric_review"
    project_dir: str = "."
    search: SearchConfig = field(default_factory=SearchConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    screening: ScreeningConfig = field(default_factory=ScreeningConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    paper: PaperConfig = field(default_factory=PaperConfig)

    # Global settings
    anthropic_api_key: str = ""
    log_dir: str = "data/logs"
    checkpoint_dir: str = "data/checkpoints"
    verbose: bool = False


def load_config(config_path: str | Path = "configs/config.yaml") -> PipelineConfig:
    """Load configuration from YAML file, with env var overrides."""
    load_dotenv()

    config_path = Path(config_path)
    raw: dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    config = PipelineConfig(
        project_name=raw.get("project_name", "bibliometric_review"),
        project_dir=raw.get("project_dir", "."),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", raw.get("anthropic_api_key", "")),
        log_dir=raw.get("log_dir", "data/logs"),
        checkpoint_dir=raw.get("checkpoint_dir", "data/checkpoints"),
        verbose=raw.get("verbose", False),
    )

    # Load sub-configs
    if "search" in raw:
        config.search = SearchConfig(**raw["search"])
    if "metadata" in raw:
        config.metadata = MetadataConfig(**raw["metadata"])
    if "screening" in raw:
        config.screening = ScreeningConfig(**raw["screening"])
    if "analysis" in raw:
        config.analysis = AnalysisConfig(**raw["analysis"])
    if "paper" in raw:
        config.paper = PaperConfig(**raw["paper"])

    return config


def save_default_config(output_path: str | Path = "configs/config.yaml") -> Path:
    """Generate a default config file with comments."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    default = {
        "project_name": "my_bibliometric_review",
        "project_dir": ".",
        "log_dir": "data/logs",
        "checkpoint_dir": "data/checkpoints",
        "verbose": False,
        "search": {
            "databases": ["wos", "scopus"],
            "period_start": 2020,
            "period_end": 2025,
            "language": "english",
            "document_types": ["article", "review", "conference paper"],
            "objectives_file": "docs/objectives.md",
        },
        "metadata": {
            "input_dir": "data/raw",
            "output_dir": "data/processed",
            "dedup_thresholds": [1.0, 0.97, 0.95],
            "dedup_fields": ["doi", "title", "year", "authors"],
            "manual_review_threshold": 0.90,
            "output_format": "bib",
        },
        "screening": {
            "model": "claude-sonnet-4-20250514",
            "batch_size": 30,
            "inclusion_criteria": [
                {"id": "IC1", "description": "Studies integrating >=2 data modalities"},
                {"id": "IC2", "description": "Application to medical diagnosis"},
                {"id": "IC3", "description": "Published 2020-2025"},
                {"id": "IC4", "description": "English language"},
                {"id": "IC5", "description": "Articles, reviews, or conference proceedings"},
                {"id": "IC6", "description": "Indexed in WoS or Scopus"},
            ],
            "exclusion_criteria": [
                {"id": "EC1", "description": "Unimodal AI systems"},
                {"id": "EC2", "description": "Non-diagnostic tasks (prognosis, treatment, etc.)"},
                {"id": "EC3", "description": "Grey literature, preprints, theses"},
                {"id": "EC4", "description": "Non-English language"},
                {"id": "EC5", "description": "No abstract available"},
                {"id": "EC6", "description": "Non-medical or tangential medical data"},
                {"id": "EC7", "description": "Pure engineering without explicit medical application"},
            ],
            "edge_cases": [
                {"case": "GenAI for synthetic medical data augmentation", "decision": "include"},
                {"case": "Radiology image + text report studies", "decision": "include"},
                {"case": "Generic multimodal architecture without medical application", "decision": "exclude"},
            ],
            "validation_sample_pct": 0.05,
            "kappa_threshold": 0.70,
        },
        "analysis": {
            "r_executable": "Rscript",
            "bibliometrix_version": "5.2.1",
            "analyses": [
                "performance",
                "co_citation",
                "co_authorship",
                "keyword_cooccurrence",
                "thematic_map",
                "thematic_evolution",
            ],
            "split_period": True,
            "split_year": 2023,
            "min_citations_cocitation": 5,
            "min_coauthorships": 2,
            "min_keyword_frequency": 5,
            "viz_dpi": 300,
            "viz_format": "png",
        },
        "paper": {
            "target_journal": "",
            "author_guidelines_url": "",
            "citation_style": "apa7",
            "language": "english",
            "max_words": 8000,
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(default, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    return output_path
