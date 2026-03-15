"""A2 · Metadata Processor

Receives bibliographic records in multiple formats (.ris, .bib, .csv, .txt),
normalizes fields, unifies into a single dataset, and deduplicates using a
three-level strategy: DOI exact → title+year+DOI (97%) → title similarity (95%).

Outputs:
- corpus.bib: unified deduplicated corpus in BibTeX format
- corpus_metadata.csv: flat CSV for inspection
- dedup_report.json: deduplication statistics
"""

import json
from pathlib import Path
from typing import Any

from biblio_review.agents.base import BaseAgent


class MetadataProcessor(BaseAgent):
    """Unify, normalize, and deduplicate bibliographic records."""

    @property
    def name(self) -> str:
        return "metadata_processor"

    @property
    def description(self) -> str:
        return "A2 · Metadata processor — Unify, normalize, and deduplicate records"

    def _validate_inputs(self, **kwargs: Any) -> bool:
        """Check that input directory contains supported files."""
        input_dir = Path(kwargs.get("input_dir", self.config.metadata.input_dir))
        if not input_dir.exists():
            self.console.print(f"[red]Input directory not found: {input_dir}[/red]")
            return False

        supported = {".ris", ".bib", ".csv", ".txt"}
        files = [f for f in input_dir.iterdir() if f.suffix.lower() in supported]
        if not files:
            self.console.print(f"[red]No supported files found in {input_dir}[/red]")
            self.console.print(f"[dim]Supported formats: {supported}[/dim]")
            return False

        self.console.print(f"Found {len(files)} input files:")
        for f in files:
            self.console.print(f"  📄 {f.name} ({f.stat().st_size / 1024:.0f} KB)")
        return True

    def _run(self, **kwargs: Any) -> dict[str, Any]:
        """Process and deduplicate bibliographic records.

        Flow:
        1. Detect and parse all input files
        2. Normalize fields (authors, journals, encoding, dates)
        3. Merge into unified dataframe
        4. Three-level deduplication
        5. Quality report
        6. Export in multiple formats
        """
        input_dir = Path(kwargs.get("input_dir", self.config.metadata.input_dir))
        output_dir = self.ensure_dir(self.config.metadata.output_dir)

        # Step 1: Parse all input files
        records = []
        source_counts = {}
        for file_path in sorted(input_dir.iterdir()):
            suffix = file_path.suffix.lower()
            if suffix not in {".ris", ".bib", ".csv", ".txt"}:
                continue

            self.log.info(f"Parsing {file_path.name}", action="parse_file")
            parsed = self._parse_file(file_path)
            source_counts[file_path.name] = len(parsed)
            records.extend(parsed)
            self.log.log_file_io(file_path, "read", record_count=len(parsed))

        total_raw = len(records)
        self.console.print(f"\n[bold]Total raw records: {total_raw}[/bold]")

        # Step 2: Normalize
        self.log.info("Normalizing fields", action="normalize")
        records = self._normalize_records(records)

        # Step 3: Deduplicate
        dedup_report = self._deduplicate(records)
        records = dedup_report["unique_records"]
        total_unique = len(records)

        # Step 4: Export
        corpus_bib = output_dir / "corpus.bib"
        corpus_csv = output_dir / "corpus_metadata.csv"
        report_file = output_dir / "dedup_report.json"

        self._export_bib(records, corpus_bib)
        self._export_csv(records, corpus_csv)

        report_data = {
            "total_raw": total_raw,
            "total_unique": total_unique,
            "duplicates_removed": total_raw - total_unique,
            "duplicate_rate": round((total_raw - total_unique) / total_raw * 100, 1),
            "source_counts": source_counts,
            "dedup_levels": dedup_report["levels"],
        }
        report_file.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

        self.console.print(f"\n[green]✓ Corpus: {total_unique} unique records[/green]")
        self.console.print(f"  Duplicates removed: {total_raw - total_unique} ({report_data['duplicate_rate']}%)")

        return {
            "output_file": str(corpus_bib),
            "csv_file": str(corpus_csv),
            "report_file": str(report_file),
            "records_in": total_raw,
            "records_out": total_unique,
            "duplicates_removed": total_raw - total_unique,
        }

    def _parse_file(self, path: Path) -> list[dict]:
        """Parse a bibliographic file into normalized records.

        Supports: .ris, .bib, .csv, .txt (WoS plain text)
        """
        suffix = path.suffix.lower()

        if suffix == ".ris":
            return self._parse_ris(path)
        elif suffix == ".bib":
            return self._parse_bib(path)
        elif suffix == ".csv":
            return self._parse_csv(path)
        elif suffix == ".txt":
            return self._parse_wos_txt(path)
        else:
            self.log.warning(f"Unsupported format: {suffix}")
            return []

    def _parse_ris(self, path: Path) -> list[dict]:
        """Parse RIS format files."""
        import rispy

        with open(path, encoding="utf-8", errors="replace") as f:
            entries = rispy.load(f)

        records = []
        for entry in entries:
            record = {
                "title": entry.get("title", entry.get("primary_title", "")),
                "authors": entry.get("authors", entry.get("first_authors", [])),
                "year": str(entry.get("year", entry.get("publication_year", ""))),
                "abstract": entry.get("abstract", entry.get("notes_abstract", "")),
                "doi": entry.get("doi", ""),
                "journal": entry.get("journal_name", entry.get("secondary_title", "")),
                "keywords": entry.get("keywords", []),
                "type": entry.get("type_of_reference", ""),
                "source_file": path.name,
                "_raw": entry,
            }
            records.append(record)
        return records

    def _parse_bib(self, path: Path) -> list[dict]:
        """Parse BibTeX format files."""
        import bibtexparser

        with open(path, encoding="utf-8", errors="replace") as f:
            parser = bibtexparser.bparser.BibTexParser(common_strings=True)
            library = bibtexparser.load(f, parser=parser)

        records = []
        for entry in library.entries:
            record = {
                "title": entry.get("title", ""),
                "authors": self._split_bib_authors(entry.get("author", "")),
                "year": entry.get("year", ""),
                "abstract": entry.get("abstract", ""),
                "doi": entry.get("doi", ""),
                "journal": entry.get("journal", ""),
                "keywords": self._split_keywords(entry.get("keywords", "")),
                "type": entry.get("ENTRYTYPE", "article"),
                "source_file": path.name,
                "bib_key": entry.get("ID", ""),
            }
            records.append(record)
        return records

    def _parse_csv(self, path: Path) -> list[dict]:
        """Parse CSV format files (typically Scopus export)."""
        import pandas as pd

        df = pd.read_csv(path, encoding="utf-8", on_bad_lines="skip")

        # Map common Scopus CSV column names
        col_map = {
            "Title": "title",
            "Author": "authors",
            "Year": "year",
            "Abstract": "abstract",
            "DOI": "doi",
            "Source title": "journal",
            "Author Keywords": "keywords",
            "Document Type": "type",
        }

        records = []
        for _, row in df.iterrows():
            record = {}
            for csv_col, field_name in col_map.items():
                val = row.get(csv_col, "")
                if pd.isna(val):
                    val = ""
                if field_name == "authors":
                    val = [a.strip() for a in str(val).split(";") if a.strip()]
                elif field_name == "keywords":
                    val = [k.strip() for k in str(val).split(";") if k.strip()]
                else:
                    val = str(val).strip()
                record[field_name] = val
            record["source_file"] = path.name
            records.append(record)
        return records

    def _parse_wos_txt(self, path: Path) -> list[dict]:
        """Parse Web of Science plain text export format."""
        # TODO: Implement WoS plain text parser
        self.log.warning(f"WoS TXT parser not yet implemented: {path.name}")
        return []

    def _normalize_records(self, records: list[dict]) -> list[dict]:
        """Normalize fields across all records."""
        import unicodedata

        for rec in records:
            # Normalize title
            title = rec.get("title", "")
            title = unicodedata.normalize("NFKD", str(title))
            rec["title"] = title.strip()
            rec["title_normalized"] = title.lower().strip()

            # Normalize DOI
            doi = str(rec.get("doi", "")).strip().lower()
            doi = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
            rec["doi"] = doi

            # Normalize year
            year = str(rec.get("year", ""))
            rec["year"] = year[:4] if len(year) >= 4 else year

            # Normalize authors
            authors = rec.get("authors", [])
            if isinstance(authors, str):
                authors = [a.strip() for a in authors.split(";") if a.strip()]
            rec["authors"] = authors
            rec["authors_normalized"] = [
                unicodedata.normalize("NFKD", a).lower().strip() for a in authors
            ]

        return records

    def _deduplicate(self, records: list[dict]) -> dict:
        """Three-level deduplication strategy."""
        from rapidfuzz import fuzz

        levels = []
        seen_ids = set()
        unique = []

        # Level 1: Exact DOI match
        doi_index: dict[str, int] = {}
        level1_dupes = 0
        for i, rec in enumerate(records):
            doi = rec.get("doi", "")
            if doi and doi in doi_index:
                level1_dupes += 1
                seen_ids.add(i)
            elif doi:
                doi_index[doi] = i

        levels.append({"method": "DOI exact match", "threshold": 1.0, "duplicates": level1_dupes})
        self.console.print(f"  Level 1 (DOI exact): {level1_dupes} duplicates")

        # Level 2: Title + Year + DOI similarity at 97%
        remaining = [(i, r) for i, r in enumerate(records) if i not in seen_ids]
        level2_dupes = 0

        title_index: dict[str, list[int]] = {}
        for idx, (i, rec) in enumerate(remaining):
            year = rec.get("year", "")
            title_norm = rec.get("title_normalized", "")
            key = f"{year}_{title_norm[:50]}"

            matched = False
            for existing_key, existing_indices in title_index.items():
                if existing_key[:5] == key[:5]:  # Same year prefix
                    for ei in existing_indices:
                        existing_rec = records[ei]
                        score = fuzz.ratio(title_norm, existing_rec.get("title_normalized", ""))
                        if score >= 97:
                            level2_dupes += 1
                            seen_ids.add(i)
                            matched = True
                            break
                if matched:
                    break

            if not matched:
                title_index.setdefault(key, []).append(i)

        levels.append({"method": "Title+Year 97% similarity", "threshold": 0.97, "duplicates": level2_dupes})
        self.console.print(f"  Level 2 (97% similarity): {level2_dupes} duplicates")

        # Level 3: Title similarity at 95%
        remaining = [(i, r) for i, r in enumerate(records) if i not in seen_ids]
        level3_dupes = 0

        clean_index: dict[str, int] = {}
        for i, rec in remaining:
            title_norm = rec.get("title_normalized", "")
            matched = False
            for existing_title, ei in clean_index.items():
                score = fuzz.ratio(title_norm, existing_title)
                if score >= 95:
                    level3_dupes += 1
                    seen_ids.add(i)
                    matched = True
                    break
            if not matched:
                clean_index[title_norm] = i

        levels.append({"method": "Title 95% similarity", "threshold": 0.95, "duplicates": level3_dupes})
        self.console.print(f"  Level 3 (95% similarity): {level3_dupes} duplicates")

        # Build unique records list
        unique = [rec for i, rec in enumerate(records) if i not in seen_ids]

        # Records between 90-95% flagged for manual review
        manual_review = []
        for i, rec in enumerate(records):
            if i in seen_ids:
                continue
            title_norm = rec.get("title_normalized", "")
            for j, rec2 in enumerate(records):
                if j <= i or j in seen_ids:
                    continue
                score = fuzz.ratio(title_norm, rec2.get("title_normalized", ""))
                if 90 <= score < 95:
                    manual_review.append({
                        "record_a": rec.get("title", "")[:80],
                        "record_b": rec2.get("title", "")[:80],
                        "similarity": score,
                    })

        if manual_review:
            self.console.print(
                f"  [yellow]⚠ {len(manual_review)} pairs between 90-95% — flagged for manual review[/yellow]"
            )

        return {
            "unique_records": unique,
            "levels": levels,
            "manual_review_pairs": manual_review[:100],  # Cap at 100 for report
        }

    def _export_bib(self, records: list[dict], path: Path) -> None:
        """Export records as BibTeX."""
        # TODO: Full BibTeX export with all metadata fields
        lines = []
        for i, rec in enumerate(records):
            key = rec.get("bib_key", f"record_{i:05d}")
            bib_type = self._map_type_to_bibtex(rec.get("type", "article"))

            lines.append(f"@{bib_type}{{{key},")
            if rec.get("title"):
                lines.append(f'  title = {{{rec["title"]}}},')
            if rec.get("authors"):
                authors_str = " and ".join(rec["authors"]) if isinstance(rec["authors"], list) else rec["authors"]
                lines.append(f"  author = {{{authors_str}}},")
            if rec.get("year"):
                lines.append(f'  year = {{{rec["year"]}}},')
            if rec.get("journal"):
                lines.append(f'  journal = {{{rec["journal"]}}},')
            if rec.get("doi"):
                lines.append(f'  doi = {{{rec["doi"]}}},')
            if rec.get("abstract"):
                lines.append(f'  abstract = {{{rec["abstract"]}}},')
            if rec.get("keywords"):
                kw = ", ".join(rec["keywords"]) if isinstance(rec["keywords"], list) else rec["keywords"]
                lines.append(f"  keywords = {{{kw}}},")
            lines.append("}\n")

        path.write_text("\n".join(lines), encoding="utf-8")
        self.log.log_file_io(path, "write", record_count=len(records))

    def _export_csv(self, records: list[dict], path: Path) -> None:
        """Export records as CSV for inspection."""
        import pandas as pd

        rows = []
        for rec in records:
            rows.append({
                "title": rec.get("title", ""),
                "authors": "; ".join(rec.get("authors", [])) if isinstance(rec.get("authors"), list) else rec.get("authors", ""),
                "year": rec.get("year", ""),
                "journal": rec.get("journal", ""),
                "doi": rec.get("doi", ""),
                "abstract": rec.get("abstract", "")[:500],  # Truncate for CSV
                "keywords": "; ".join(rec.get("keywords", [])) if isinstance(rec.get("keywords"), list) else "",
                "type": rec.get("type", ""),
                "source_file": rec.get("source_file", ""),
            })

        df = pd.DataFrame(rows)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        self.log.log_file_io(path, "write", record_count=len(rows))

    @staticmethod
    def _split_bib_authors(authors_str: str) -> list[str]:
        """Split BibTeX author string."""
        if not authors_str:
            return []
        return [a.strip() for a in authors_str.split(" and ") if a.strip()]

    @staticmethod
    def _split_keywords(kw_str: str) -> list[str]:
        """Split keyword string."""
        if not kw_str:
            return []
        for sep in [";", ","]:
            if sep in kw_str:
                return [k.strip() for k in kw_str.split(sep) if k.strip()]
        return [kw_str.strip()]

    @staticmethod
    def _map_type_to_bibtex(doc_type: str) -> str:
        """Map document type to BibTeX entry type."""
        type_map = {
            "article": "article",
            "review": "article",
            "conference paper": "inproceedings",
            "conference": "inproceedings",
            "proceedings": "inproceedings",
            "book": "book",
            "book chapter": "incollection",
        }
        return type_map.get(doc_type.lower().strip(), "article")
