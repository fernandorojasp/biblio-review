"""A4 · Screener

AI-assisted title/abstract screening using Anthropic API.
Proposes inclusion/exclusion criteria based on objectives, then screens
records in batches with checkpointing and human validation.

Outputs:
- corpus_screened.bib: included records only
- corpus_excluded.bib: excluded records
- screening_results.csv: full results with decisions and reasons
- exclusion_report.json: exclusion reason distribution
- validation_sample.csv: random sample for kappa calculation
"""

import json
import random
from pathlib import Path
from typing import Any

from biblio_review.agents.base import BaseAgent
from biblio_review.utils.batch import BatchConfig, BatchProcessor, BatchResult


class Screener(BaseAgent):
    """AI-assisted title/abstract screening with validation."""

    @property
    def name(self) -> str:
        return "screener"

    @property
    def description(self) -> str:
        return "A4 · Screener — AI-assisted title/abstract screening"

    def _validate_inputs(self, **kwargs: Any) -> bool:
        corpus_path = Path(kwargs.get("corpus", "data/processed/corpus.bib"))
        if not corpus_path.exists():
            self.console.print(f"[red]Corpus file not found: {corpus_path}[/red]")
            return False
        if not self.config.anthropic_api_key:
            self.console.print("[red]ANTHROPIC_API_KEY not set[/red]")
            return False
        return True

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        """Screen records using AI assistance.

        Flow:
        1. Load corpus
        2. Present criteria for user review (propose if not configured)
        3. Screen in batches via Anthropic API
        4. Generate validation sample
        5. Export results
        """
        corpus_path = Path(kwargs.get("corpus", "data/processed/corpus.bib"))
        output_dir = self.ensure_dir("data/processed")
        reports_dir = self.ensure_dir("data/outputs/reports")

        # Step 1: Load corpus
        records = self._load_corpus(corpus_path)
        self.console.print(f"\nLoaded {len(records)} records for screening")

        # Step 2: Review criteria
        ic = self.config.screening.inclusion_criteria
        ec = self.config.screening.exclusion_criteria
        edges = self.config.screening.edge_cases

        if not ic or not ec:
            self.console.print("[yellow]No screening criteria configured. Using defaults.[/yellow]")
            ic, ec, edges = self._propose_default_criteria()

        ic, ec, edges = self.present_criteria(ic, ec, edges)

        # Step 3: Screen in batches
        batch_processor = BatchProcessor(
            config=BatchConfig(
                max_records_per_batch=self.config.screening.batch_size,
                max_tokens_per_batch=80_000,
                retry_failed_batches=2,
            ),
            logger=self.log,
            checkpoint_dir=f"{self.config.checkpoint_dir}/screener_batches",
        )

        screening_prompt = self._build_screening_prompt(ic, ec, edges)

        all_results = batch_processor.process(
            records=records,
            process_fn=lambda batch, idx, total: self._screen_batch(
                batch, idx, total, screening_prompt
            ),
            merge_fn=self._merge_results,
            resume=True,
        )

        # Step 4: Generate validation sample
        sample_size = max(30, int(len(records) * self.config.screening.validation_sample_pct))
        validation_sample = random.sample(
            all_results, min(sample_size, len(all_results))
        )

        # Step 5: Export results
        results_data = self._export_results(
            all_results, records, output_dir, reports_dir, validation_sample
        )

        return results_data

    def _load_corpus(self, path: Path) -> list[dict]:
        """Load corpus records."""
        import bibtexparser

        with open(path, encoding="utf-8", errors="replace") as f:
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            library = bibtexparser.load(f, parser=parser)

        records = []
        for entry in library.entries:
            record = dict(entry)  # entry is already a dict in v1
            records.append(record)
        return records

    def _propose_default_criteria(self) -> tuple[list, list, list]:
        """Propose default screening criteria based on the thesis objectives."""
        ic = [
            {"id": "IC1", "description": "Studies integrating >=2 data modalities (e.g., image+text, image+signal, image+tabular)"},
            {"id": "IC2", "description": "Application to medical diagnosis in any clinical specialty"},
            {"id": "IC3", "description": "Published between January 2020 and December 2025"},
            {"id": "IC4", "description": "Published in English"},
            {"id": "IC5", "description": "Document types: original articles, review articles, or conference proceedings"},
            {"id": "IC6", "description": "Indexed in Web of Science Core Collection or Scopus"},
        ]
        ec = [
            {"id": "EC1", "description": "Unimodal AI systems (single data modality only)"},
            {"id": "EC2", "description": "Multimodal AI for non-diagnostic tasks: prognosis, treatment planning, drug discovery, clinical management"},
            {"id": "EC3", "description": "Grey literature, preprints, doctoral theses, technical reports"},
            {"id": "EC4", "description": "Publications in languages other than English"},
            {"id": "EC5", "description": "Studies with no abstract available"},
            {"id": "EC6", "description": "AI applied to non-medical data with only tangential medical references"},
            {"id": "EC7", "description": "Pure engineering papers proposing generic architectures without explicit medical application"},
        ]
        edges = [
            {"case": "Generative AI for synthetic medical data augmentation feeding diagnostic systems", "decision": "include"},
            {"case": "Radiology studies combining images + text reports", "decision": "include"},
            {"case": "Generic multimodal architecture without explicit medical application", "decision": "exclude"},
        ]
        return ic, ec, edges

    def _build_screening_prompt(
        self,
        ic: list[dict],
        ec: list[dict],
        edges: list[dict],
    ) -> str:
        """Build the system prompt for screening."""
        ic_text = "\n".join(f"- {c['id']}: {c['description']}" for c in ic)
        ec_text = "\n".join(f"- {c['id']}: {c['description']}" for c in ec)
        edge_text = "\n".join(f"- {c['case']} → {c['decision'].upper()}" for c in edges)

        return f"""You are a systematic review screener. Evaluate each record based on its title and abstract.

INCLUSION CRITERIA (ALL must be met):
{ic_text}

EXCLUSION CRITERIA (ANY triggers exclusion):
{ec_text}

EDGE CASES (apply these specific rules):
{edge_text}

For each record, respond with a JSON object:
{{
  "decision": "include" | "exclude" | "uncertain",
  "reason": "Brief justification (1-2 sentences)",
  "exclusion_code": "EC1" | "EC2" | ... | null (if excluded, which criterion)
}}

Be conservative: when in doubt, mark as "uncertain" rather than excluding.
Evaluate based ONLY on the title and abstract provided."""

    def _screen_batch(
        self,
        batch: list[dict],
        batch_index: int,
        total_batches: int,
        system_prompt: str,
    ) -> BatchResult:
        """Screen a batch of records via Anthropic API."""
        import anthropic

        client = anthropic.Anthropic(api_key=self.config.anthropic_api_key)

        # Build user message with records
        records_text = ""
        for i, rec in enumerate(batch):
            records_text += f"\n--- RECORD {i + 1} ---\n"
            records_text += f"Title: {rec.get('title', 'N/A')}\n"
            records_text += f"Abstract: {rec.get('abstract', 'N/A')}\n"
            records_text += f"Year: {rec.get('year', 'N/A')}\n"
            records_text += f"Type: {rec.get('type', 'N/A')}\n"

        user_message = f"""Screen the following {len(batch)} records.
Return a JSON array with one object per record, in the same order.

{records_text}

Respond ONLY with the JSON array, no other text."""

        response = client.messages.create(
            model=self.config.screening.model,
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = response.content[0].text

        # Log the LLM call
        self.log.log_llm_call(
            prompt=system_prompt + user_message,
            response=response_text,
            model=self.config.screening.model,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            action="screen_batch",
        )

        # Parse results
        try:
            # Strip markdown fences if present
            clean = response_text.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
            decisions = json.loads(clean)
        except json.JSONDecodeError:
            self.log.error(f"Failed to parse screening response for batch {batch_index}")
            decisions = [{"decision": "uncertain", "reason": "Parse error", "exclusion_code": None}] * len(batch)

        # Merge decisions with record metadata
        results = []
        for rec, dec in zip(batch, decisions):
            results.append({
                "bib_key": rec.get("bib_key", ""),
                "title": rec.get("title", ""),
                "year": rec.get("year", ""),
                "decision": dec.get("decision", "uncertain"),
                "reason": dec.get("reason", ""),
                "exclusion_code": dec.get("exclusion_code"),
            })

        return BatchResult(
            batch_index=batch_index,
            total_batches=total_batches,
            records_processed=len(batch),
            results=results,
        )

    def _merge_results(self, batch_results: list[BatchResult]) -> list[dict]:
        """Merge all batch results into a single list."""
        all_results = []
        for br in batch_results:
            all_results.extend(br.results)
        return all_results

    def _export_results(
        self,
        results: list[dict],
        original_records: list[dict],
        output_dir: Path,
        reports_dir: Path,
        validation_sample: list[dict],
    ) -> dict[str, Any]:
        """Export screening results in multiple formats."""
        import pandas as pd

        # Results CSV
        results_csv = reports_dir / "screening_results.csv"
        df = pd.DataFrame(results)
        df.to_csv(results_csv, index=False, encoding="utf-8-sig")

        # Counts
        from collections import Counter
        decision_counts = Counter(r["decision"] for r in results)
        exclusion_counts = Counter(
            r["exclusion_code"] for r in results
            if r["decision"] == "exclude" and r.get("exclusion_code")
        )

        # Exclusion report
        report = {
            "total_screened": len(results),
            "included": decision_counts.get("include", 0),
            "excluded": decision_counts.get("exclude", 0),
            "uncertain": decision_counts.get("uncertain", 0),
            "exclusion_by_criterion": dict(exclusion_counts.most_common()),
        }
        report_file = reports_dir / "exclusion_report.json"
        report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

        # Validation sample CSV
        val_csv = reports_dir / "validation_sample.csv"
        val_df = pd.DataFrame(validation_sample)
        val_df["human_decision"] = ""  # Empty column for manual classification
        val_df["human_exclusion_code"] = ""
        val_df.to_csv(val_csv, index=False, encoding="utf-8-sig")

        # TODO: Export included/excluded .bib files
        # This requires matching results back to original records

        self.console.print(f"\n[bold]Screening results:[/bold]")
        self.console.print(f"  Included:  {report['included']}")
        self.console.print(f"  Excluded:  {report['excluded']}")
        self.console.print(f"  Uncertain: {report['uncertain']}")
        self.console.print(f"\n  Validation sample: {len(validation_sample)} records saved to {val_csv}")

        return {
            "results_csv": str(results_csv),
            "report_file": str(report_file),
            "validation_sample": str(val_csv),
            "included": report["included"],
            "excluded": report["excluded"],
            "uncertain": report["uncertain"],
        }
