"""Render bioinformatics process components and check preserved source records.

Only annotation and thought-pattern components have option catalogs. The third
slot receives multiple actual tools from the runtime tool-map retriever; this
generator neither proposes tool implementations nor assembles fixed episodes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
FILES = (
    ("annotation_options.json", "A", "Scientific support slot: unavailable pending review"),
    ("thought_options.json", "P", "Thought patterns"),
)


def cell(value):
    if isinstance(value, list):
        return "<br>".join(cell(x) for x in value)
    if isinstance(value, dict):
        return "<br>".join(f"{cell(k)}: {cell(v)}" for k, v in value.items())
    return str(value).replace("|", "\\|").replace("\n", " ")


def link_record(ref):
    old = Path(ref["record_path"])
    rel = Path("corpus") / old.relative_to("/tmp/episode-published-cases")
    if "line" in ref:
        return f"[{old.name}, line {ref['line']}]({rel})"
    pointer = ref.get("json_pointer", "") or "/"
    return f"[{old.name}, `{pointer}`]({rel})"


def detail(value, depth=0):
    if isinstance(value, dict):
        return "\n".join(
            f"{'  ' * depth}- **{k.replace('_', ' ')}:** "
            + ("\n" + detail(v, depth + 1) if isinstance(v, (dict, list)) else str(v))
            for k, v in value.items()
        )
    if isinstance(value, list):
        return "\n".join(
            "  " * depth + "- " + ("\n" + detail(v, depth + 1) if isinstance(v, (dict, list)) else str(v))
            for v in value
        )
    return str(value)


def source_matches(url, content):
    """Recognize recorded URLs or explicit DOI/PMCID bibliographic aliases."""
    url = unquote(url).rstrip("/").lower()
    content = unquote(content).lower()
    if url in content:
        return True
    pmc = re.search(r"pmc\d+", url)
    if pmc and pmc.group() in content:
        return True
    doi = re.search(r"10\.\d{4,9}/[^\s]+", url)
    return bool(doi and doi.group().rstrip("/") in content)


def render(ROOT):
    """Render only inside a new, unpublished working copy."""
    def read(name):
        return json.loads((ROOT / name).read_text())

    def write_json(name, value):
        (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")

    cases = read("case_records.json")
    groups = {g["case_group"]: g for g in cases}
    case_ids = {
        group: {r["index_reference"]["case_id"] for r in g["records"]}
        for group, g in groups.items()
    }
    assert len(groups) == 142
    snapshot = read("corpus_snapshot_manifest.json")
    for item in snapshot["files"]:
        path = ROOT / item["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], path
    for group in cases:
        for retained in group["records"]:
            ref = retained["index_reference"]
            local = ROOT / "corpus" / Path(ref["record_path"]).relative_to("/tmp/episode-published-cases")
            if ref.get("record_format") == "json_document":
                record = json.loads(local.read_text())
                for component in ref.get("json_pointer", "").split("/")[1:]:
                    component = component.replace("~1", "/").replace("~0", "~")
                    record = record[int(component)] if isinstance(record, list) else record[component]
            else:
                record = json.loads(local.read_text().splitlines()[ref["line"] - 1])
            assert record == retained["record"], ref
    catalogs = {prefix: read(name) for name, prefix, _ in FILES}
    assert not catalogs["A"]["options"], "First-slot content is unavailable pending scoring-axis review"
    all_ids = {}
    counts = {}
    evidence_rows = []
    coverage = {g: {"case_group": g, "inspection": record["best_coverage"], "slots": {}} for g, record in groups.items()}
    warnings = []
    source_aliases_to_review = []
    source_texts = {group: json.dumps(record, ensure_ascii=False) for group, record in groups.items()}
    for group, record in groups.items():
        for extension in record.get("trace_extensions", []):
            local = ROOT / "corpus" / Path(extension).relative_to("/tmp/episode-published-cases")
            source_texts[group] += "\n" + local.read_text()
    for filename, prefix, title in FILES:
        catalog = catalogs[prefix]
        assert isinstance(catalog["options"], list), filename
        if prefix == "P":
            assert catalog["options"], filename
        counts[prefix] = len(catalog["options"])
        ids = set()
        for option in catalog["options"]:
            ident = option["id"]
            assert re.fullmatch(prefix + r"\d{2,}", ident), ident
            assert ident not in all_ids, ident
            assert option["name"] and option["description"] and option["evidence"], ident
            required = ("use_when", "live_alternatives", "decision_guidance", "outcome_contingencies", "boundary")
            for field in required:
                assert option.get(field), (ident, field)
            all_ids[ident] = option
            ids.add(ident)
            for n, evidence in enumerate(option["evidence"], 1):
                group = evidence["case_group"]
                assert group in groups, (ident, group)
                assert evidence["case_id"] in case_ids[group], (ident, evidence["case_id"])
                for field in ("source_url", "source_locator", "observation", "limit"):
                    assert evidence.get(field), (ident, field)
                assert evidence["source_url"].startswith("https://"), (ident, evidence["source_url"])
                if not source_matches(evidence["source_url"], source_texts[group]):
                    source_aliases_to_review.append({"option_id": ident, "case_group": group, "source_url": evidence["source_url"]})
                if groups[group]["best_coverage"] == "abstract_or_summary":
                    warnings.append(f"{ident}: supporting reference {group} has only abstract/summary inspection.")
                evidence_rows.append({"evidence_id": f"E-{ident}-{n:02d}", "option_id": ident, **evidence})
        mappings = catalog.get("case_mapping", [])
        assert len(mappings) == 142, (filename, "case_mapping", len(mappings))
        assert {m["case_group"] for m in mappings} == set(groups), filename
        for mapping in mappings:
            assert set(mapping["option_ids"]) <= ids, mapping
            assert mapping["role"] in {"direct_support", "context_only", "limited_inspection", "not_assigned"}, mapping
            assert mapping["note"], mapping
            if "option_roles" in mapping:
                assert set(mapping["option_roles"]) == set(mapping["option_ids"]), mapping
                assert set(mapping["option_roles"].values()) <= {"direct_support", "context_only", "limited_inspection"}, mapping
            if (mapping["role"] != "not_assigned" and
                    groups[mapping["case_group"]]["best_coverage"] == "abstract_or_summary"):
                assert mapping["role"] == "limited_inspection", mapping
            coverage[mapping["case_group"]]["slots"][prefix] = mapping

    # These original headings are retained as background, not first-slot options.
    # Validate them against their original source rows without publishing them.
    background = read("background/biological_claim_distinctions/annotation_options.json")
    background_sources = read("background/biological_claim_distinctions/option_sources.json")
    expected_background_rows = []
    for option in background["options"]:
        path = ROOT / "background" / "biological_claim_distinctions" / "entries" / f"{option['id']}.json"
        assert json.loads(path.read_text()) == {"slot": background["slot"], **option}, path
        for n, evidence in enumerate(option["evidence"], 1):
            group = evidence["case_group"]
            assert evidence["case_id"] in case_ids[group], evidence
            assert source_matches(evidence["source_url"], source_texts[group]), evidence
            expected_background_rows.append({"evidence_id": f"E-{option['id']}-{n:02d}", "option_id": option["id"], **evidence})
    assert background_sources["rows"] == expected_background_rows
    assert not list((ROOT / "entries").glob("A*.json")), "Background headings cannot be active entries"
    assert not list((ROOT / "entries").glob("T*.json")), "Tools come from actual map retrieval"
    for removed in ("tool_options.json", "assemblies.json", "ASSEMBLIES.md"):
        assert not (ROOT / removed).exists(), removed

    (ROOT / "entries").mkdir(exist_ok=True)
    metadata = []
    for filename, prefix, title in FILES:
        for option in catalogs[prefix]["options"]:
            path = f"entries/{option['id']}.json"
            write_json(path, {"slot": catalogs[prefix]["slot"], **option})
            metadata.append({
                "id": option["id"], "slot": catalogs[prefix]["slot"],
                "name": option["name"], "description": option["description"], "detail_path": path,
                "source_evidence_ids": [f"E-{option['id']}-{n:02d}" for n in range(1, len(option["evidence"]) + 1)],
            })
    write_json("index.json", {
        "format": "research_three_slot_options_v1", "status": "First scientific support slot unavailable pending scoring-axis review; only curated thought patterns are discoverable. The third slot receives retrieved actual tools. Biological claim headings remain nonselectable background.",
        "slots": [{"slot": catalogs[prefix]["slot"], "catalog": filename, "count": counts[prefix]} for filename, prefix, _ in FILES],
        "entries": metadata,
    })

    write_json("option_sources.json", {"meaning": "Each row links an option to the particular case observation supporting its content; no row awards credit or establishes independent replication.", "rows": evidence_rows})
    write_json("case_coverage.json", {"meaning": "Curatorial relation to each slot, not a biological validation result. Direct support tags must be read with their case-specific note and original inspection scope.", "rows": list(coverage.values())})
    sources_md = [
        "# Option-to-source inspection table", "",
        "The observation column states why the case supports the option. Each link leads to a published source and a preserved case record; limits retain the original inspection and experimental scope. Additional papers and traces remain in the record. One source reused by several options remains the same evidence.", "",
        "| Evidence / option | Case and preserved record | Primary source and locator | Observation supporting this option | Inspection / inference limit |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in evidence_rows:
        group = groups[row["case_group"]]
        ref = next(r["index_reference"] for r in group["records"] if r["index_reference"]["case_id"] == row["case_id"])
        sources_md.append("| " + " | ".join([
            f"`{row['evidence_id']}` / **{row['option_id']}**",
            f"`{row['case_group']}`<br>`{row['case_id']}`<br>{link_record(ref)}",
            f"[Primary source]({row['source_url']})<br>{cell(row['source_locator'])}",
            cell(row["observation"]), cell(row["limit"]),
        ]) + " |")
    (ROOT / "OPTION_SOURCES.md").write_text("\n".join(sources_md) + "\n")

    coverage_md = [
        "# All-case coverage register", "",
        "All 142 distinct groups are retained. The seven duplicate records stay linked within their groups. The first scientific support slot has no adopted options. Thought-pattern per-option tags identify explicit evidence rows versus relevant context; a case-level tag describes the strongest relation and does not establish every associated pattern. Abstract/summary inspection remains limited. Original biological claim mappings are preserved only as nonselectable background.", "",
        "| Case group / inspection | Scientific support slot | Thought patterns | Preserved record |",
        "| --- | --- | --- | --- |",
    ]
    for group, row in coverage.items():
        values = [f"`{group}`<br>{row['inspection']}"]
        for prefix in ("A", "P"):
            m = row["slots"][prefix]
            roles = m.get("option_roles", {})
            labels = [f"{ident} ({roles[ident]})" if ident in roles else ident for ident in m["option_ids"]]
            values.append(cell(", ".join(labels) or "No option assigned") + f"<br>**Group relation: {m['role']}**: " + cell(m["note"]))
        values.append("<br>".join(link_record(r["index_reference"]) for r in groups[group]["records"]))
        coverage_md.append("| " + " | ".join(values) + " |")
    (ROOT / "CASE_COVERAGE.md").write_text("\n".join(coverage_md) + "\n")

    overview = []
    for filename, prefix, title in FILES:
        overview += [f"## {title}", "", "| ID | Option | What its selection contributes |", "| --- | --- | --- |"]
        for option in catalogs[prefix]["options"]:
            overview.append(f"| [{option['id']}](DETAILS.md#{option['id'].lower()}) | {cell(option['name'])} | {cell(option['description'])} |")
        overview += ["", f"Full entry content: [{filename}]({filename}).", ""]
    (ROOT / "OPTIONS.md").write_text(f"# Bioinformatics process components\n\nThe user specified: \"there should be 3 slots from our discussion. 1 related to annotation credit axis, 1 related to thought pattern, and 1 with the tools that the child is scoped to\". The first slot is unavailable pending review of scientific support and scoring. There are {counts['P']} curated thought patterns. The third slot receives multiple actual tools from retrieval, never a fixed bundle from this catalog. The old biological claim headings are [nonselectable background](background/biological_claim_distinctions/README.md). These counts do not establish completeness. See [CURRENT_SLOT_SOURCES.md](CURRENT_SLOT_SOURCES.md).\n\n" + "\n".join(overview))

    details = ["# Full bioinformatics component content", "", "The first scientific support slot is unavailable pending scoring-axis review. The old A claim headings are preserved only as nonselectable background; neither those headings nor existing scoring labels are accepted merely because they were written in files. P entries supply reusable thought patterns. The third slot receives multiple actual tools from retrieval, with their exact callable contracts. Published cases below provide provenance for bioinformatics reasoning; they do not define literature workflows. See [CURRENT_SLOT_SOURCES.md](CURRENT_SLOT_SOURCES.md).", ""]
    for _, prefix, title in FILES:
        details += [f"## {title}", ""]
        for option in catalogs[prefix]["options"]:
            details += [f'<a id="{option["id"].lower()}"></a>', f"### {option['id']}: {option['name']}", "", detail({k: v for k, v in option.items() if k not in {"id", "name", "evidence"}}), "", f"Source observations: " + ", ".join(f"E-{option['id']}-{n:02d}" for n in range(1, len(option['evidence']) + 1)) + " in [OPTION_SOURCES.md](OPTION_SOURCES.md).", ""]
    (ROOT / "DETAILS.md").write_text("\n".join(details))

    summary = {
        "case_groups": len(groups),
        "case_records": sum(len(g["records"]) for g in groups.values()),
        "inspection_counts": {level: sum(g["best_coverage"] == level for g in groups.values()) for level in sorted({g["best_coverage"] for g in groups.values()})},
        "option_counts": counts,
        "source_links": len(evidence_rows),
        "separately_addressable_entries": len(metadata),
        "case_slot_relations": sum(len(row["slots"]) for row in coverage.values()),
        "tool_slot_source": "multiple actual tools retrieved from the caller-provided runtime tool map; no fixed T entries or episode assemblies",
        "first_slot": "unavailable_pending_scientific_support_and_scoring_axis_review",
        "nonselectable_background_claim_headings": len(background["options"]),
        "preserved_background_source_links": len(expected_background_rows),
        "warnings": warnings,
        "source_aliases_to_review": source_aliases_to_review,
        "preserved_files_hash_checked": len(snapshot["files"]),
        "verification_scope": "Active thought-pattern content, nonselectable background provenance, identifiers, recorded source links, all-case mappings and frozen corpus integrity. No adopted first-slot options, runtime episode construction, credit projection, biological replication or prospective performance test.",
    }
    write_json("validation.json", summary)
    # Check only current curation documents, not frozen historical research
    # prose whose original raw-asset paths may point outside this repository.
    documents = ["README.md", "OPTIONS.md", "DETAILS.md", "CURRENT_SLOT_SOURCES.md",
                 "BUILD_SCOPE.md", "OPTION_SOURCES.md", "CASE_COVERAGE.md",
                 "background/biological_claim_distinctions/README.md"]
    local_links, missing_links = 0, []
    for document in documents:
        text = (ROOT / document).read_text()
        for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
            destination = match.group(1)
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", destination):
                continue
            target, _, anchor = destination.partition("#")
            path = (ROOT / document).parent / unquote(target)
            local_links += 1
            if not path.exists():
                missing_links.append({"document": document, "destination": destination})
            if anchor and path.name == "DETAILS.md":
                assert f'<a id="{anchor}"></a>' in path.read_text(), (document, anchor)
    assert not missing_links, missing_links
    inspections = {
        "format": "bioinformatics_process_component_curation_v2",
        "current_document_local_links_checked": local_links,
        "missing_current_document_local_links": missing_links,
        "active_entry_anchors_checked": len(metadata),
        "active_thought_patterns": len(catalogs["P"]["options"]),
        "first_slot": "unavailable_pending_scientific_support_and_scoring_axis_review",
        "nonselectable_background_headings": len(background["options"]),
        "source_relationship_digests": {
            "current_active_P_rows": hashlib.sha256(json.dumps(evidence_rows,
                sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
            "preserved_background_A_rows": hashlib.sha256(json.dumps(expected_background_rows,
                sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()},
        "preserved_case_records_sha256": hashlib.sha256((ROOT / "case_records.json").read_bytes()).hexdigest(),
        "preserved_corpus_snapshot_manifest_sha256": hashlib.sha256((ROOT / "corpus_snapshot_manifest.json").read_bytes()).hexdigest(),
        "preserved_background_catalog_sha256": hashlib.sha256((ROOT / "background/biological_claim_distinctions/annotation_options.json").read_bytes()).hexdigest(),
        "source_url_check": "All active and background option URLs match the preserved case record or retained trace by URL, DOI or PMCID; no fresh online-access claim.",
        "scope": "Content curation, provenance, links and frozen corpus only; no runtime episode or numerical scoring verification."}
    write_json("inspection_checks.json", inspections)
    current_files = ["index.json", "annotation_options.json", "thought_options.json",
                     "option_sources.json", "case_coverage.json", "validation.json",
                     "inspection_checks.json", "build_catalog.py", "case_records.json",
                     "corpus_snapshot_manifest.json", *documents]
    current_files += [str(path.relative_to(ROOT)) for path in sorted((ROOT / "entries").glob("*.json"))]
    current_files += [str(path.relative_to(ROOT)) for path in sorted((ROOT / "background/biological_claim_distinctions").rglob("*.json"))]
    write_json("catalog_manifest.json", {
        "format": "bioinformatics_process_component_curation_v2",
        "status": "Thought patterns curated; first scientific support slot unavailable pending review; actual-tool retrieval is separate runtime work.",
        "active_thought_patterns": counts["P"],
        "first_slot_options": counts["A"],
        "background_claim_headings": len(background["options"]),
        "active_source_links": len(evidence_rows),
        "background_source_links": len(expected_background_rows),
        "core_files": [{"path": name, "bytes": (ROOT / name).stat().st_size,
                        "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
                       for name in dict.fromkeys(current_files)],
        "limitations": [
            "No first-slot evidence/support options adopted and no numerical axes or weights changed.",
            "No fixed tool bundles, fabricated capabilities or complete episode definitions are active catalog entries.",
            "Actual tool retrieval, episode execution and configured-model science require their own connected verification.",
            "Eight abstract/summary case groups retain limited inspection; known published outcomes are retrospective reasoning support.",
            "Original case corpus, case records and historical integration verification remain unchanged."]})
    print(json.dumps(summary, indent=2))


def publish(source, destination):
    """Publish a new self-contained version without modifying prior records.

    A destination is never reused, including an incomplete publication. There is
    no automatic latest-version pointer or runtime adoption of these outputs.
    """
    source, destination = Path(source).resolve(), Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    if not source.is_dir():
        raise NotADirectoryError(source)
    destination = destination.resolve()
    if source == destination or (source in destination.parents and
                                 source / "publications" not in destination.parents):
        raise ValueError("An output inside the source must be under publications/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".catalog-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "catalog"
        shutil.copytree(source, stage, copy_function=shutil.copyfile,
                        ignore=shutil.ignore_patterns("publications", "__pycache__",
                                                     "PUBLICATION.json"))
        input_files = [{"path": str(path.relative_to(stage)),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                       for path in sorted(stage.rglob("*")) if path.is_file()]
        render(stage)
        publication = {
            "format": "bioinformatics_catalog_publication_v1",
            "source_directory": str(source),
            "inputs": input_files,
            "files": [{"path": str(path.relative_to(stage)),
                       "bytes": path.stat().st_size,
                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                      for path in sorted(stage.rglob("*")) if path.is_file()],
            "scope": "Preserved content publication; no runtime adoption or scoring change.",
        }
        (stage / "PUBLICATION.json").write_text(json.dumps(publication, indent=2) + "\n")
        # mkdir is exclusive even if another publisher races with this one.
        # The completion record is moved last; a failed publication stays distinct.
        destination.mkdir()
        for path in sorted(stage.iterdir(), key=lambda path: path.name == "PUBLICATION.json"):
            path.rename(destination / path.name)
        for path in destination.rglob("*"):
            if path.is_file():
                path.chmod(0o444)
    return destination


def main():
    parser = argparse.ArgumentParser(description="Publish a new immutable catalog version.")
    parser.add_argument("--source", type=Path, required=True,
                        help="Explicit curated source directory; never modified")
    parser.add_argument("--output", type=Path, required=True,
                        help="New directory; existing paths are refused")
    args = parser.parse_args()
    publish(args.source, args.output)


if __name__ == "__main__":
    main()
