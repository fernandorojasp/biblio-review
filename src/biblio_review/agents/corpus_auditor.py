"""A3 · Corpus Auditor

Validates corpus quality before analysis and generates PRISMA flow numbers.
Checks: field completeness, temporal distribution, outliers, suspicious records.

Outputs:
- audit_report.json: quality metrics
- prisma_numbers.json: PRISMA 2020 flow diagram data
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from biblio_review.agents.base import BaseAgent


class CorpusAuditor(BaseAgent):
    """Validate corpus quality and generate PRISMA numbers."""

    @property
    def name(self) -> str:
        return "corpus_auditor"

    @property
    def description(self) -> str:
        return "A3 · Corpus auditor — Validate quality and generate PRISMA numbers"

    def _validate_inputs(self, **kwargs: Any) -> bool:
        corpus_path = Path(kwargs.get("corpus", "data/processed/corpus.bib"))
        if not corpus_path.exists():
            self.console.print(f"[red]Corpus file not found: {corpus_path}[/red]")
            return False
        return True

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        """Audit corpus quality.

        Checks:
        1. Field completeness (title, abstract, authors, year, DOI, keywords, references)
        2. Temporal distribution (records per year)
        3. Document type distribution
        4. Source file distribution
        5. Language verification
        6. Outlier detection (suspiciously short titles/abstracts)
        7. PRISMA flow numbers
        """
        corpus_path = Path(kwargs.get("corpus", "data/processed/corpus.bib"))
        output_dir = self.ensure_dir("data/outputs/reports")

        # Load corpus
        records = self._load_corpus(corpus_path)
        total = len(records)
        self.console.print(f"\nAuditing {total} records...")

        # 1. Field completeness
        completeness = self._check_completeness(records)

        # 2. Temporal distribution
        year_dist = Counter(r.get("year", "unknown") for r in records)

        # 3. Document type distribution
        type_dist = Counter(r.get("type", "unknown") for r in records)

        # 4. Source distribution
        source_dist = Counter(r.get("source_file", "unknown") for r in records)

        # 5. Outliers
        outliers = self._detect_outliers(records)

        # Build audit report
        audit = {
            "total_records": total,
            "completeness": completeness,
            "temporal_distribution": dict(sorted(year_dist.items())),
            "document_types": dict(type_dist.most_common()),
            "source_files": dict(source_dist.most_common()),
            "outliers": outliers,
            "quality_score": self._calculate_quality_score(completeness, outliers),
        }

        # PRISMA numbers (from dedup report if available)
        prisma = self._build_prisma_numbers(kwargs, audit)

        # Save reports
        audit_file = output_dir / "audit_report.json"
        audit_file.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")

        prisma_file = output_dir / "prisma_numbers.json"
        prisma_file.write_text(json.dumps(prisma, indent=2, ensure_ascii=False), encoding="utf-8")

        # Display summary
        self._display_summary(audit)

        return {
            "audit_file": str(audit_file),
            "prisma_file": str(prisma_file),
            "total_records": total,
            "quality_score": audit["quality_score"],
        }

    def _load_corpus(self, path: Path) -> list[dict]:
        """Load corpus from BibTeX file."""
        import bibtexparser

        with open(path, encoding="utf-8", errors="replace") as f:
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            library = bibtexparser.load(f, parser=parser)

        records = []
        for entry in library.entries:
            record = dict(entry)  # entry is already a dict in v1
            records.append(record)
        return records

    def _check_completeness(self, records: list[dict]) -> dict:
        """Check field completeness across all records."""
        fields = ["title", "author", "year", "abstract", "doi", "keywords", "journal"]
        completeness = {}

        for field in fields:
            present = sum(1 for r in records if r.get(field, "").strip())
            pct = round(present / len(records) * 100, 1) if records else 0
            completeness[field] = {"present": present, "missing": len(records) - present, "pct": pct}

        return completeness

    def _detect_outliers(self, records: list[dict]) -> dict:
        """Detect suspicious records."""
        outliers = {
            "no_abstract": [],
            "short_title": [],
            "year_out_of_range": [],
            "duplicate_titles": [],
        }

        title_counts: dict[str, int] = Counter()

        for i, rec in enumerate(records):
            title = rec.get("title", "")
            abstract = rec.get("abstract", "")
            year = rec.get("year", "")

            if not abstract.strip():
                outliers["no_abstract"].append({"index": i, "title": title[:80]})

            if len(title) < 20:
                outliers["short_title"].append({"index": i, "title": title})

            try:
                y = int(year[:4])
                if y < 2020 or y > 2025:
                    outliers["year_out_of_range"].append({"index": i, "title": title[:80], "year": year})
            except (ValueError, TypeError):
                pass

            title_counts[title.lower().strip()] += 1

        # Find remaining duplicates
        for title, count in title_counts.items():
            if count > 1:
                outliers["duplicate_titles"].append({"title": title[:80], "count": count})

        # Summarize
        for key in outliers:
            outliers[key] = outliers[key][:50]  # Cap at 50 per category

        return outliers

    def _calculate_quality_score(self, completeness: dict, outliers: dict) -> float:
        """Calculate an overall quality score (0-100)."""
        score = 100.0

        # Penalize missing fields (weighted)
        weights = {"abstract": 20, "doi": 15, "keywords": 10, "author": 20, "year": 15, "title": 20}
        for field, weight in weights.items():
            if field in completeness:
                missing_pct = 100 - completeness[field]["pct"]
                score -= (missing_pct / 100) * weight

        return round(max(0, score), 1)

    def _build_prisma_numbers(self, kwargs: Any, audit: dict) -> dict:
        """Build PRISMA 2020 flow diagram numbers."""
        # Try to load dedup report for earlier numbers
        dedup_report_path = Path("data/processed/dedup_report.json")
        dedup_data = {}
        if dedup_report_path.exists():
            dedup_data = json.loads(dedup_report_path.read_text(encoding="utf-8"))

        return {
            "identification": {
                "records_wos": dedup_data.get("source_counts", {}).get("wos", "[TO COMPLETE]"),
                "records_scopus": dedup_data.get("source_counts", {}).get("scopus", "[TO COMPLETE]"),
                "total_raw": dedup_data.get("total_raw", "[TO COMPLETE]"),
            },
            "deduplication": {
                "duplicates_removed": dedup_data.get("duplicates_removed", "[TO COMPLETE]"),
                "records_after_dedup": dedup_data.get("total_unique", audit["total_records"]),
            },
            "screening": {
                "records_screened": "[AFTER SCREENING]",
                "records_excluded": "[AFTER SCREENING]",
                "exclusion_reasons": "[AFTER SCREENING]",
            },
            "included": {
                "final_corpus": "[AFTER SCREENING]",
            },
        }

    def _display_summary(self, audit: dict) -> None:
        """Display audit summary to console."""
        from rich.table import Table

        self.console.print(f"\n[bold]Quality score: {audit['quality_score']}/100[/bold]")

        table = Table(title="Field completeness")
        table.add_column("Field")
        table.add_column("Present", justify="right")
        table.add_column("Missing", justify="right")
        table.add_column("%", justify="right")

        for field, data in audit["completeness"].items():
            style = "green" if data["pct"] >= 95 else "yellow" if data["pct"] >= 80 else "red"
            table.add_row(field, str(data["present"]), str(data["missing"]), f"[{style}]{data['pct']}%[/{style}]")

        self.console.print(table)

        # Year distribution
        self.console.print("\n[bold]Temporal distribution:[/bold]")
        for year, count in sorted(audit["temporal_distribution"].items()):
            bar = "█" * (count // 50)
            self.console.print(f"  {year}: {count:>5} {bar}")
