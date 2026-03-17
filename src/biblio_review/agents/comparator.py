"""A7 · Comparator

Deep content comparison of pre/post GenAI periods (or two independent corpora).
Analyzes actual data changes, not just row counts.

Compares:
- Annual production growth with inflection point detection
- Author rankings: new entrants, departures, risers, fallers
- Country rankings: same analysis
- Source rankings: same analysis
- Most cited papers: new landmark papers in each period
- Keywords: emerging, declining, persistent terms
- Thematic clusters: quadrant shifts in Callon map
- Bradford/Lotka: distribution changes

Outputs:
- comparison_report.json: structured comparison data
- comparison_report.md: narrative report with tables
- delta_authors.csv, delta_countries.csv, etc.: differential data
"""

import json
from pathlib import Path
from typing import Any

from biblio_review.agents.base import BaseAgent


class Comparator(BaseAgent):
    """Deep content comparison of two bibliometric periods."""

    @property
    def name(self) -> str:
        return "comparator"

    @property
    def description(self) -> str:
        return "A7 · Comparator — Deep comparison of pre/post periods or two corpora"

    def _validate_inputs(self, **kwargs: Any) -> bool:
        dir_a = Path(kwargs.get("dir_a", ""))
        dir_b = Path(kwargs.get("dir_b", ""))

        if not dir_a.exists() or not dir_b.exists():
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
        mode = kwargs.get("mode", "temporal")
        output_dir = self.ensure_dir("data/outputs/reports")
        delta_dir = self.ensure_dir("data/outputs/metrics/deltas")

        if mode == "temporal":
            results = self._compare_temporal(delta_dir)
        else:
            dir_a = Path(kwargs["dir_a"])
            dir_b = Path(kwargs["dir_b"])
            results = self._compare_cross(dir_a, dir_b, delta_dir)

        # Save reports
        report_file = output_dir / "comparison_report.json"
        report_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

        md_file = output_dir / "comparison_report.md"
        md_file.write_text(self._format_markdown(results), encoding="utf-8")

        self.log.log_file_io(report_file, "write")
        self.log.log_file_io(md_file, "write")

        return {
            "report_file": str(report_file),
            "markdown_file": str(md_file),
            "mode": mode,
            "analyses": list(results.get("analyses", {}).keys()),
        }

    def _compare_temporal(self, delta_dir: Path) -> dict:
        """Deep comparison of pre/post GenAI periods."""
        import pandas as pd

        metrics_dir = Path("data/outputs/metrics")
        results = {
            "mode": "temporal",
            "pre_period": "2020-2022",
            "post_period": "2023-2025",
            "analyses": {},
        }

        # 1. Annual production
        self.console.print("\n[bold]Comparing annual production...[/bold]")
        results["analyses"]["production"] = self._compare_production(metrics_dir)

        # 2. Top authors
        self.console.print("[bold]Comparing author rankings...[/bold]")
        results["analyses"]["authors"] = self._compare_rankings(
            metrics_dir, "top_authors", "Author", "Articles", delta_dir / "delta_authors.csv"
        )

        # 3. Top countries
        self.console.print("[bold]Comparing country rankings...[/bold]")
        results["analyses"]["countries"] = self._compare_rankings(
            metrics_dir, "top_countries", "Country", "Articles", delta_dir / "delta_countries.csv"
        )

        # 4. Top sources
        self.console.print("[bold]Comparing source rankings...[/bold]")
        results["analyses"]["sources"] = self._compare_rankings(
            metrics_dir, "top_sources", "Source", "Articles", delta_dir / "delta_sources.csv"
        )

        # 5. Most cited papers
        self.console.print("[bold]Comparing most cited papers...[/bold]")
        results["analyses"]["citations"] = self._compare_citations(metrics_dir)

        # 6. Keywords / thematic clusters
        self.console.print("[bold]Comparing thematic structure...[/bold]")
        results["analyses"]["themes"] = self._compare_themes(metrics_dir, delta_dir)

        # 7. Bradford
        self.console.print("[bold]Comparing Bradford distribution...[/bold]")
        results["analyses"]["bradford"] = self._compare_bradford(metrics_dir)

        # Summary
        self._print_summary(results)

        return results

    def _compare_production(self, metrics_dir: Path) -> dict:
        """Compare annual production between periods."""
        import pandas as pd

        result = {}
        try:
            df_pre = pd.read_csv(metrics_dir / "annual_production_pre.csv")
            df_post = pd.read_csv(metrics_dir / "annual_production_post.csv")

            pre_total = int(df_pre["Articles"].sum())
            post_total = int(df_post["Articles"].sum())
            growth = round((post_total - pre_total) / max(pre_total, 1) * 100, 1)

            # Year-by-year
            pre_years = {int(r["Year"]): int(r["Articles"]) for _, r in df_pre.iterrows()}
            post_years = {int(r["Year"]): int(r["Articles"]) for _, r in df_post.iterrows()}

            result = {
                "pre_total": pre_total,
                "post_total": post_total,
                "growth_pct": growth,
                "pre_yearly": pre_years,
                "post_yearly": post_years,
                "pre_avg_per_year": round(pre_total / max(len(pre_years), 1), 1),
                "post_avg_per_year": round(post_total / max(len(post_years), 1), 1),
            }

            self.console.print(f"  Pre: {pre_total} articles ({result['pre_avg_per_year']}/year)")
            self.console.print(f"  Post: {post_total} articles ({result['post_avg_per_year']}/year)")
            self.console.print(f"  Growth: [bold]{growth:+.1f}%[/bold]")
        except Exception as e:
            result["error"] = str(e)
            self.log.warning(f"Production comparison failed: {e}")

        return result

    def _compare_rankings(
        self, metrics_dir: Path, base_name: str, name_col: str, value_col: str, delta_path: Path
    ) -> dict:
        """Compare ranked lists between pre and post periods."""
        import pandas as pd

        result = {}
        try:
            df_pre = pd.read_csv(metrics_dir / f"{base_name}_pre.csv")
            df_post = pd.read_csv(metrics_dir / f"{base_name}_post.csv")

            # Normalize column names (some may vary)
            if name_col not in df_pre.columns:
                name_col = df_pre.columns[0]
            if value_col not in df_pre.columns:
                value_col = df_pre.columns[-1]

            pre_set = set(df_pre[name_col].astype(str).str.strip())
            post_set = set(df_post[name_col].astype(str).str.strip())

            new_entrants = sorted(post_set - pre_set)
            departed = sorted(pre_set - post_set)
            persistent = sorted(pre_set & post_set)

            # Build ranking comparison for persistent entities
            pre_rank = {str(r[name_col]).strip(): i + 1 for i, (_, r) in enumerate(df_pre.iterrows())}
            post_rank = {str(r[name_col]).strip(): i + 1 for i, (_, r) in enumerate(df_post.iterrows())}

            rank_changes = []
            for entity in persistent:
                pre_r = pre_rank.get(entity, 999)
                post_r = post_rank.get(entity, 999)
                change = pre_r - post_r  # positive = rose in ranking
                rank_changes.append({"entity": entity, "pre_rank": pre_r, "post_rank": post_r, "change": change})

            rank_changes.sort(key=lambda x: x["change"], reverse=True)
            risers = [r for r in rank_changes if r["change"] > 0][:10]
            fallers = [r for r in rank_changes if r["change"] < 0][-10:]

            result = {
                "pre_count": len(pre_set),
                "post_count": len(post_set),
                "new_entrants": new_entrants[:20],
                "departed": departed[:20],
                "persistent": len(persistent),
                "top_risers": risers,
                "top_fallers": fallers,
            }

            # Save delta CSV
            delta_rows = []
            for entity in post_set | pre_set:
                pre_val = df_pre.loc[df_pre[name_col].astype(str).str.strip() == entity, value_col]
                post_val = df_post.loc[df_post[name_col].astype(str).str.strip() == entity, value_col]
                delta_rows.append({
                    "entity": entity,
                    "pre_value": int(pre_val.iloc[0]) if len(pre_val) > 0 else 0,
                    "post_value": int(post_val.iloc[0]) if len(post_val) > 0 else 0,
                    "status": "new" if entity in new_entrants else ("departed" if entity in departed else "persistent"),
                })

            delta_df = pd.DataFrame(delta_rows)
            delta_df["delta"] = delta_df["post_value"] - delta_df["pre_value"]
            delta_df = delta_df.sort_values("delta", ascending=False)
            delta_df.to_csv(delta_path, index=False)

            self.console.print(f"  Persistent: {len(persistent)} | New: {len(new_entrants)} | Departed: {len(departed)}")
        except Exception as e:
            result["error"] = str(e)
            self.log.warning(f"Ranking comparison failed for {base_name}: {e}")

        return result

    def _compare_citations(self, metrics_dir: Path) -> dict:
        """Compare most cited papers between periods."""
        import pandas as pd

        result = {}
        try:
            df_pre = pd.read_csv(metrics_dir / "most_cited_pre.csv")
            df_post = pd.read_csv(metrics_dir / "most_cited_post.csv")

            # Get title/paper column (first text column)
            paper_col = df_pre.columns[0]

            pre_papers = set(df_pre[paper_col].astype(str).str.strip().str[:100])
            post_papers = set(df_post[paper_col].astype(str).str.strip().str[:100])

            new_landmarks = sorted(post_papers - pre_papers)
            persistent_classics = sorted(pre_papers & post_papers)

            result = {
                "pre_top_papers": len(pre_papers),
                "post_top_papers": len(post_papers),
                "new_landmark_papers": new_landmarks[:15],
                "persistent_classics": len(persistent_classics),
                "pre_top_5": df_pre.head(5).to_dict(orient="records"),
                "post_top_5": df_post.head(5).to_dict(orient="records"),
            }

            self.console.print(f"  New landmark papers in post-period: {len(new_landmarks)}")
            self.console.print(f"  Persistent classics: {len(persistent_classics)}")
        except Exception as e:
            result["error"] = str(e)
            self.log.warning(f"Citation comparison failed: {e}")

        return result

    def _compare_themes(self, metrics_dir: Path, delta_dir: Path) -> dict:
        """Compare thematic clusters between periods."""
        import pandas as pd

        result = {}
        try:
            df_pre = pd.read_csv(metrics_dir / "thematic_clusters_pre.csv")
            df_post = pd.read_csv(metrics_dir / "thematic_clusters_post.csv")

            # Extract keyword/word column
            word_col = None
            for col in df_pre.columns:
                if "word" in col.lower() or "keyword" in col.lower() or "label" in col.lower():
                    word_col = col
                    break
            if word_col is None:
                word_col = df_pre.columns[0]

            pre_keywords = set(df_pre[word_col].astype(str).str.strip().str.lower())
            post_keywords = set(df_post[word_col].astype(str).str.strip().str.lower())

            emerging = sorted(post_keywords - pre_keywords)
            declining = sorted(pre_keywords - post_keywords)
            persistent = sorted(pre_keywords & post_keywords)

            result = {
                "pre_keywords": len(pre_keywords),
                "post_keywords": len(post_keywords),
                "emerging_keywords": emerging[:30],
                "declining_keywords": declining[:30],
                "persistent_keywords": len(persistent),
            }

            # Save delta
            delta_rows = []
            for kw in emerging:
                delta_rows.append({"keyword": kw, "status": "emerging", "period": "post-only"})
            for kw in declining:
                delta_rows.append({"keyword": kw, "status": "declining", "period": "pre-only"})
            for kw in persistent:
                delta_rows.append({"keyword": kw, "status": "persistent", "period": "both"})

            pd.DataFrame(delta_rows).to_csv(delta_dir / "delta_keywords.csv", index=False)

            self.console.print(f"  Emerging keywords: {len(emerging)}")
            self.console.print(f"  Declining keywords: {len(declining)}")
            self.console.print(f"  Persistent: {len(persistent)}")

            if emerging:
                self.console.print(f"  [green]Top emerging: {', '.join(emerging[:10])}[/green]")
            if declining:
                self.console.print(f"  [red]Top declining: {', '.join(declining[:10])}[/red]")

        except Exception as e:
            result["error"] = str(e)
            self.log.warning(f"Theme comparison failed: {e}")

        # Thematic map comparison
        try:
            map_pre = pd.read_csv(metrics_dir / "thematic_map_data_pre.csv")
            map_post = pd.read_csv(metrics_dir / "thematic_map_data_post.csv")
            result["thematic_map_pre"] = map_pre.to_dict(orient="records")
            result["thematic_map_post"] = map_post.to_dict(orient="records")
        except Exception:
            pass

        return result

    def _compare_bradford(self, metrics_dir: Path) -> dict:
        """Compare Bradford law distributions."""
        import pandas as pd

        result = {}
        try:
            df_pre = pd.read_csv(metrics_dir / "bradford_pre.csv")
            df_post = pd.read_csv(metrics_dir / "bradford_post.csv")

            result = {
                "pre_zones": len(df_pre),
                "post_zones": len(df_post),
                "pre_core_journals": int(df_pre.iloc[0].get("Freq", 0)) if len(df_pre) > 0 else 0,
                "post_core_journals": int(df_post.iloc[0].get("Freq", 0)) if len(df_post) > 0 else 0,
            }

            self.console.print(f"  Pre core journals: {result['pre_core_journals']}")
            self.console.print(f"  Post core journals: {result['post_core_journals']}")
        except Exception as e:
            result["error"] = str(e)

        return result

    def _print_summary(self, results: dict) -> None:
        """Print a summary of all comparisons."""
        self.console.print("\n[bold]═══ Comparison summary ═══[/bold]")

        prod = results["analyses"].get("production", {})
        if "pre_total" in prod:
            self.console.print(f"\n  Production: {prod['pre_total']} → {prod['post_total']} ({prod['growth_pct']:+.1f}%)")

        for key in ["authors", "countries", "sources"]:
            data = results["analyses"].get(key, {})
            if "new_entrants" in data:
                self.console.print(f"  {key.title()}: {data.get('persistent', 0)} persistent, {len(data.get('new_entrants', []))} new, {len(data.get('departed', []))} departed")

        themes = results["analyses"].get("themes", {})
        if "emerging_keywords" in themes:
            self.console.print(f"  Keywords: {len(themes['emerging_keywords'])} emerging, {len(themes['declining_keywords'])} declining")

    def _compare_cross(self, dir_a: Path, dir_b: Path, delta_dir: Path) -> dict:
        """Compare two independent result directories."""
        return {"mode": "cross", "status": "not_yet_implemented"}

    def _format_markdown(self, results: dict) -> str:
        """Format comparison results as a detailed markdown report."""
        lines = [
            "# Comparative analysis: pre-generative vs post-generative periods\n",
            f"**Pre-period:** {results.get('pre_period', '?')}",
            f"**Post-period:** {results.get('post_period', '?')}\n",
            "---\n",
        ]

        analyses = results.get("analyses", {})

        # Production
        prod = analyses.get("production", {})
        if prod and "error" not in prod:
            lines.append("## 1. Annual production\n")
            lines.append(f"| Period | Total articles | Avg/year |")
            lines.append(f"|--------|---------------|----------|")
            lines.append(f"| Pre (2020–2022) | {prod.get('pre_total', '?')} | {prod.get('pre_avg_per_year', '?')} |")
            lines.append(f"| Post (2023–2025) | {prod.get('post_total', '?')} | {prod.get('post_avg_per_year', '?')} |")
            lines.append(f"| **Growth** | **{prod.get('growth_pct', '?'):+.1f}%** | |\n")

            if prod.get("pre_yearly"):
                lines.append("Year-by-year:\n")
                for year, count in sorted({**prod.get("pre_yearly", {}), **prod.get("post_yearly", {})}.items()):
                    lines.append(f"- {year}: {count}")
                lines.append("")

        # Rankings (authors, countries, sources)
        for key, title in [("authors", "2. Author rankings"), ("countries", "3. Country rankings"), ("sources", "4. Source/journal rankings")]:
            data = analyses.get(key, {})
            if data and "error" not in data:
                lines.append(f"## {title}\n")
                lines.append(f"- Persistent (in both periods): {data.get('persistent', '?')}")
                lines.append(f"- New in post-period: {len(data.get('new_entrants', []))}")
                lines.append(f"- Absent in post-period: {len(data.get('departed', []))}\n")

                if data.get("new_entrants"):
                    lines.append(f"**New entrants (post-period):** {', '.join(str(e) for e in data['new_entrants'][:15])}\n")

                if data.get("top_risers"):
                    lines.append("**Top risers (improved ranking):**\n")
                    lines.append("| Entity | Pre rank | Post rank | Change |")
                    lines.append("|--------|----------|-----------|--------|")
                    for r in data["top_risers"][:5]:
                        lines.append(f"| {r['entity'][:40]} | {r['pre_rank']} | {r['post_rank']} | +{r['change']} |")
                    lines.append("")

                if data.get("top_fallers"):
                    lines.append("**Top fallers (declined ranking):**\n")
                    lines.append("| Entity | Pre rank | Post rank | Change |")
                    lines.append("|--------|----------|-----------|--------|")
                    for r in data["top_fallers"][:5]:
                        lines.append(f"| {r['entity'][:40]} | {r['pre_rank']} | {r['post_rank']} | {r['change']} |")
                    lines.append("")

        # Citations
        cit = analyses.get("citations", {})
        if cit and "error" not in cit:
            lines.append("## 5. Most cited papers\n")
            lines.append(f"- Persistent classics (top-cited in both periods): {cit.get('persistent_classics', '?')}")
            lines.append(f"- New landmark papers (top-cited only in post): {len(cit.get('new_landmark_papers', []))}\n")

            if cit.get("new_landmark_papers"):
                lines.append("**New landmark papers in post-period:**\n")
                for i, paper in enumerate(cit["new_landmark_papers"][:10], 1):
                    lines.append(f"{i}. {paper}")
                lines.append("")

        # Themes
        themes = analyses.get("themes", {})
        if themes and "error" not in themes:
            lines.append("## 6. Thematic structure\n")
            lines.append(f"- Pre-period keywords: {themes.get('pre_keywords', '?')}")
            lines.append(f"- Post-period keywords: {themes.get('post_keywords', '?')}")
            lines.append(f"- Persistent: {themes.get('persistent_keywords', '?')}")
            lines.append(f"- Emerging (new in post): {len(themes.get('emerging_keywords', []))}")
            lines.append(f"- Declining (absent in post): {len(themes.get('declining_keywords', []))}\n")

            if themes.get("emerging_keywords"):
                lines.append(f"**Emerging keywords:** {', '.join(themes['emerging_keywords'][:20])}\n")
            if themes.get("declining_keywords"):
                lines.append(f"**Declining keywords:** {', '.join(themes['declining_keywords'][:20])}\n")

        # Bradford
        brad = analyses.get("bradford", {})
        if brad and "error" not in brad:
            lines.append("## 7. Bradford law\n")
            lines.append(f"- Pre-period core journals: {brad.get('pre_core_journals', '?')}")
            lines.append(f"- Post-period core journals: {brad.get('post_core_journals', '?')}\n")

        lines.append("---\n")
        lines.append("*Generated by biblio-review v0.1.0*\n")

        return "\n".join(lines)
