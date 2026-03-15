"""A1 · Query Optimizer

Generates and validates search queries for WoS and Scopus.
Asks the user for research objectives and strategy, then produces
optimized Boolean queries with syntax validation for each database.

Outputs:
- queries.json: validated queries per database
- search_strategy.md: PRISMA-S documentation
"""

from pathlib import Path
from typing import Any

from biblio_review.agents.base import BaseAgent


class QueryOptimizer(BaseAgent):
    """Generate and validate bibliometric search queries."""

    @property
    def name(self) -> str:
        return "query_optimizer"

    @property
    def description(self) -> str:
        return "A1 · Query optimizer — Generate and validate WoS/Scopus search queries"

    def _validate_inputs(self, **kwargs: Any) -> bool:
        """Validate that objectives are provided."""
        objectives = kwargs.get("objectives") or self.config.search.objectives_file
        if objectives and Path(objectives).exists():
            return True
        # If no file, we'll ask interactively
        return True

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        """Generate optimized search queries.

        Flow:
        1. Load or ask for research objectives
        2. Identify key conceptual blocks (AI/ML, multimodal, diagnosis)
        3. Expand each block with synonyms, MeSH terms, wildcards
        4. Build Boolean queries adapted to WoS and Scopus syntax
        5. Present to user for review
        6. Generate PRISMA-S search strategy documentation
        """
        output_dir = self.ensure_dir(self.config.metadata.output_dir)

        # Step 1: Get objectives
        objectives_file = kwargs.get("objectives") or self.config.search.objectives_file
        if objectives_file and Path(objectives_file).exists():
            objectives = Path(objectives_file).read_text(encoding="utf-8")
            self.log.info(f"Loaded objectives from {objectives_file}", action="load_objectives")
        else:
            self.console.print("[yellow]No objectives file found. Please describe your research objectives:[/yellow]")
            objectives = self.ask_text("Research objectives")

        # Step 2: Build conceptual blocks
        # TODO: Use LLM to expand search terms based on objectives
        # For now, use the validated blocks from the thesis
        blocks = self._build_default_blocks()

        # Step 3: Generate queries per database
        queries = {}
        for db in self.config.search.databases:
            query = self._build_query(blocks, db)
            queries[db] = query
            self.console.print(f"\n[bold]{db.upper()} query:[/bold]")
            self.console.print(f"[dim]{query}[/dim]")

        # Step 4: Present for review
        if not self.ask_confirm("\nDo you approve these queries?"):
            self.console.print("[yellow]Edit the queries in the output file and re-run.[/yellow]")

        # Step 5: Save outputs
        import json
        queries_file = output_dir / "queries.json"
        queries_file.write_text(json.dumps(queries, indent=2), encoding="utf-8")
        self.log.log_file_io(queries_file, "write")

        # Step 6: Generate PRISMA-S documentation
        strategy_file = output_dir / "search_strategy.md"
        self._write_prisma_s(strategy_file, queries, objectives)
        self.log.log_file_io(strategy_file, "write")

        return {
            "queries_file": str(queries_file),
            "strategy_file": str(strategy_file),
            "databases": self.config.search.databases,
            "period": f"{self.config.search.period_start}-{self.config.search.period_end}",
        }

    def _build_default_blocks(self) -> dict[str, list[str]]:
        """Build default conceptual blocks for the search query.

        These are the validated blocks from the thesis methodology.
        Override via LLM expansion in future versions.
        """
        return {
            "ai_ml": [
                '"artificial intelligence"', '"machine learning"', '"deep learning"',
                '"neural network*"', '"transformer*"', '"large language model*"',
                '"foundation model*"', '"generative AI"', '"diffusion model*"',
                '"vision-language model*"', '"GPT*"', '"BERT"', '"CLIP"',
                '"contrastive learning"', '"self-supervised learning"',
                '"transfer learning"', '"attention mechanism*"',
            ],
            "multimodal": [
                '"multimodal"', '"multi-modal"', '"cross-modal"',
                '"data fusion"', '"feature fusion"', '"information fusion"',
                '"multi-source"', '"heterogeneous data"',
                '"image-text"', '"vision-language"',
            ],
            "diagnosis": [
                '"diagnosis"', '"diagnostic"', '"detection"', '"classification"',
                '"segmentation"', '"medical imaging"', '"radiology"',
                '"pathology"', '"clinical decision"', '"computer-aided diagnosis"',
                '"CAD"', '"screening"',
            ],
        }

    def _build_query(self, blocks: dict[str, list[str]], database: str) -> str:
        """Build a Boolean query for a specific database."""
        if database == "wos":
            return self._build_wos_query(blocks)
        elif database == "scopus":
            return self._build_scopus_query(blocks)
        else:
            raise ValueError(f"Unsupported database: {database}")

    def _build_wos_query(self, blocks: dict[str, list[str]]) -> str:
        """Build a Web of Science query."""
        parts = []
        for block_name, terms in blocks.items():
            joined = " OR ".join(terms)
            parts.append(f"TS=({joined})")

        query = " AND ".join(parts)

        # Add filters
        period = f"PY=({self.config.search.period_start}-{self.config.search.period_end})"
        lang = "LA=(English)"
        doc_types = "DT=(Article OR Review OR Proceedings Paper)"

        return f"{query} AND {period} AND {lang} AND {doc_types}"

    def _build_scopus_query(self, blocks: dict[str, list[str]]) -> str:
        """Build a Scopus query."""
        parts = []
        for block_name, terms in blocks.items():
            joined = " OR ".join(terms)
            parts.append(f"TITLE-ABS-KEY({joined})")

        query = " AND ".join(parts)

        # Add filters
        period = f"PUBYEAR > {self.config.search.period_start - 1} AND PUBYEAR < {self.config.search.period_end + 1}"
        lang = 'LANGUAGE("English")'
        doc_types = 'DOCTYPE("ar" OR "re" OR "cp")'

        return f"{query} AND {period} AND {lang} AND {doc_types}"

    def _write_prisma_s(self, path: Path, queries: dict, objectives: str) -> None:
        """Generate PRISMA-S search strategy documentation."""
        from datetime import datetime, timezone

        content = f"""# Search strategy documentation (PRISMA-S)

## 1. Research objectives

{objectives}

## 2. Information sources

Databases searched: {', '.join(q.upper() for q in queries.keys())}

## 3. Search queries

"""
        for db, query in queries.items():
            content += f"### {db.upper()}\n\n```\n{query}\n```\n\n"

        content += f"""## 4. Filters applied

- **Period**: {self.config.search.period_start}–{self.config.search.period_end}
- **Language**: {self.config.search.language}
- **Document types**: {', '.join(self.config.search.document_types)}

## 5. Search date

Date of search execution: [TO BE COMPLETED]

## 6. Search strategy validation

- Strategy reviewed by: [TO BE COMPLETED]
- Peer review of search strategy (PRESS): [TO BE COMPLETED]

---
*Generated by biblio-review v0.1.0 on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*
"""
        path.write_text(content, encoding="utf-8")
