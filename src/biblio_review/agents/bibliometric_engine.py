"""A5 · Bibliometric Engine

Orchestrates R/Bibliometrix for validated bibliometric calculations.
Loads ORIGINAL WoS/Scopus export files directly into Bibliometrix (preserving
all metadata: authors, affiliations, cited references, Keywords Plus, etc.),
filters by screening results, then runs analyses.

Strategy:
1. Generate a data-loading R script that reads raw files with convert2df()
2. Merge WoS + Scopus with mergeDbSources()
3. Filter by included titles from screening_results.csv
4. Save the prepared dataframe as .rds
5. Each analysis script loads the .rds and runs its analysis

This ensures Bibliometrix receives complete metadata (AU, C1, CR, DE, ID)
which is essential for co-citation, co-authorship, and keyword analyses.

Outputs:
- data/outputs/metrics/*.csv: all computed metrics
- data/outputs/viz/*.png: publication-ready figures
- data/outputs/r_scripts/*.R: auto-generated scripts (methodological transparency)
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

    ANALYSES = {
        "performance": "5a · Performance analysis (production, rankings, laws)",
        "co_citation": "5b · Co-citation analysis (intellectual structure)",
        "co_authorship": "5c · Co-authorship networks (social structure)",
        "keyword_cooccurrence": "5d · Keyword co-occurrence (conceptual structure)",
        "thematic_map": "5d · Thematic map (Callon strategic diagram)",
        "thematic_evolution": "5d · Thematic evolution analysis",
    }

    def _validate_inputs(self, **kwargs: Any) -> bool:
        # Check raw files exist
        raw_dir = Path(kwargs.get("raw_dir", "data/raw"))
        if not raw_dir.exists():
            self.console.print(f"[red]Raw data directory not found: {raw_dir}[/red]")
            return False

        wos_files = list(raw_dir.glob("*.txt"))
        scopus_files = list(raw_dir.glob("*.csv"))
        if not wos_files and not scopus_files:
            self.console.print("[red]No WoS (.txt) or Scopus (.csv) files in data/raw/[/red]")
            return False

        self.console.print(f"  Found {len(wos_files)} WoS files + {len(scopus_files)} Scopus files")

        # Check screening results exist
        screening_csv = Path("data/outputs/reports/screening_results.csv")
        if screening_csv.exists():
            self.console.print(f"  [green]✓ Screening results found[/green]")
        else:
            self.console.print(f"  [yellow]⚠ No screening results — will use full corpus[/yellow]")

        # Check R
        if not self._check_r_available():
            return False
        if not self._check_bibliometrix():
            return False

        return True

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        """Run bibliometric analyses.

        Flow:
        1. Generate and execute data preparation script (load + merge + filter)
        2. For each analysis: generate R script → execute → capture results
        3. If split_period: run each analysis for both sub-periods
        """
        raw_dir = Path(kwargs.get("raw_dir", "data/raw"))
        metrics_dir = self.ensure_dir("data/outputs/metrics")
        viz_dir = self.ensure_dir("data/outputs/viz")
        scripts_dir = self.ensure_dir("data/outputs/r_scripts")
        rds_dir = self.ensure_dir("data/processed")

        analyses = kwargs.get("analyses", self.config.analysis.analyses)
        split = kwargs.get("split", self.config.analysis.split_period)
        split_year = kwargs.get("split_year", self.config.analysis.split_year)

        # Step 1: Prepare data (load original files, merge, filter by screening)
        self.console.print("\n[bold]Step 1: Loading original files into Bibliometrix...[/bold]")
        prep_script = self._generate_data_prep_script(raw_dir, rds_dir)
        prep_path = scripts_dir / "00_data_preparation.R"
        prep_path.write_text(prep_script, encoding="utf-8")

        prep_result = self._execute_r_script(prep_path)
        if prep_result.get("status") != "completed":
            self.console.print("[red]Data preparation failed. Cannot proceed with analyses.[/red]")
            return {"status": "failed", "error": "Data preparation failed"}

        # Step 2: Run each analysis
        results = {}
        rds_path = rds_dir / "bibliometrix_corpus.rds"

        for analysis in analyses:
            if analysis not in self.ANALYSES:
                self.log.warning(f"Unknown analysis: {analysis}")
                continue

            self.console.print(f"\n[bold]Running {self.ANALYSES[analysis]}...[/bold]")

            # Full corpus analysis
            r_script = self._generate_analysis_script(
                analysis, rds_path, metrics_dir, viz_dir, period="full"
            )
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
                    r_script = self._generate_analysis_script(
                        analysis, rds_path, metrics_dir, viz_dir,
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

    def _generate_data_prep_script(self, raw_dir: Path, rds_dir: Path) -> str:
        """Generate R script that loads original files, merges, deduplicates, and filters."""
        wos_files = sorted(raw_dir.glob("*.txt"))
        scopus_files = sorted(raw_dir.glob("*.csv"))
        screening_csv = Path("data/outputs/reports/screening_results.csv")

        # Build file loading code
        load_sections = []

        if wos_files:
            wos_paths = ", ".join(f'"{f}"' for f in wos_files)
            load_sections.append(f"""
# Load WoS files (plain text format)
wos_files <- c({wos_paths})
M_wos <- convert2df(wos_files, dbsource = "wos", format = "plaintext")
cat(paste("WoS records loaded:", nrow(M_wos), "\\n"))
""")

        if scopus_files:
            scopus_paths = ", ".join(f'"{f}"' for f in scopus_files)
            load_sections.append(f"""
# Load Scopus files (CSV format)
scopus_files <- c({scopus_paths})
M_scopus <- convert2df(scopus_files, dbsource = "scopus", format = "csv")
cat(paste("Scopus records loaded:", nrow(M_scopus), "\\n"))
""")

        # Merge code
        if wos_files and scopus_files:
            merge_code = """
# Merge WoS and Scopus
M <- mergeDbSources(M_wos, M_scopus, remove.duplicated = TRUE)
cat(paste("Merged corpus:", nrow(M), "records\\n"))
"""
        elif wos_files:
            merge_code = "M <- M_wos\n"
        else:
            merge_code = "M <- M_scopus\n"

        # Filter by screening results
        if screening_csv.exists():
            filter_code = f"""
# Filter by screening results (included only)
screening <- read.csv("{screening_csv}", stringsAsFactors = FALSE)
included <- screening[screening$decision == "include", ]
cat(paste("Screening: ", nrow(included), "included records\\n"))

# Match by normalized title
M$TI_LOWER <- tolower(trimws(M$TI))
included$title_lower <- tolower(trimws(included$title))

M_filtered <- M[M$TI_LOWER %in% included$title_lower, ]
cat(paste("After title matching:", nrow(M_filtered), "records\\n"))

# If match rate is low, warn but proceed with full corpus
match_rate <- nrow(M_filtered) / nrow(included) * 100
cat(paste("Match rate:", round(match_rate, 1), "%\\n"))

if (match_rate < 50) {{
    cat("WARNING: Low match rate. Using full merged corpus instead.\\n")
    M_filtered <- M
}}

# Clean up temp column
M_filtered$TI_LOWER <- NULL
M <- M_filtered
"""
        else:
            filter_code = """
# No screening results available — using full corpus
cat("No screening results found. Using full merged corpus.\\n")
"""

        rds_path = rds_dir / "bibliometrix_corpus.rds"

        return f"""# Auto-generated by biblio-review v0.1.0
# Data preparation: load original files, merge, deduplicate, filter
# DO NOT EDIT — regenerate with: biblio-review analyze

library(bibliometrix)

cat("=== Data Preparation ===\\n")

{''.join(load_sections)}

{merge_code}

{filter_code}

# Save prepared corpus as RDS for analysis scripts
saveRDS(M, "{rds_path}")
cat(paste("Corpus saved:", nrow(M), "records ->", "{rds_path}", "\\n"))
cat("Data preparation complete\\n")
"""

    def _generate_analysis_script(
        self,
        analysis: str,
        rds_path: Path,
        metrics_dir: Path,
        viz_dir: Path,
        period: str = "full",
        year_range: tuple[int, int] | None = None,
    ) -> str:
        """Generate an R script for a specific analysis.

        Each script loads the prepared .rds corpus and runs one analysis.
        """
        suffix = f"_{period}" if period != "full" else ""
        filter_code = ""
        if year_range:
            filter_code = f"""
# Filter to period: {year_range[0]}-{year_range[1]}
M <- M[M$PY >= {year_range[0]} & M$PY <= {year_range[1]}, ]
cat(paste("Records after period filter:", nrow(M), "\\n"))
"""

        header = f"""# Auto-generated by biblio-review v0.1.0
# Analysis: {analysis} | Period: {period}
# DO NOT EDIT — regenerate with: biblio-review analyze

library(bibliometrix)

# Load prepared corpus
M <- readRDS("{rds_path}")
cat(paste("Corpus loaded:", nrow(M), "records\\n"))
{filter_code}
"""

        body = self._get_analysis_code(analysis, metrics_dir, viz_dir, suffix)
        return header + body

    def _get_analysis_code(self, analysis: str, metrics_dir: Path, viz_dir: Path, suffix: str) -> str:
        """Get R code for a specific analysis type."""

        if analysis == "performance":
            return f"""
# ── Performance analysis ──────────────────────────────
results <- biblioAnalysis(M, sep = ";")
S <- summary(results, k = 20, pause = FALSE)

# Annual production (computed from PY field)
annual_tab <- table(M$PY)
annual_df <- data.frame(Year = as.integer(names(annual_tab)), Articles = as.integer(annual_tab))
annual_df <- annual_df[order(annual_df$Year), ]
write.csv(annual_df, "{metrics_dir}/annual_production{suffix}.csv", row.names = FALSE)

# Most productive authors
au <- data.frame(Author = names(results$Authors), Articles = as.integer(results$Authors))
au <- au[order(-au$Articles), ]
write.csv(head(au, 50), "{metrics_dir}/top_authors{suffix}.csv", row.names = FALSE)

# Most productive sources
so <- data.frame(Source = names(results$Sources), Articles = as.integer(results$Sources))
so <- so[order(-so$Articles), ]
write.csv(head(so, 50), "{metrics_dir}/top_sources{suffix}.csv", row.names = FALSE)

# Most productive countries
co <- data.frame(Country = names(results$Countries), Articles = as.integer(results$Countries))
co <- co[order(-co$Articles), ]
write.csv(head(co, 50), "{metrics_dir}/top_countries{suffix}.csv", row.names = FALSE)

# Most cited documents
write.csv(head(results$MostCitedPapers, 50), "{metrics_dir}/most_cited{suffix}.csv", row.names = FALSE)

# Document types
dt <- data.frame(Type = names(results$Documents), Count = as.integer(results$Documents))
write.csv(dt, "{metrics_dir}/document_types{suffix}.csv", row.names = FALSE)

# Bradford's law
tryCatch({{
    bradford_results <- bradford(M)
    write.csv(bradford_results$table, "{metrics_dir}/bradford{suffix}.csv", row.names = FALSE)
}}, error = function(e) cat(paste("Bradford skipped:", e$message, "\\n")))

# Lotka's law
tryCatch({{
    lotka_results <- lotka(results)
    write.csv(data.frame(
        Authors = lotka_results$AuthorProd$N.of.Authors,
        Articles = lotka_results$AuthorProd$Freq
    ), "{metrics_dir}/lotka{suffix}.csv", row.names = FALSE)
}}, error = function(e) cat(paste("Lotka skipped:", e$message, "\\n")))

# Save annual production plot
tryCatch({{
    png("{viz_dir}/annual_production{suffix}.png", width = 2400, height = 1600, res = {self.config.analysis.viz_dpi})
    barplot(annual_df$Articles, names.arg = annual_df$Year,
            main = "Annual scientific production", xlab = "Year", ylab = "Articles",
            col = "#4472C4", border = NA)
    dev.off()
}}, error = function(e) {{ cat(paste("Plot skipped:", e$message, "\\n")); try(dev.off(), silent=TRUE) }})

cat("Performance analysis complete\\n")
"""

        elif analysis == "co_citation":
            return f"""
# ── Co-citation analysis ──────────────────────────────
tryCatch({{
    NetMatrix <- biblioNetwork(M, analysis = "co-citation", network = "references", sep = ";")
    net <- networkPlot(NetMatrix, n = 50, type = "auto", Title = "Co-Citation Network{suffix}",
                       size = TRUE, remove.multiple = TRUE, labelsize = 0.7, edgesize = 3,
                       plot = FALSE)

    # Export adjacency matrix (top 200)
    n <- min(200, nrow(NetMatrix))
    write.csv(as.matrix(NetMatrix[1:n, 1:n]), "{metrics_dir}/cocitation_matrix{suffix}.csv")

    # Save network plot
    png("{viz_dir}/cocitation_network{suffix}.png", width = 3000, height = 3000, res = {self.config.analysis.viz_dpi})
    plot(net$graph)
    dev.off()
}}, error = function(e) {{ cat(paste("Co-citation skipped:", e$message, "\\n")); try(dev.off(), silent=TRUE) }})

cat("Co-citation analysis complete\\n")
"""

        elif analysis == "co_authorship":
            return f"""
# ── Co-authorship analysis ────────────────────────────
tryCatch({{
    NetMatrix <- biblioNetwork(M, analysis = "collaboration", network = "authors", sep = ";")
    net <- networkPlot(NetMatrix, n = 50, type = "auto", Title = "Author Collaboration{suffix}",
                       size = TRUE, remove.multiple = TRUE, labelsize = 0.7, plot = FALSE)

    n <- min(100, nrow(NetMatrix))
    write.csv(as.matrix(NetMatrix[1:n, 1:n]), "{metrics_dir}/coauthorship_matrix{suffix}.csv")

    png("{viz_dir}/coauthorship_network{suffix}.png", width = 3000, height = 3000, res = {self.config.analysis.viz_dpi})
    plot(net$graph)
    dev.off()
}}, error = function(e) {{ cat(paste("Author collaboration skipped:", e$message, "\\n")); try(dev.off(), silent=TRUE) }})

# Country collaboration
tryCatch({{
    NetCountry <- biblioNetwork(M, analysis = "collaboration", network = "countries", sep = ";")
    png("{viz_dir}/country_collaboration{suffix}.png", width = 3000, height = 2000, res = {self.config.analysis.viz_dpi})
    net_co <- networkPlot(NetCountry, n = 30, type = "auto", Title = "Country Collaboration{suffix}",
                          size = TRUE, remove.multiple = TRUE, labelsize = 0.8)
    dev.off()
}}, error = function(e) {{ cat(paste("Country collaboration skipped:", e$message, "\\n")); try(dev.off(), silent=TRUE) }})

cat("Co-authorship analysis complete\\n")
"""

        elif analysis == "keyword_cooccurrence":
            return f"""
# ── Keyword co-occurrence ─────────────────────────────
tryCatch({{
    NetMatrix <- biblioNetwork(M, analysis = "co-occurrences", network = "author_keywords", sep = ";")

    n <- min(100, nrow(NetMatrix))
    write.csv(as.matrix(NetMatrix[1:n, 1:n]), "{metrics_dir}/keyword_cooccurrence{suffix}.csv")

    png("{viz_dir}/keyword_network{suffix}.png", width = 3000, height = 3000, res = {self.config.analysis.viz_dpi})
    net <- networkPlot(NetMatrix, n = 50, type = "auto", Title = "Keyword Co-occurrence{suffix}",
                       size = TRUE, remove.multiple = TRUE, labelsize = 0.7, edgesize = 3)
    dev.off()
}}, error = function(e) {{ cat(paste("Keyword co-occurrence skipped:", e$message, "\\n")); try(dev.off(), silent=TRUE) }})

cat("Keyword co-occurrence analysis complete\\n")
"""

        elif analysis == "thematic_map":
            return f"""
# ── Thematic map (Callon strategic diagram) ───────────
tryCatch({{
    Map <- thematicMap(M, field = "DE", n = 250, minfreq = {self.config.analysis.min_keyword_frequency},
                       stemming = FALSE, size = 0.5, repel = TRUE)

    write.csv(Map$words, "{metrics_dir}/thematic_clusters{suffix}.csv", row.names = FALSE)
    write.csv(Map$clusters, "{metrics_dir}/thematic_map_data{suffix}.csv", row.names = FALSE)

    png("{viz_dir}/thematic_map{suffix}.png", width = 3000, height = 2400, res = {self.config.analysis.viz_dpi})
    plot(Map$map)
    dev.off()
}}, error = function(e) {{ cat(paste("Thematic map skipped:", e$message, "\\n")); try(dev.off(), silent=TRUE) }})

cat("Thematic map analysis complete\\n")
"""

        elif analysis == "thematic_evolution":
            return f"""
# ── Thematic evolution analysis ───────────────────────
tryCatch({{
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

        write.csv(nexus$Nodes, "{metrics_dir}/thematic_evolution_nodes{suffix}.csv", row.names = FALSE)
        write.csv(nexus$Edges, "{metrics_dir}/thematic_evolution_edges{suffix}.csv", row.names = FALSE)
    }} else {{
        cat("Not enough time periods for thematic evolution\\n")
    }}
}}, error = function(e) {{ cat(paste("Thematic evolution skipped:", e$message, "\\n")); try(dev.off(), silent=TRUE) }})

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
                timeout=600,  # 10 minute timeout per script
                cwd=str(Path.cwd()),  # Run from project root
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
                error_msg = result.stderr[:500] if result.stderr else result.stdout[:500]
                self.log.error(f"R script failed: {error_msg}", action="r_error")
                self.console.print(f"[red]  ✗ {script_path.name} failed[/red]")
                self.console.print(f"[dim]{error_msg[:300]}[/dim]")
                return {"status": "failed", "error": error_msg}

            self.console.print(f"[green]  ✓ {script_path.name}[/green]")
            return {"status": "completed", "stdout": result.stdout}

        except subprocess.TimeoutExpired:
            self.log.error(f"R script timed out: {script_path.name}", action="r_timeout")
            self.console.print(f"[red]  ✗ {script_path.name} timed out (10 min)[/red]")
            return {"status": "timeout"}
        except Exception as e:
            self.log.error(f"R execution error: {e}", action="r_exception")
            return {"status": "error", "error": str(e)}
