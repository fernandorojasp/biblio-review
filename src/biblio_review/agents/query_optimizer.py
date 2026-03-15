"""A1 · Query Optimizer

Analyzes existing search queries against research objectives using Claude API.
Compares original queries with optimized versions and produces a comparison report
with actionable recommendations.

Inputs:
- docs/objectives.md: research objectives (OE1-OE5, PI1-PI5)
- docs/current_queries.md: original queries already executed

Outputs:
- queries_optimized.json: optimized queries per database
- query_comparison_report.md: comparison original vs optimized with recommendations
- search_strategy.md: PRISMA-S documentation
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from biblio_review.agents.base import BaseAgent


class QueryOptimizer(BaseAgent):
    """Analyze, compare, and optimize bibliometric search queries."""

    @property
    def name(self) -> str:
        return "query_optimizer"

    @property
    def description(self) -> str:
        return "A1 · Query optimizer — Analyze and optimize WoS/Scopus search queries"

    def _validate_inputs(self, **kwargs: Any) -> bool:
        """Validate that objectives and API key are available."""
        objectives = kwargs.get("objectives") or self.config.search.objectives_file
        if objectives and Path(objectives).exists():
            self.log.info(f"Objectives file found: {objectives}", action="validate")
        else:
            self.console.print("[yellow]No objectives file found. Will ask interactively.[/yellow]")

        if not self.config.anthropic_api_key:
            self.console.print("[red]ANTHROPIC_API_KEY not set. Required for query analysis.[/red]")
            return False

        return True

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        """Analyze and optimize search queries.

        Flow:
        1. Load research objectives
        2. Load original queries (if available)
        3. Send to Claude API for comparative analysis
        4. Generate optimized queries
        5. Produce comparison report
        6. Present results for user review
        7. Generate PRISMA-S documentation
        """
        output_dir = self.ensure_dir(self.config.metadata.output_dir)

        # Step 1: Load objectives
        objectives_file = kwargs.get("objectives") or self.config.search.objectives_file
        if objectives_file and Path(objectives_file).exists():
            objectives = Path(objectives_file).read_text(encoding="utf-8")
            self.log.info(f"Loaded objectives from {objectives_file}", action="load_objectives")
        else:
            self.console.print("[yellow]Please describe your research objectives:[/yellow]")
            objectives = self.ask_text("Research objectives")

        # Step 2: Load original queries
        original_queries = self._load_original_queries()

        # Step 3: Analyze with Claude API
        if original_queries:
            self.console.print("\n[bold]Analyzing original queries against objectives...[/bold]")
            analysis = self._analyze_queries_with_llm(objectives, original_queries)
        else:
            self.console.print("\n[bold]No original queries found. Generating from scratch...[/bold]")
            analysis = self._generate_queries_with_llm(objectives)

        # Step 4: Save comparison report
        report_file = output_dir / "query_comparison_report.md"
        report_file.write_text(analysis["report"], encoding="utf-8")
        self.log.log_file_io(report_file, "write")
        self.console.print(f"\n[green]✓ Comparison report saved: {report_file}[/green]")

        # Step 5: Save optimized queries
        queries_file = output_dir / "queries_optimized.json"
        queries_file.write_text(
            json.dumps(analysis["optimized_queries"], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        self.log.log_file_io(queries_file, "write")

        # Step 6: Display summary and recommendation
        self.console.print(f"\n[bold]Recommendation:[/bold] {analysis['recommendation']}")

        if analysis.get("should_rerun"):
            self.console.print("[yellow]⚠ The analysis suggests re-running searches with optimized queries.[/yellow]")
        else:
            self.console.print("[green]✓ Original queries are adequate. You can proceed with the current corpus.[/green]")

        # Step 7: Generate PRISMA-S
        strategy_file = output_dir / "search_strategy.md"
        final_queries = analysis["optimized_queries"]
        self._write_prisma_s(strategy_file, final_queries, objectives, original_queries)
        self.log.log_file_io(strategy_file, "write")

        return {
            "queries_file": str(queries_file),
            "report_file": str(report_file),
            "strategy_file": str(strategy_file),
            "recommendation": analysis["recommendation"],
            "should_rerun": analysis.get("should_rerun", False),
        }

    def _load_original_queries(self) -> str:
        """Load original queries from docs/current_queries.md."""
        candidates = [
            Path("docs/current_queries.md"),
            Path("docs/queries.md"),
            Path("docs/search_queries.md"),
        ]
        for path in candidates:
            if path.exists():
                content = path.read_text(encoding="utf-8")
                self.log.info(f"Loaded original queries from {path}", action="load_queries")
                self.console.print(f"  📄 Original queries loaded from: {path}")
                return content

        self.console.print("[dim]  No original queries file found in docs/[/dim]")
        return ""

    def _analyze_queries_with_llm(self, objectives: str, original_queries: str) -> dict:
        """Use Claude API to analyze original queries against objectives."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)

        system_prompt = """You are an expert in systematic review methodology and bibliometric search strategies.
You specialize in designing search queries for Web of Science and Scopus.
You know PRISMA-S guidelines for reporting search strategies.
You understand Boolean operators, field codes, truncation, and proximity operators for both databases.

Your task is to analyze existing search queries against research objectives and produce:
1. A detailed comparison report
2. Optimized queries
3. A clear recommendation on whether to re-run the searches

Be specific and actionable. If a query is good, say so. If it needs changes, explain exactly what and why."""

        user_prompt = f"""Analyze the following search queries against the research objectives.

## RESEARCH OBJECTIVES

{objectives}

## ORIGINAL QUERIES (already executed)

{original_queries}

## ANALYSIS REQUESTED

Produce a JSON response with this exact structure:

{{
  "report": "Full markdown comparison report (see format below)",
  "optimized_queries": {{
    "wos": "optimized WoS query string",
    "scopus": "optimized Scopus query string"
  }},
  "recommendation": "One-paragraph summary recommendation",
  "should_rerun": true/false
}}

The "report" field must be a complete markdown document with this structure:

# Query comparison report

## 1. Summary assessment
[Overall verdict: are the original queries adequate for the stated objectives?]

## 2. Coverage analysis by conceptual block

### Block A: AI and computational techniques
- **Original coverage**: [what terms are present]
- **Missing terms**: [terms that should be added, with justification tied to specific objectives]
- **Redundant terms**: [terms that could be removed]

### Block B: Multimodal processing
- [same structure]

### Block C: Medical diagnosis
- [same structure]

## 3. Syntax and technical issues
- [WoS-specific syntax issues]
- [Scopus-specific syntax issues]
- [Operator issues]
- [Truncation issues]

## 4. Alignment with research questions
[For each PI1-PI5, assess whether the queries would capture the relevant literature]

## 5. Optimized queries

### Web of Science
```
[full optimized query]
```

### Scopus
```
[full optimized query]
```

## 6. Diff summary
[Table of specific changes: term added/removed/modified, reason, affected objective]

## 7. Recommendation
[Clear recommendation: keep original / re-run with optimized / minor adjustments only]
[If re-run recommended: estimate of impact on corpus size]
[If keep original: confirmation that current corpus is adequate]

---

Respond ONLY with the JSON object. No markdown fences around the JSON itself."""

        with self.log.timed("llm_query_analysis"):
            response = client.messages.create(
                model=self.config.screening.model,
                max_tokens=8000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

        response_text = response.content[0].text

        self.log.log_llm_call(
            prompt=system_prompt + user_prompt,
            response=response_text,
            model=self.config.screening.model,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            action="query_analysis",
        )

        # Parse response
        try:
            clean = response_text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(clean)
        except json.JSONDecodeError:
            self.log.error("Failed to parse LLM response as JSON", action="parse_error")
            result = {
                "report": response_text,
                "optimized_queries": {"wos": "", "scopus": ""},
                "recommendation": "Could not parse structured response. See report for details.",
                "should_rerun": False,
            }

        return result

    def _generate_queries_with_llm(self, objectives: str) -> dict:
        """Generate queries from scratch when no originals are available."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)

        system_prompt = """You are an expert in systematic review methodology and bibliometric search strategies.
Generate optimized Boolean search queries for Web of Science and Scopus based on the provided research objectives.
Use proper field codes, truncation, and Boolean operators for each database."""

        user_prompt = f"""Generate search queries for the following research objectives.

## RESEARCH OBJECTIVES

{objectives}

## REQUIREMENTS

- Three conceptual blocks connected with AND: (1) AI/ML techniques, (2) multimodal processing, (3) medical diagnosis
- Period: {self.config.search.period_start}-{self.config.search.period_end}
- Language: English
- Document types: articles, reviews, conference proceedings
- Use proper syntax for each database (TS= for WoS, TITLE-ABS-KEY for Scopus)
- Include truncation (*) where appropriate
- Include both established and emerging terms (LLM, foundation models, diffusion models, etc.)

Respond with a JSON object:
{{
  "report": "Markdown document explaining the query design rationale",
  "optimized_queries": {{
    "wos": "complete WoS query",
    "scopus": "complete Scopus query"
  }},
  "recommendation": "Summary of the generated queries",
  "should_rerun": true
}}

Respond ONLY with the JSON object."""

        with self.log.timed("llm_query_generation"):
            response = client.messages.create(
                model=self.config.screening.model,
                max_tokens=6000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

        response_text = response.content[0].text

        self.log.log_llm_call(
            prompt=system_prompt + user_prompt,
            response=response_text,
            model=self.config.screening.model,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            action="query_generation",
        )

        try:
            clean = response_text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            return json.loads(clean)
        except json.JSONDecodeError:
            return {
                "report": response_text,
                "optimized_queries": {"wos": "", "scopus": ""},
                "recommendation": "Could not parse structured response.",
                "should_rerun": False,
            }

    def _write_prisma_s(
        self,
        path: Path,
        queries: dict,
        objectives: str,
        original_queries: str = "",
    ) -> None:
        """Generate PRISMA-S search strategy documentation."""
        content = f"""# Search strategy documentation (PRISMA-S)

## 1. Research objectives

{objectives}

## 2. Information sources

Databases searched: Web of Science Core Collection, Scopus

## 3. Original search queries

{original_queries if original_queries else "[No original queries documented]"}

## 4. Optimized search queries

"""
        if isinstance(queries, dict):
            for db, query in queries.items():
                if db == "original":
                    continue
                content += f"### {db.upper()}\n\n```\n{query}\n```\n\n"

        content += f"""## 5. Filters applied

- **Period**: {self.config.search.period_start}–{self.config.search.period_end}
- **Language**: {self.config.search.language}
- **Document types**: {', '.join(self.config.search.document_types)}

## 6. Search date

Date of search execution: [TO BE COMPLETED]

## 7. Search strategy validation

- Strategy reviewed by: [TO BE COMPLETED]
- Peer review of search strategy (PRESS): [TO BE COMPLETED]
- AI-assisted query analysis: Performed via biblio-review v0.1.0 (Claude API)

---
*Generated by biblio-review v0.1.0 on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*
"""
        path.write_text(content, encoding="utf-8")
