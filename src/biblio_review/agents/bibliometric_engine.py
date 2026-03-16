"""A5 · Bibliometric Engine

Orchestrates R/Bibliometrix for validated bibliometric calculations.
Generates R scripts from templates, executes them via subprocess,
and captures results as CSV/JSON for downstream processing.

Sub-agents:
- 5a: Performance analysis (production, rankings, Bradford, Lotka)
- 5b: Co-citation analysis (references, authors, clustering)
- 5c: Co-authorship analysis (networks, centrality, communities)
- 5d: Keyword/thematic analysis (co-occurrence, Callon map, evolution)
- 5e: Visualization engine (network maps, charts, 300dpi export)

Outputs:
- data/outputs/metrics/*.csv: all computed metrics
- data/outputs/viz/*.png: publication-ready figures
- data/outputs/viz/*.html: interactive visualizations
"""

import json
import subprocess
from pathlib import Path
from typing import Any

from biblio_review.agents.base import BaseAgent


class BibliometricEngine(BaseAgent):
    """Orchestrate R/Bibliometrix for bibliometric analysis."""

    @property
    def name(self) -> str:
        return "bibliometric_engine"

    @property
    def description(self) -> str:
        return "A5 · Bibliometric engine — Run bibliometric analyses via R/Bibliometrix"

    # Sub-analyses that can be run independently
    ANALYSES = {
        "performance": "5a · Performance analysis (production, rankings, laws)",
        "co_citation": "5b · Co-citation analysis (intellectual structure)",
        "co_authorship": "5c · Co-authorship networks (social structure)",
        "keyword_cooccurrence": "5d · Keyword co-occurrence (conceptual structure)",
        "thematic_map": "5d · Thematic map (Callon strategic diagram)",
        "thematic_evolution": "5d · Thematic evolution analysis",
    }

    def _validate_inputs(self, **kwargs: Any) -> bool:
        # Check corpus exists
        corpus = Path(kwargs.get("corpus", "data/processed/corpus_screened.bib"))
        if not corpus.exists():
            # Fall back to unscreened corpus
            corpus = Path("data/processed/corpus.bib")
            if not corpus.exists():
                self.console.print("[red]No corpus file found[/red]")
                return False

        # Check R is available
        if not self._check_r_available():
            return False

        # Check Bibliometrix is installed
        if not self._check_bibliometrix():
            return False

        return True

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        """Run bibliometric analyses.

        Flow:
        1. Determine which analyses to run
        2. For each analysis: generate R script → execute → capture results
        3. If split_period: run each analysis for both sub-periods
        4. Compile all results
        """
        corpus = kwargs.get("corpus", "data/processed/corpus_screened.bib")
        if not Path(corpus).exists():
            corpus = "data/processed/corpus.bib"

        metrics_dir = self.ensure_dir("data/outputs/metrics")
        viz_dir = self.ensure_dir("data/outputs/viz")
        scripts_dir = self.ensure_dir("data/outputs/r_scripts")

        analyses = kwargs.get("analyses", self.config.analysis.analyses)
        split = kwargs.get("split", self.config.analysis.split_period)
        split_year = kwargs.get("split_year", self.config.analysis.split_year)

        results = {}

        # Run each analysis
        for analysis in analyses:
            if analysis not in self.ANALYSES:
                self.log.warning(f"Unknown analysis: {analysis}")
                continue

            self.console.print(f"\n[bold]Running {self.ANALYSES[analysis]}...[/bold]")

            # Full corpus analysis
            r_script = self._generate_r_script(analysis, corpus, metrics_dir, viz_dir, period="full")
            script_path = scripts_dir / f"{analysis}_full.R"
            script_path.write_text(r_script, encoding="utf-8")

            result = self._execute_r_script(script_path)
            results[f"{analysis}_full"] = result

            # Split period analysis
            if split:
                for period_label, year_range in [
                    ("pre", (self.config.search.period_start, split_year - 1)),
                    ("post", (split_year, self.config.search.period_end)),
                ]:
                    r_script = self._generate_r_script(
                        analysis, corpus, metrics_dir, viz_dir,
                        period=period_label, year_range=year_range,
                    )
                    script_path = scripts_dir / f"{analysis}_{period_label}.R"
                    script_path.write_text(r_script, encoding="utf-8")

                    result = self._execute_r_script(script_path)
                    results[f"{analysis}_{period_label}"] = result

        return {
            "metrics_dir": str(metrics_dir),
            "viz_dir": str(viz_dir),
            "scripts_dir": str(scripts_dir),
            "analyses_run": list(results.keys()),
            "results_summary": {k: v.get("status", "unknown") for k, v in results.items()},
        }

    def _check_r_available(self) -> bool:
        """Check if R/Rscript is available."""
        try:
            result = subprocess.run(
                [self.config.analysis.r_executable, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                version = result.stdout.split("\n")[0] if result.stdout else result.stderr.split("\n")[0]
                self.console.print(f"  [green]✓ R found: {version}[/green]")
                return True
        except FileNotFoundError:
            pass
        self.console.print("[red]R/Rscript not found. Install R and add to PATH.[/red]")
        return False

    def _check_bibliometrix(self) -> bool:
        """Check if bibliometrix R package is installed."""
        check_script = 'cat(as.character(packageVersion("bibliometrix")))'
	try:
            result = subprocess.run(
                [self.config.analysis.r_executable, "-e", check_script],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                self.console.print(f"  [green]✓ bibliometrix {version}[/green]")
                return True
        except Exception:
            pass

        self.console.print("[red]bibliometrix R package not found.[/red]")
        self.console.print('[dim]Install with: Rscript -e \'install.packages("bibliometrix")\'[/dim]')
        return False

    def _generate_r_script(
        self,
        analysis: str,
        corpus_path: str,
        metrics_dir: Path,
        viz_dir: Path,
        period: str = "full",
        year_range: tuple[int, int] | None = None,
    ) -> str:
        """Generate an R script for a specific analysis.

        Each script follows the same structure:
        1. Load libraries
        2. Read corpus with convert2df()
        3. Filter by period if needed
        4. Run analysis
        5. Export results as CSV
        6. Generate and save plots
        """
        suffix = f"_{period}" if period != "full" else ""
        filter_code = ""
        if year_range:
            filter_code = f"""
# Filter to period: {year_range[0]}-{year_range[1]}
M <- M[M$PY >= {year_range[0]} & M$PY <= {year_range[1]}, ]
cat(paste("Records after filtering:", nrow(M), "\\n"))
"""

        # Base script template
        header = f"""# Auto-generated by biblio-review v0.1.0
# Analysis: {analysis} | Period: {period}
# DO NOT EDIT — regenerate with: biblio-review analyze

library(bibliometrix)

# Load corpus
corpus_path <- "{corpus_path}"
file_ext <- tools::file_ext(corpus_path)

if (file_ext == "bib") {{
  M <- convert2df(corpus_path, dbsource = "generic", format = "bibtex")
}} else if (file_ext == "ris") {{
  M <- convert2df(corpus_path, dbsource = "generic", format = "endnote")
}} else {{
  stop(paste("Unsupported format:", file_ext))
}}

cat(paste("Total records loaded:", nrow(M), "\\n"))
{filter_code}
"""

        # Analysis-specific code
        body = self._get_analysis_code(analysis, metrics_dir, viz_dir, suffix)

        return header + body

    def _get_analysis_code(self, analysis: str, metrics_dir: Path, viz_dir: Path, suffix: str) -> str:
        """Get R code for a specific analysis type."""

        if analysis == "performance":
            return f"""
# ── Performance analysis ──────────────────────────────
results <- biblioAnalysis(M, sep = ";")
S <- summary(results, k = 20, pause = FALSE)

# Annual production
annual <- data.frame(Year = results$Years, Articles = results$nAU)  # placeholder
write.csv(data.frame(results$AnnualProduction), "{metrics_dir}/annual_production{suffix}.csv", row.names = FALSE)

# Most productive authors
write.csv(data.frame(results$Authors), "{metrics_dir}/top_authors{suffix}.csv", row.names = FALSE)

# Most productive sources
write.csv(data.frame(results$Sources), "{metrics_dir}/top_sources{suffix}.csv", row.names = FALSE)

# Most productive countries
write.csv(data.frame(results$Countries), "{metrics_dir}/top_countries{suffix}.csv", row.names = FALSE)

# Most cited documents
write.csv(data.frame(results$MostCitedPapers), "{metrics_dir}/most_cited{suffix}.csv", row.names = FALSE)

# Bradford's law
bradford_results <- bradford(M)
write.csv(bradford_results$table, "{metrics_dir}/bradford{suffix}.csv", row.names = FALSE)

# Lotka's law
lotka_results <- lotka(results)
write.csv(data.frame(
  Authors = lotka_results$AuthorProd$N.of.Authors,
  Articles = lotka_results$AuthorProd$Freq
), "{metrics_dir}/lotka{suffix}.csv", row.names = FALSE)

# Save plots
png("{viz_dir}/annual_production{suffix}.png", width = 2400, height = 1600, res = {self.config.analysis.viz_dpi})
plot(x = results, k = 20)
dev.off()

cat("Performance analysis complete\\n")
"""

        elif analysis == "co_citation":
            return f"""
# ── Co-citation analysis ──────────────────────────────
# Reference co-citation network
NetMatrix <- biblioNetwork(M, analysis = "co-citation", network = "references", sep = ";")

# Clustering
net <- networkPlot(NetMatrix, n = 50, type = "auto", Title = "Co-Citation Network",
                   size = TRUE, remove.multiple = TRUE, labelsize = 0.7, edgesize = 3)

# Export adjacency matrix
write.csv(as.matrix(NetMatrix[1:min(200, nrow(NetMatrix)), 1:min(200, ncol(NetMatrix))]),
          "{metrics_dir}/cocitation_matrix{suffix}.csv")

# Save network plot
png("{viz_dir}/cocitation_network{suffix}.png", width = 3000, height = 3000, res = {self.config.analysis.viz_dpi})
networkPlot(NetMatrix, n = 50, type = "auto", Title = "Co-Citation Network{suffix}",
            size = TRUE, remove.multiple = TRUE, labelsize = 0.7, edgesize = 3)
dev.off()

cat("Co-citation analysis complete\\n")
"""

        elif analysis == "co_authorship":
            return f"""
# ── Co-authorship analysis ────────────────────────────
# Author collaboration network
NetMatrix <- biblioNetwork(M, analysis = "collaboration", network = "authors", sep = ";")

net <- networkPlot(NetMatrix, n = 50, type = "auto", Title = "Author Collaboration",
                   size = TRUE, remove.multiple = TRUE, labelsize = 0.7)

# Country collaboration
NetCountry <- biblioNetwork(M, analysis = "collaboration", network = "countries", sep = ";")

# Export metrics
write.csv(as.matrix(NetMatrix[1:min(100, nrow(NetMatrix)), 1:min(100, ncol(NetMatrix))]),
          "{metrics_dir}/coauthorship_matrix{suffix}.csv")

# Save plots
png("{viz_dir}/coauthorship_network{suffix}.png", width = 3000, height = 3000, res = {self.config.analysis.viz_dpi})
networkPlot(NetMatrix, n = 50, type = "auto", Title = "Author Collaboration{suffix}",
            size = TRUE, remove.multiple = TRUE, labelsize = 0.7)
dev.off()

png("{viz_dir}/country_collaboration{suffix}.png", width = 3000, height = 2000, res = {self.config.analysis.viz_dpi})
networkPlot(NetCountry, n = 30, type = "auto", Title = "Country Collaboration{suffix}",
            size = TRUE, remove.multiple = TRUE, labelsize = 0.8)
dev.off()

cat("Co-authorship analysis complete\\n")
"""

        elif analysis == "keyword_cooccurrence":
            return f"""
# ── Keyword co-occurrence ─────────────────────────────
NetMatrix <- biblioNetwork(M, analysis = "co-occurrences", network = "author_keywords", sep = ";")

net <- networkPlot(NetMatrix, n = 50, type = "auto", Title = "Keyword Co-occurrence",
                   size = TRUE, remove.multiple = TRUE, labelsize = 0.7, edgesize = 3)

write.csv(as.matrix(NetMatrix[1:min(100, nrow(NetMatrix)), 1:min(100, ncol(NetMatrix))]),
          "{metrics_dir}/keyword_cooccurrence{suffix}.csv")

png("{viz_dir}/keyword_network{suffix}.png", width = 3000, height = 3000, res = {self.config.analysis.viz_dpi})
networkPlot(NetMatrix, n = 50, type = "auto", Title = "Keyword Co-occurrence{suffix}",
            size = TRUE, remove.multiple = TRUE, labelsize = 0.7, edgesize = 3)
dev.off()

cat("Keyword co-occurrence analysis complete\\n")
"""

        elif analysis == "thematic_map":
            return f"""
# ── Thematic map (Callon strategic diagram) ───────────
Map <- thematicMap(M, field = "DE", n = 250, minfreq = {self.config.analysis.min_keyword_frequency},
                   stemming = FALSE, size = 0.5, repel = TRUE)

# Export cluster data
write.csv(Map$words, "{metrics_dir}/thematic_clusters{suffix}.csv", row.names = FALSE)
write.csv(Map$clusters, "{metrics_dir}/thematic_map_data{suffix}.csv", row.names = FALSE)

png("{viz_dir}/thematic_map{suffix}.png", width = 3000, height = 2400, res = {self.config.analysis.viz_dpi})
plot(Map$map)
dev.off()

cat("Thematic map analysis complete\\n")
"""

        elif analysis == "thematic_evolution":
            return f"""
# ── Thematic evolution analysis ───────────────────────
years <- sort(unique(M$PY))
n_slices <- min(3, length(unique(M$PY)))
cutting_points <- quantile(years, probs = seq(0, 1, length.out = n_slices + 1))
cutting_points <- unique(round(cutting_points))

if (length(cutting_points) >= 3) {{
  nexus <- thematicEvolution(M, field = "DE", years = cutting_points,
                             n = 200, minfreq = {self.config.analysis.min_keyword_frequency})

  png("{viz_dir}/thematic_evolution{suffix}.png", width = 4000, height = 2000, res = {self.config.analysis.viz_dpi})
  plotThematicEvolution(nexus$Nodes, nexus$Edges)
  dev.off()

  # Export evolution data
  write.csv(nexus$Nodes, "{metrics_dir}/thematic_evolution_nodes{suffix}.csv", row.names = FALSE)
  write.csv(nexus$Edges, "{metrics_dir}/thematic_evolution_edges{suffix}.csv", row.names = FALSE)
}} else {{
  cat("Not enough time periods for thematic evolution\\n")
}}

cat("Thematic evolution analysis complete\\n")
"""

        return "cat('Analysis not implemented\\n')\n"

    def _execute_r_script(self, script_path: Path) -> dict[str, Any]:
        """Execute an R script and capture results."""
        self.log.info(f"Executing R script: {script_path.name}", action="r_execute")

        try:
            result = subprocess.run(
                [self.config.analysis.r_executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout per analysis
                cwd=str(script_path.parent),
            )

            self.log.info(
                f"R script completed: {script_path.name}",
                action="r_complete",
                data={
                    "returncode": result.returncode,
                    "stdout_lines": len(result.stdout.split("\n")),
                    "stderr_lines": len(result.stderr.split("\n")),
                },
            )

            if result.returncode != 0:
                self.log.error(f"R script failed: {result.stderr[:500]}", action="r_error")
                self.console.print(f"[red]  ✗ {script_path.name} failed[/red]")
                self.console.print(f"[dim]{result.stderr[:300]}[/dim]")
                return {"status": "failed", "error": result.stderr[:500]}

            self.console.print(f"[green]  ✓ {script_path.name}[/green]")
            return {"status": "completed", "stdout": result.stdout}

        except subprocess.TimeoutExpired:
            self.log.error(f"R script timed out: {script_path.name}", action="r_timeout")
            return {"status": "timeout"}
        except Exception as e:
            self.log.error(f"R execution error: {e}", action="r_exception")
            return {"status": "error", "error": str(e)}
