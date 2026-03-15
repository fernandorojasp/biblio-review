"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest

from biblio_review.utils.config import PipelineConfig, load_config, save_default_config


class TestConfig:
    def test_default_config(self):
        cfg = PipelineConfig()
        assert cfg.project_name == "bibliometric_review"
        assert cfg.search.period_start == 2020
        assert cfg.search.period_end == 2025
        assert cfg.screening.model == "claude-sonnet-4-20250514"
        assert cfg.analysis.split_year == 2023

    def test_save_and_load_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_config.yaml"
            save_default_config(path)
            assert path.exists()

            cfg = load_config(path)
            assert cfg.project_name == "my_bibliometric_review"
            assert cfg.search.databases == ["wos", "scopus"]
            assert len(cfg.screening.inclusion_criteria) == 6
            assert len(cfg.screening.exclusion_criteria) == 7

    def test_screening_criteria_loaded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_config.yaml"
            save_default_config(path)
            cfg = load_config(path)

            ic_ids = [c["id"] for c in cfg.screening.inclusion_criteria]
            assert "IC1" in ic_ids
            assert "IC6" in ic_ids

            ec_ids = [c["id"] for c in cfg.screening.exclusion_criteria]
            assert "EC1" in ec_ids
            assert "EC7" in ec_ids

    def test_load_nonexistent_config_returns_defaults(self):
        cfg = load_config("/tmp/nonexistent_config.yaml")
        assert cfg.project_name == "bibliometric_review"
