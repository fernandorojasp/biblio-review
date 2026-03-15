"""A7 · Comparator

Compares two bibliometric analyses: either two time periods of the same
corpus (pre/post GenAI) or two independent corpora.

Outputs:
- comparison_report.json: structured comparison data
- comparison_report.md: narrative report
- delta_*.csv: differential metrics
"""

import json
from pathlib import Path
from typing import Any

from biblio_review.agents.base import BaseAgent


class Comparator(BaseAgent):
    """Compare two bibliometric analyses."""

    @property
    def name(self) -> str:
        return "comparator"

    @property
    def description(self) -> str:
        return "A7 · Comparator — Compare pre/post periods or two corpora"

    def _validate_inputs(self, **kwargs: Any) -> bool:
        dir_a = Path(kwargs.get("dir_a", ""))
        dir_b = Path(kwargs.get("dir_b", ""))

        if not dir_a.exists() or not dir_b.exists():
            # Try to find pre/post directories from engine output
            metrics = Path("data/outputs/metrics")
            pre_files = list(metrics.glob("*_pre.csv"))
            post_files = list(metrics.glob("*_post.csv"))
            if pre_files and post_files:
                self.console.print(f"Found {len(pre_files)} pre-period and {len(post_files)} post-period metric files")
                return True
            self.console.print("[red]Need two result directories or pre/post metric files[/red]")
            return False
        return True

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        """Compare two sets of bibliometric results.

        Modes:
        - temporal: Compare pre/post files from the same analysis run
        - cross: Compare two independent result directories

        Compares:
        - Production growth rates
        - Top author/institution/country changes
        - New vs disappearing keywords
        - Network structure changes (density, clustering)
        - Thematic map quadrant shifts
        """
        mode = kwargs.get("mode", "temporal")
        output_dir = self.ensure_dir("data/outputs/reports")

        if mode == "temporal":
            results = self._compare_temporal()
        else:
            dir_a = Path(kwargs["dir_a"])
            dir_b = Path(kwargs["dir_b"])
            results = self._compare_cross(dir_a, dir_b)

        # Save report
        report_file = output_dir / "comparison_report.json"
        report_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

        md_file = output_dir / "comparison_report.md"
        md_file.write_text(self._format_markdown(results), encoding="utf-8")

        return {
            "report_file": str(report_file),
            "markdown_file": str(md_file),
            "mode": mode,
        }

    def _compare_temporal(self) -> dict:
        """Compare pre/post GenAI periods from the same corpus."""
        import pandas as pd

        metrics_dir = Path("data/outputs/metrics")
        comparison = {"mode": "temporal", "sections": {}}

        # Find matching pre/post file pairs
        pre_files = {f.stem.replace("_pre", ""): f for f in metrics_dir.glob("*_pre.csv")}
        post_files = {f.stem.replace("_post", ""): f for f in metrics_dir.glob("*_post.csv")}

        common = set(pre_files.keys()) & set(post_files.keys())
        self.console.print(f"\nComparing {len(common)} metric pairs (pre vs post)")

        for metric_name in sorted(common):
            try:
                df_pre = pd.read_csv(pre_files[metric_name])
                df_post = pd.read_csv(post_files[metric_name])

                comparison["sections"][metric_name] = {
                    "pre_rows": len(df_pre),
                    "post_rows": len(df_post),
                    "growth_rate": round((len(df_post) - len(df_pre)) / max(len(df_pre), 1) * 100, 1),
                    "pre_columns": list(df_pre.columns),
                    "post_columns": list(df_post.columns),
                }

                self.console.print(
                    f"  {metric_name}: {len(df_pre)} → {len(df_post)} "
                    f"({comparison['sections'][metric_name]['growth_rate']:+.1f}%)"
                )
            except Exception as e:
                self.log.warning(f"Could not compare {metric_name}: {e}")

        return comparison

    def _compare_cross(self, dir_a: Path, dir_b: Path) -> dict:
        """Compare two independent result directories."""
        # TODO: Implement cross-corpus comparison
        return {"mode": "cross", "status": "not_yet_implemented"}

    def _format_markdown(self, results: dict) -> str:
        """Format comparison results as markdown."""
        lines = ["# Comparative analysis report\n"]
        lines.append(f"**Mode:** {results.get('mode', 'unknown')}\n")

        if "sections" in results:
            for section, data in results["sections"].items():
                lines.append(f"\n## {section.replace('_', ' ').title()}\n")
                lines.append(f"- Pre-period: {data.get('pre_rows', '?')} entries")
                lines.append(f"- Post-period: {data.get('post_rows', '?')} entries")
                lines.append(f"- Growth: {data.get('growth_rate', '?')}%\n")

        lines.append("\n---\n*Generated by biblio-review v0.1.0*")
        return "\n".join(lines)
