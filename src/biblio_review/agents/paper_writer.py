"""A6 · Paper Writer

Generates a journal-adapted manuscript draft from bibliometric results.
Each section is generated via Claude API with relevant metrics as context.
Produces a complete Markdown draft ready for editing.

Inputs:
- data/outputs/metrics/*.csv: computed bibliometric metrics
- data/outputs/viz/*.png: generated figures
- data/outputs/reports/: screening and audit reports
- docs/objectives.md: research objectives

Outputs:
- data/outputs/reports/paper_draft.md: complete manuscript draft
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from biblio_review.agents.base import BaseAgent


class PaperWriter(BaseAgent):
    """Generate journal-adapted manuscript drafts via LLM."""

    @property
    def name(self) -> str:
        return "paper_writer"

    @property
    def description(self) -> str:
        return "A6 · Paper writer — Generate journal-adapted manuscript draft"

    # Sections to generate, in order
    SECTIONS = [
        ("abstract", "Abstract"),
        ("introduction", "Introduction"),
        ("methods", "Methods"),
        ("results", "Results"),
        ("discussion", "Discussion"),
        ("conclusions", "Conclusions"),
    ]

    def _validate_inputs(self, **kwargs: Any) -> bool:
        metrics_dir = Path(kwargs.get("results", "data/outputs/metrics"))
        if not metrics_dir.exists() or not list(metrics_dir.glob("*.csv")):
            self.console.print("[red]No metrics files found. Run analysis first.[/red]")
            return False
        if not self.config.anthropic_api_key:
            self.console.print("[red]ANTHROPIC_API_KEY not set. Required for paper generation.[/red]")
            return False
        return True

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        """Generate manuscript draft section by section.

        Flow:
        1. Load all metrics, reports, and objectives
        2. Determine target journal
        3. Generate each section via LLM with relevant data
        4. Assemble into a single Markdown document
        5. Save draft
        """
        metrics_dir = Path(kwargs.get("results", "data/outputs/metrics"))
        viz_dir = Path(kwargs.get("viz", "data/outputs/viz"))
        reports_dir = Path("data/outputs/reports")
        output_dir = self.ensure_dir("data/outputs/reports")

        # Step 1: Journal selection
        journal = kwargs.get("journal", self.config.paper.target_journal)
        if not journal:
            journal = self.ask_text(
                "Target journal (e.g., 'Scientometrics', 'JMIR', 'npj Digital Medicine')",
                default="Scientometrics",
            )
        self.console.print(f"\nTarget journal: [bold]{journal}[/bold]")

        # Step 2: Load all context
        context = self._build_context(metrics_dir, viz_dir, reports_dir)
        self.console.print(f"Loaded context: {len(context['metrics'])} metrics, {len(context['figures'])} figures")

        # Step 3: Generate sections
        sections = {}
        for section_id, section_title in self.SECTIONS:
            self.console.print(f"\n[bold]Generating: {section_title}...[/bold]")
            section_text = self._generate_section(section_id, section_title, journal, context)
            sections[section_id] = section_text
            self.console.print(f"[green]  ✓ {section_title} ({len(section_text)} chars)[/green]")

        # Step 4: Assemble draft
        draft = self._assemble_draft(journal, sections, context)

        # Step 5: Save
        draft_path = output_dir / "paper_draft.md"
        draft_path.write_text(draft, encoding="utf-8")
        self.log.log_file_io(draft_path, "write")

        self.console.print(f"\n[green]✓ Draft saved: {draft_path} ({len(draft)} chars)[/green]")

        return {
            "draft_file": str(draft_path),
            "journal": journal,
            "sections": list(sections.keys()),
            "total_chars": len(draft),
        }

    def _build_context(self, metrics_dir: Path, viz_dir: Path, reports_dir: Path) -> dict:
        """Load all available data to provide as context to the LLM."""
        import pandas as pd

        context = {
            "metrics": {},
            "figures": [],
            "reports": {},
            "objectives": "",
            "screening": {},
            "corpus_stats": {},
        }

        # Load metrics (top rows of each CSV)
        for csv_file in sorted(metrics_dir.glob("*.csv")):
            try:
                df = pd.read_csv(csv_file)
                context["metrics"][csv_file.stem] = {
                    "columns": list(df.columns),
                    "rows": len(df),
                    "data": df.head(20).to_csv(index=False),
                }
            except Exception:
                pass

        # List available figures
        for png_file in sorted(viz_dir.glob("*.png")):
            context["figures"].append(png_file.stem)

        # Load reports
        for report_name in ["audit_report.json", "exclusion_report.json", "prisma_numbers.json", "dedup_report.json"]:
            report_path = reports_dir / report_name
            if not report_path.exists():
                report_path = Path("data/processed") / report_name
            if report_path.exists():
                try:
                    context["reports"][report_name] = json.loads(report_path.read_text(encoding="utf-8"))
                except Exception:
                    pass

        # Load objectives
        objectives_path = Path("docs/objectives.md")
        if objectives_path.exists():
            context["objectives"] = objectives_path.read_text(encoding="utf-8")

        # Load screening results summary
        screening_path = reports_dir / "exclusion_report.json"
        if screening_path.exists():
            try:
                context["screening"] = json.loads(screening_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        return context

    def _generate_section(
        self, section_id: str, section_title: str, journal: str, context: dict
    ) -> str:
        """Generate a single section via Claude API."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)

        system_prompt = f"""You are an expert academic writer specializing in bibliometric reviews for high-impact journals.
You are writing a paper for {journal}.
Write in formal academic English, third person, past tense for methods and results.
Be precise with numbers — always cite the exact values from the data provided.
Do not invent data or references. If data is missing, write [DATA NEEDED].
Use the structure and tone expected by {journal}.
Every claim must be supported by the data provided in the context."""

        # Build section-specific prompt with relevant data
        section_prompt = self._build_section_prompt(section_id, section_title, context)

        # Results and discussion need more space
        section_max_tokens = 8000 if section_id in ("results", "discussion") else 4000

        with self.log.timed(f"generate_{section_id}"):
            response = client.messages.create(
                model=self.config.screening.model,
                max_tokens=section_max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": section_prompt}],
            )

        text = response.content[0].text

        self.log.log_llm_call(
            prompt=system_prompt + section_prompt,
            response=text,
            model=self.config.screening.model,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            action=f"generate_{section_id}",
        )

        return text

    def _build_section_prompt(self, section_id: str, section_title: str, context: dict) -> str:
        """Build the prompt for a specific section with relevant data."""
        objectives = context.get("objectives", "[Objectives not loaded]")

        # Select relevant metrics for each section
        if section_id == "abstract":
            relevant = self._format_metrics(context, [
                "annual_production", "annual_production_pre", "annual_production_post",
            ])
            screening = json.dumps(context.get("screening", {}), indent=2)
            return f"""Write the ABSTRACT for this bibliometric review paper.

RESEARCH OBJECTIVES:
{objectives}

KEY DATA:
- Total corpus after screening: {context.get('screening', {}).get('included', '[DATA NEEDED]')} included articles
- Screening: {screening}
- Annual production data:
{relevant}

Available figures: {', '.join(context['figures'])}

Write a structured abstract (250-300 words) with: Background, Methods, Results, Conclusions.
Include key quantitative findings (total corpus size, growth rates, key periods)."""

        elif section_id == "introduction":
            return f"""Write the INTRODUCTION section for this bibliometric review paper.

RESEARCH OBJECTIVES:
{objectives}

The paper studies multimodal AI for medical diagnosis (2020-2025) with a pre/post GenAI comparison (cut at 2023).

Write 4-5 paragraphs covering:
1. Context: AI in medical diagnosis, evolution from unimodal to multimodal
2. The GenAI disruption: LLMs, VLMs, diffusion models entering medical diagnosis
3. Gap: need for a systematic bibliometric mapping of this transformation
4. Objectives and research questions (PI1-PI5)
5. Contribution of this study

Mark references as [REF] — they will be added later. Do not invent specific references."""

        elif section_id == "methods":
            dedup = json.dumps(context.get("reports", {}).get("dedup_report.json", {}), indent=2)
            screening = json.dumps(context.get("screening", {}), indent=2)
            audit = json.dumps(context.get("reports", {}).get("audit_report.json", {}).get("completeness", {}), indent=2)

            return f"""Write the METHODS section for this bibliometric review paper.

STUDY DATA:
- Databases: Web of Science Core Collection + Scopus
- Period: 2020-2025
- Search: three conceptual blocks (AI techniques AND multimodal processing AND medical diagnosis)
- Deduplication report: {dedup}
- Screening results: {screening}
- Corpus quality audit: {audit}
- Analysis software: Bibliometrix 5.2.1 for R, biblio-review pipeline v0.1.0
- Split analysis: pre-generative (2020-2022) vs post-generative (2023-2025)

INCLUSION CRITERIA: IC1 (>=2 modalities), IC2 (medical diagnosis), IC3 (2020-2025), IC4 (English), IC5 (articles/reviews/proceedings), IC6 (WoS/Scopus)
EXCLUSION CRITERIA: EC1 (unimodal), EC2 (non-diagnostic), EC3 (grey lit), EC4 (non-English), EC5 (no abstract), EC6 (tangential), EC7 (pure engineering)

ANALYSES PERFORMED:
1. Performance analysis (production, rankings, Bradford, Lotka)
2. Co-citation analysis (intellectual structure)
3. Co-authorship networks (social structure)
4. Keyword co-occurrence (conceptual structure)
5. Thematic map (Callon strategic diagram)
6. Thematic evolution

Write subsections: Study design, Search strategy, Inclusion/exclusion criteria, Data processing, Bibliometric techniques, Software and tools.
Follow PRISMA-ScR guidelines. Be precise with numbers."""

        elif section_id == "results":
            # Gather ALL key metrics — performance, thematic, and comparison data
            relevant_keys = [
                "annual_production", "annual_production_pre", "annual_production_post",
                "top_authors", "top_sources", "top_countries", "most_cited",
                "top_authors_pre", "top_authors_post",
                "top_sources_pre", "top_sources_post",
                "top_countries_pre", "top_countries_post",
                "most_cited_pre", "most_cited_post",
                "bradford", "bradford_pre", "bradford_post",
                "lotka", "lotka_pre", "lotka_post",
                "document_types", "document_types_pre", "document_types_post",
                "thematic_clusters", "thematic_clusters_pre", "thematic_clusters_post",
                "thematic_map_data", "thematic_map_data_pre", "thematic_map_data_post",
            ]
            relevant = self._format_metrics(context, relevant_keys)

            # For matrices, provide summary stats instead of raw data
            matrix_summaries = self._summarize_matrices(context)

            return f"""Write the RESULTS section for this bibliometric review paper.

METRICS DATA:
{relevant}

NETWORK ANALYSIS SUMMARIES:
{matrix_summaries}

Available figures: {', '.join(context['figures'])}

Write subsections:
3.1 Descriptive analysis and annual production (PI1) — cite exact numbers from annual_production, compare pre vs post growth
3.2 Most productive authors, sources, countries (PI2) — cite top 5 from each ranking, note changes between pre and post periods
3.3 Intellectual structure: co-citation analysis (PI3) — use the co-citation network summary to describe main clusters
3.4 Social structure: co-authorship networks (PI2) — use the co-authorship network summary to describe collaboration patterns
3.5 Conceptual structure: keyword co-occurrence and thematic maps (PI4) — use thematic_clusters and thematic_map_data to describe themes in each quadrant (motor, basic, niche, emerging/declining)
3.6 Pre/post GenAI comparison (PI1, PI4) — compare pre and post period data across all dimensions

Reference figures as (Figure N) and tables as (Table N).
Be precise: cite exact values from the data provided. Use ALL the data — every metric file contains real data that should be referenced."""

        elif section_id == "discussion":
            relevant = self._format_metrics(context, [
                "annual_production", "annual_production_pre", "annual_production_post",
                "top_countries", "top_countries_pre", "top_countries_post",
                "most_cited", "most_cited_pre", "most_cited_post",
                "thematic_clusters", "thematic_clusters_pre", "thematic_clusters_post",
                "thematic_map_data", "thematic_map_data_pre", "thematic_map_data_post",
            ])
            matrix_summaries = self._summarize_matrices(context)
            screening = json.dumps(context.get("screening", {}), indent=2)

            return f"""Write the DISCUSSION section for this bibliometric review paper.

KEY DATA:
{relevant}

NETWORK SUMMARIES:
{matrix_summaries}

SCREENING DATA:
{screening}

Write 5-6 paragraphs covering:
1. Summary of key findings — the GenAI inflection point (cite exact production numbers pre vs post)
2. Exponential growth pattern and what drives it (cite CAGR, key years)
3. Geographic and institutional implications — cite exact country rankings and shifts between periods
4. Thematic evolution: what changed post-2023 — use thematic_clusters data to identify emerging vs declining themes
5. Research gaps identified (PI5) — based on thematic map quadrants (niche and emerging/declining themes), underexplored modalities, clinical specialties with low representation
6. Limitations of this study (two databases only, English restriction, AI-assisted screening with kappa validation, temporal window may miss early preprints)

Be analytical, not just descriptive. Interpret the patterns using the actual data."""

        elif section_id == "conclusions":
            relevant = self._format_metrics(context, [
                "annual_production", "top_authors", "top_countries", "most_cited",
                "thematic_map_data",
            ])
            screening = json.dumps(context.get("screening", {}), indent=2)

            return f"""Write the CONCLUSIONS section for this bibliometric review paper.

RESEARCH OBJECTIVES:
{objectives}

KEY DATA SUMMARY:
{relevant}

SCREENING:
{screening}

Write 3-4 paragraphs covering:
1. Summary: answer EACH research question (PI1-PI5) in one sentence, citing specific data:
   - PI1: cite exact production numbers and growth rates from annual_production
   - PI2: cite top countries, authors, and journals from the rankings
   - PI3: cite the most cited papers and how they shifted between periods
   - PI4: cite specific themes that emerged vs declined from thematic_map_data
   - PI5: identify specific gaps based on the data
2. Theoretical contribution: first bibliometric map incorporating GenAI disruption analysis
3. Practical implications: for researchers, funders, and policy makers
4. Future research agenda: specific actionable lines of work derived from the gaps identified

Keep it concise (400-500 words). End with a forward-looking statement. Use real numbers from the data."""

        return f"Write the {section_title} section. [No specific context available]"

    def _summarize_matrices(self, context: dict) -> str:
        """Summarize network matrices for LLM context (too large to pass raw)."""
        import pandas as pd

        summaries = []
        matrix_keys = {
            "cocitation_matrix": "Co-citation network",
            "cocitation_matrix_pre": "Co-citation network (pre-GenAI)",
            "cocitation_matrix_post": "Co-citation network (post-GenAI)",
            "coauthorship_matrix": "Co-authorship network",
            "coauthorship_matrix_pre": "Co-authorship network (pre-GenAI)",
            "coauthorship_matrix_post": "Co-authorship network (post-GenAI)",
            "keyword_cooccurrence": "Keyword co-occurrence network",
            "keyword_cooccurrence_pre": "Keyword co-occurrence (pre-GenAI)",
            "keyword_cooccurrence_post": "Keyword co-occurrence (post-GenAI)",
        }

        for key, label in matrix_keys.items():
            if key in context["metrics"]:
                m = context["metrics"][key]
                n = m["rows"]
                # Extract top nodes from column/row names
                cols = m["columns"][:20] if m["columns"] else []
                summaries.append(f"### {label}\n- Nodes: {n}\n- Top entities: {', '.join(str(c) for c in cols[:10])}")

        return "\n\n".join(summaries) if summaries else "[No network data available]"

    def _format_metrics(self, context: dict, keys: list[str]) -> str:
        """Format selected metrics as text for the LLM prompt."""
        parts = []
        for key in keys:
            if key in context["metrics"]:
                m = context["metrics"][key]
                parts.append(f"\n### {key} ({m['rows']} rows)\n{m['data']}")
        return "\n".join(parts) if parts else "[No matching metrics found]"

    def _assemble_draft(self, journal: str, sections: dict[str, str], context: dict) -> str:
        """Assemble all sections into a complete Markdown document."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        figures = context.get("figures", [])

        header = f"""---
title: "Impact of generative AI on multimodal artificial intelligence research for medical diagnosis: a bibliometric review (2020–2025)"
journal: "{journal}"
date: "{now}"
status: "DRAFT — auto-generated by biblio-review v0.1.0"
---

# Impact of generative AI on multimodal artificial intelligence research for medical diagnosis: a bibliometric review (2020–2025)

**Target journal:** {journal}
**Generated:** {now}
**Status:** Draft — requires human review, reference completion, and figure integration

---

"""

        body = ""
        section_titles = {
            "abstract": "ABSTRACT",
            "introduction": "1. INTRODUCTION",
            "methods": "2. METHODS",
            "results": "3. RESULTS",
            "discussion": "4. DISCUSSION",
            "conclusions": "5. CONCLUSIONS",
        }

        for section_id, _ in self.SECTIONS:
            title = section_titles.get(section_id, section_id.upper())
            text = sections.get(section_id, "[Section not generated]")
            body += f"## {title}\n\n{text}\n\n---\n\n"

        # Add figure list
        if figures:
            body += "## FIGURES\n\n"
            for i, fig in enumerate(figures, 1):
                body += f"- Figure {i}: `data/outputs/viz/{fig}.png`\n"
            body += "\n---\n\n"

        # Add references placeholder
        body += """## REFERENCES

[References to be completed. All [REF] markers in the text need to be resolved with actual citations.]

---

*Auto-generated by biblio-review v0.1.0. This draft requires thorough human review before submission.*
"""

        return header + body
