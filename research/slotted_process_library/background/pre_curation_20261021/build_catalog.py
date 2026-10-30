"""Render and check the research catalog; does not alter episode/runtime code."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
FILES = (
    ("annotation_options.json", "A", "Annotation distinctions for the structured credit form"),
    ("thought_options.json", "P", "Thought patterns"),
    ("tool_options.json", "T", "Tools"),
)


def read(name):
    return json.loads((ROOT / name).read_text())


def write_json(name, value):
    (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


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


def main():
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
        assert catalog["options"], filename
        counts[prefix] = len(catalog["options"])
        ids = set()
        for option in catalog["options"]:
            ident = option["id"]
            assert re.fullmatch(prefix + r"\d{2,}", ident), ident
            assert ident not in all_ids, ident
            assert option["name"] and option["description"] and option["evidence"], ident
            required = {
                "A": ("claim_scope", "distinctions", "example_structured_values", "not_established", "follow_up_lane_ids"),
                "P": ("use_when", "live_alternatives", "decision_guidance", "outcome_contingencies", "boundary"),
                "T": ("capability_operations", "availability", "limits", "observed_uses"),
            }[prefix]
            for field in required:
                assert option.get(field), (ident, field)
            if prefix == "A":
                assert set(option["follow_up_lane_ids"]) <= {"F01", "F02", "F03", "F04", "F05"}, ident
            if prefix == "T":
                for operation in option["capability_operations"]:
                    for field in ("operation", "inputs", "outputs"):
                        assert operation.get(field), (ident, field)
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
            assert mapping["role"] in {"direct_support", "context_only", "limited_inspection"}, mapping
            assert mapping["note"], mapping
            if "option_roles" in mapping:
                assert set(mapping["option_roles"]) == set(mapping["option_ids"]), mapping
                assert set(mapping["option_roles"].values()) <= {"direct_support", "context_only", "limited_inspection"}, mapping
            if groups[mapping["case_group"]]["best_coverage"] == "abstract_or_summary":
                assert mapping["role"] == "limited_inspection", mapping
            coverage[mapping["case_group"]]["slots"][prefix] = mapping

    assemblies = read("assemblies.json")
    for item in assemblies["assemblies"]:
        for key, prefix in (("annotation", "A"), ("thought", "P"), ("tools", "T")):
            assert item[key] in all_ids and item[key].startswith(prefix), item
        assert item["case_groups"] and set(item["case_groups"]) <= set(groups), item
    for item in assemblies["incompatible_examples"]:
        for ident in item["option_ids"]:
            assert ident in all_ids, item
        assert set(item["case_groups"]) <= set(groups), item
    assembled_ids = {row[key] for row in assemblies["assemblies"] for key in ("annotation", "thought", "tools")}
    assert set(all_ids) <= assembled_ids, ("Options without an assembly illustration", set(all_ids) - assembled_ids)

    assembly_md = [
        "# Worked three-slot selections", "",
        assemblies["status"], "",
        "Each row selects exactly one annotation entry, one thought pattern and one tool context. Parent-provided evidence remains an input. Tool contexts can contain related primitive operations. These selections cover every current option at least once; this is a coverage illustration, not a compatibility/performance validation. The case records and option source table retain the actual evidence and scope.", "",
        "| Selection / case question | Annotation distinction | Thought pattern | Tools | Narrowed decision |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in assemblies["assemblies"]:
        cells = [f"**{row['id']}**: {cell(row['question'])}<br>" + ", ".join(f"`{g}`" for g in row["case_groups"])]
        for key in ("annotation", "thought", "tools"):
            ident = row[key]
            cells.append(f"[{ident}](DETAILS.md#{ident.lower()}): {cell(all_ids[ident]['name'])}")
        cells.append(cell(row["narrowed_decision"]))
        assembly_md.append("| " + " | ".join(cells) + " |")
    assembly_md += ["", "## Exact inputs, outputs and limits", ""]
    for row in assemblies["assemblies"]:
        assembly_md += [f"### {row['id']}", "", f"**Parent inputs / explicit tool dependencies:** {row['parent_inputs']}", "", f"**Tool return:** {row['tool_return']}", "", f"**Limit:** {row['limit']}", ""]
    assembly_md += [
        "## Combinations that do not answer the selected question", "",
        "A tool-data limitation, an unsuitable thought pattern and a changed scientific question are different reasons to revise a selection. The examples do not install automatic gates or an action-selection policy.", "",
        "| ID / selection | Case | Specific mismatch | Appropriate revision |",
        "| --- | --- | --- | --- |",
    ]
    for row in assemblies["incompatible_examples"]:
        assembly_md.append("| " + " | ".join([
            f"**{row['id']}**: " + " × ".join(row["option_ids"]) + f"<br>{cell(row['failure_kind'])}",
            ", ".join(f"`{g}`" for g in row["case_groups"]), cell(row["mismatch"]), cell(row["repair"]),
        ]) + " |")
    assembly_md += [
        "", "## What recombines", "",
        "C02/C03/C13/C22 hold target specificity (A02) while changing the thought pattern and evidence operations. C06/C20 retain contribution attribution (P06) while changing annotation scope and tools. C08/C12 retain native physiology (A08) while changing the resource-versus-time question. C13/C21 retain resolution of an aggregate claim (P13) while changing annotation scope and the MS-versus-RNA evidence operations. C03/C22 retain both annotation and thought selections while changing the assay-record-versus-model tool context; the available inferences and execution status change with that evidence.", "",
        "These crossings depend on explicit biological identities, conditions and available evidence. They do not establish that every A × P × T combination is meaningful. Input repair or later selection revision remains an episode decision; no fixed order follows from the examples.",
    ]
    (ROOT / "ASSEMBLIES.md").write_text("\n".join(assembly_md) + "\n")

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
        "format": "research_three_slot_options_v1", "status": "Curated library content; no runtime retrieval/dispatch binding installed.",
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
        "All 142 distinct groups are retained. The seven duplicate records stay linked within their groups. Group-level tags describe curatorial use; they do not turn case inspection into validation or assert that every attached option is directly established. Slot 1 also provides explicit per-option roles, shown below. Abstract/summary inspection remains limited. See the per-option source table for the narrower observations actually cited as support.", "",
        "| Case group / inspection | Annotation options | Thought options | Tool options | Preserved record |",
        "| --- | --- | --- | --- | --- |",
    ]
    for group, row in coverage.items():
        values = [f"`{group}`<br>{row['inspection']}"]
        for prefix in ("A", "P", "T"):
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
    (ROOT / "OPTIONS.md").write_text(f"# Three-slot options\n\n{counts['A']} annotation distinctions, {counts['P']} thought patterns and {counts['T']} tool contexts. Counts reflect the current curation, not a target size or a completeness claim.\n\n" + "\n".join(overview))

    details = ["# Full option content", "", "These are research library entries. Illustrative structured values do not replace the current credit schema. Tool contracts marked as specifications are not callable runtime APIs.", ""]
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
        "assembly_count": len(assemblies["assemblies"]),
        "incompatible_example_count": len(assemblies["incompatible_examples"]),
        "options_illustrated_in_assemblies": len(assembled_ids),
        "warnings": warnings,
        "source_aliases_to_review": source_aliases_to_review,
        "preserved_files_hash_checked": len(snapshot["files"]),
        "verification_scope": "Structural consistency of research catalog, identifiers, recorded source links, all-case mappings and composition references. No runtime episode construction, credit projection, biological replication or prospective performance test.",
    }
    write_json("validation.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
