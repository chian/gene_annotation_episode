"""Additive source-only accounting; never import application modules or run them."""
from pathlib import Path
import ast
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE_PATH = ROOT / "verification/tool_graders_shared_grader_link_count_2026-10-28_575/census.json"
HISTORY_PATH = ROOT / "verification/tool_graders_historical_count_reconciliation_2026-10-28_579/reconciliation.json"
base = json.loads(BASE_PATH.read_text())
history = json.loads(HISTORY_PATH.read_text())
source_hashes = {}


def read(relative):
    path = ROOT / relative
    raw = path.read_bytes()
    source_hashes[relative] = hashlib.sha256(raw).hexdigest()
    return raw.decode()


def py(name):
    relative = "gene_annotation_episode/" + name + ".py"
    return relative, read(relative)


def assignment(name, variable):
    _, source = py(name)
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == variable for t in node.targets):
            if isinstance(node.value, ast.Dict):
                return {ast.literal_eval(k): ast.literal_eval(v.args[0] if isinstance(v, ast.Call) else v)
                        for k, v in zip(node.value.keys, node.value.values)}
            return ast.literal_eval(node.value)
    raise AssertionError((name, variable))


def function(name, function_name):
    relative, source = py(name)
    node = next(n for n in ast.walk(ast.parse(source))
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == function_name)
    calls = sorted({ast.unparse(n.func) for n in ast.walk(node) if isinstance(n, ast.Call)})
    return {"path": relative, "line": node.lineno, "end_line": node.end_lineno,
            "function": function_name, "calls": calls, "sha256": source_hashes[relative]}


def match(name, text):
    relative, source = py(name)
    lines = [i for i, line in enumerate(source.splitlines(), 1) if text in line]
    assert lines, (name, text)
    return {"path": relative, "lines": lines, "matched_text": text, "sha256": source_hashes[relative]}


hmmer = assignment("native_hmmer_preparation_contracts", "PROGRAM_MODES")
infernal = assignment("infernal_preparation_schema", "PROGRAM_MODES")
for family, modes in (("hmmer", hmmer), ("infernal", infernal)):
    descriptions = assignment("native_" + family + "_preparation_tool_info", "_DESCRIPTIONS")
    assert set(descriptions) == set(modes)
    assert all(set(descriptions[p]) == set(ms) for p, ms in modes.items())


def names(catalog, programs):
    return sorted("native." + p + "." + m for p in programs for m in catalog[p])


def hmmer_row(key, title, sheet, programs, reader, calculator, meaning):
    row = {"key": key, "label": title, "classification": "supporting_preparation_numerical_and_validation",
           "sheet_authority": sheet, "calculator_authority": calculator, "reader_authority": reader,
           "inventory_programs": programs, "inventory_row_count": len(programs),
           "operation_names": names(hmmer, programs), "numerical_meaning": meaning,
           "evidence": [function(*reader.rsplit(".", 1)), function(*calculator.rsplit(".", 1))]}
    row["linked_name_count"] = len(row["operation_names"])
    return row


rows = [
    hmmer_row("hmmer_alignment_preparation", "HMMER alignment preparation", "hmmer_alignment_preparation_sheet_v1",
              ["alimask", "hmmbuild"], "hmmer_alignment_preparation_data.populate_hmmer_alignment_preparation_sheet",
              "hmmer_alignment_preparation_calculations.calculate_hmmer_alignment_preparation_components",
              "Alignment/model measurements, mask/map relationships and validation; no gene-function confidence."),
    hmmer_row("hmmer_artifact", "HMMER artifact preparation", "hmmer_artifact_sheet_v1",
              ["hmmconvert", "hmmfetch", "hmmpress"], "hmmer_artifact_data.populate_hmmer_artifact_sheet",
              "hmmer_artifact_calculations.calculate_hmmer_artifact_components",
              "Decoded model/key/artifact counts, probability-body differences where decoded, and custody/format checks; opaque content remains unknown."),
    hmmer_row("hmmer_emission", "HMMER generated sequences", "hmmer_emission_sheet_v1", ["hmmemit"],
              "hmmer_emission_data.populate_hmmemit_sheet", "hmmer_emission_calculations.calculate_hmmemit_components",
              "Generated sequence composition, counts, alignment quantities and consensus checks; not observed biological evidence."),
    hmmer_row("hmmer_simulation", "HMMER score simulation", "hmmer_simulation_sheet_v1", ["hmmsim"],
              "hmmer_simulation_data.populate_hmmsim_sheet", "hmmer_simulation_calculations.calculate_hmmsim_components",
              "Native and independently fitted random-score distribution quantities with their selected populations."),
    hmmer_row("hmmer_statistics", "HMMER model statistics", "hmmer_statistics_sheet_v1", ["hmmstat"],
              "hmmer_statistics_data.populate_hmmstat_sheet", "hmmer_statistics_calculations.calculate_hmmstat_components",
              "Native model statistics and explicit-parameter recalculation; missing background is unavailable."),
    hmmer_row("hmmer_fm", "HMMER FM index and literal matches", "hmmer_fm_sheet_v1", ["makehmmerdb", "hmmerfm-exactmatch"],
              "hmmer_fm_data.populate_hmmer_fm_sheet", "hmmer_fm_calculations.calculate_hmmer_fm_components",
              "Index/source populations and literal-location/count validation; raw FM intervals are distinct from validated source matches."),
]
infernal_branches = [
    {"label": "Statistics/build/calibration", "programs": ["cmbuild", "cmcalibrate", "cmstat"],
     "classification": "numerical_statistics_and_validation",
     "reader": "infernal_preparation_statistics.populate_infernal_statistics_sheet",
     "calculator_or_validator": "infernal_preparation_calculations.calculate_infernal_statistics"},
    {"label": "Generated sequences", "programs": ["cmemit"],
     "classification": "generated_data_numerical_components_and_validation",
     "reader": "infernal_preparation_emission.populate_cmemit_sheet",
     "calculator_or_validator": "infernal_preparation_emission_calculations.calculate_cmemit_components"},
    {"label": "Artifact validation", "programs": ["cmconvert", "cmfetch", "cmpress"],
     "classification": "artifact_validation_with_counts_and_bytes_not_scientific_scoring",
     "reader": "infernal_preparation_artifacts.populate_infernal_artifact_sheet",
     "calculator_or_validator": "infernal_preparation_artifacts.validate_infernal_artifact_sheet"},
]
for branch in infernal_branches:
    branch["operation_names"] = names(infernal, branch["programs"])
    branch["linked_name_count"] = len(branch["operation_names"])
    branch["evidence"] = [function(*branch[k].rsplit(".", 1)) for k in ("reader", "calculator_or_validator")]
rows.append({"key": "infernal_preparation", "label": "Infernal preparation (one shared sheet, three branches)",
    "classification": "supporting_preparation_mixed_numerical_and_artifact_validation",
    "sheet_authority": "infernal_preparation_sheet_v1", "branches": infernal_branches,
    "inventory_programs": list(infernal), "inventory_row_count": len(infernal),
    "operation_names": names(infernal, infernal), "linked_name_count": 27,
    "numerical_meaning": "18 statistics/generated-data modes plus 9 artifact-validation modes; the latter compute counts/bytes and checks, not scientific-confidence scores. Branches are not extra independent analyses."})

data_names = [assignment("api_bvbrc", "DATA_QUERY_OPERATION"), assignment("api_bvbrc", "DATA_RESULT_OPERATION")]
for key, label, sheet, reader, calculators, classification, meaning in [
    ("bvbrc_data_page", "BV-BRC Data pages/counts/facets", "bvbrc_data_sheet_v1", "bvbrc_data_readers.parse_data_snapshot",
     ["bvbrc_data_calculators.calculate_page_counts", "bvbrc_data_calculators.calculate_facet_fractions"], "supporting_acquisition_numerical_components",
     "Native/valid/invalid row counts and same-response exact-population facet fractions; counts are not evidence confidence."),
    ("bvbrc_data_feature_sequence", "BV-BRC feature-sequence joins", "bvbrc_feature_sequence_sheet_v1", "bvbrc_data_feature_sequences.extract_feature_sequence_join",
     ["bvbrc_data_calculators.calculate_feature_sequence_counts"], "supporting_acquisition_numerical_components",
     "Selected features, native sequence occurrences, distinct exact sequence identities, missing/conflicting relationships and length agreement."),
    ("bvbrc_data_molecular", "BV-BRC molecular measurements and relationships", "bvbrc_molecular_sheet_v1", "bvbrc_data_molecular.extract_molecular_experiment_rows",
     [], "typed_extraction_and_validation_without_independent_calculator",
     "Retains source numerical measurements and experiment/bioset/feature/condition/unit associations. No separate numerical scoring calculator."),
]:
    rows.append({"key": key, "label": label, "classification": classification, "sheet_authority": sheet,
        "reader_authority": reader, "calculator_authority": calculators,
        "operation_names": data_names, "linked_name_count": 2, "numerical_meaning": meaning,
        "pipeline_qualification": "query acquires/parses the selected response; result publication invokes the calculators or molecular extractor. Two named operations are pipeline links, not two independent analyses.",
        "evidence": [function(*reader.rsplit(".", 1)), *[function(*c.rsplit(".", 1)) for c in calculators]]})

support_names = set(n for row in rows for n in row["operation_names"])
historical_support = [r for r in history["rows"] if r["disposition"] != "scientific_tool_or_mode"]
assert len(historical_support) == 50
assert support_names == {n for r in historical_support for n in r["actual_operation_names"]}
assert sum(map(len, hmmer.values())) == 26
assert sum(map(len, infernal.values())) == 27
assert [b["linked_name_count"] for b in infernal_branches] == [15, 3, 9]
scientific_names = set(base["combined_main_summary"]["public_names"])
assert len(scientific_names) == 65 and scientific_names.isdisjoint(support_names)
combined_names = sorted(scientific_names | support_names)
assert len(combined_names) == 120

chains = {}
for family in ("hmmer", "infernal"):
    prefix = "native_" + family + "_preparation"
    chains[family] = [function(prefix + "_tool_info", prefix + "_tool_contracts"),
        match("execution_episodes", prefix + "_tool_contracts"),
        match("practical_execution_operations", prefix + "_program_mode_software_not_bound"),
        function(prefix + "_results", "execute"),
        function(prefix + "_result_publication", "prepare_" + prefix + "_grading"),
        function(prefix + "_result_worker", "_grade"),
        function(prefix + "_worker", "grade_" + family + "_preparation"),
        function(prefix + "_worker", "recalculate_" + family + "_preparation"),
        function(prefix + "_result_worker", "_project"),
        function(family + "_preparation_result_views", "preparation_projection_catalog")]
chains["bvbrc_data"] = [function("api_bvbrc", name) for name in ("capabilities", "result_capabilities", "prepare", "invoke", "decode", "publish")]
chains["bvbrc_data"] += [function("bvbrc_data_publication", "publish_bvbrc_data"),
    match("api_service_execution", "self.bvbrc_data.publication_inputs"), match("api_service_execution", "outcome = service.publish")]

# Check the named numerical/validation dispatch calls in source AST, not by importing code.
expected_hmmer = {
    "artifact_calculations.calculate_hmmer_artifact_components",
    "alignment_calculations.calculate_hmmer_alignment_preparation_components",
    "emission_calculations.calculate_hmmemit_components",
    "simulation_calculations.calculate_hmmsim_components",
    "statistics_calculations.calculate_hmmstat_components", "fm_calculations.calculate_hmmer_fm_components"}
assert expected_hmmer <= set(function("native_hmmer_preparation_worker", "recalculate_hmmer_preparation")["calls"])
assert {"validate_infernal_artifact_sheet", "calculate_infernal_statistics", "calculate_cmemit_components"} <= set(
    function("native_infernal_preparation_worker", "grade_infernal_preparation")["calls"])
assert {"calculate_page_counts", "calculate_facet_fractions", "calculate_feature_sequence_counts", "extract_molecular_experiment_rows"} <= set(
    function("bvbrc_data_publication", "publish_bvbrc_data")["calls"])

baseline_rows = [dict(key=r["key"], label=r.get("label", r["key"]), operation_names=r["public_tool_names"],
    linked_name_count=len(r["public_tool_names"]), evidence_source=str(BASE_PATH.relative_to(ROOT)))
    for r in [*base["source_verified_rows"], *base["parent_reported_direct_rows"]]]
assert len(baseline_rows) == 35 and sum(r["linked_name_count"] for r in baseline_rows) == 73
combined_rows = baseline_rows + rows
histogram = dict(sorted(Counter(r["linked_name_count"] for r in combined_rows).items()))
assert len(combined_rows) == 45 and sum(r["linked_name_count"] for r in combined_rows) == 132

result = {
    "record_type": "additive_supporting_sheet_operation_source_census",
    "basis": "Inherited scientific census plus fresh source inspection of all omitted supporting authorities. This is not a completion claim.",
    "historical_units_preserved": {"inventory_rows": 114, "scientific_tool_or_mode_rows": 64,
        "preparation_tool_rows": 17, "bvbrc_data_collection_and_query_ability_rows": 33},
    "scientific_baseline": base["combined_main_summary"],
    "supporting_summary": {"historical_rows": 50, "sheet_authorities": 10,
        "authorities_with_some_numerical_components": 9, "typed_only_sheet_authorities": 1,
        "hmmer_preparation_operation_names": 26, "infernal_preparation_operation_names": 27,
        "bvbrc_data_operation_names": 2, "unique_operation_names": 55, "sheet_operation_links": 59},
    "combined_summary": {"sheet_authorities": 45, "authorities_with_some_numerical_components": 44,
        "numerical_component_authorities_with_named_operations": 43,
        "typed_only_sheet_authorities": 1, "sheet_operation_links": 132,
        "links_to_authorities_with_some_numerical_components": 130,
        "typed_only_sheet_links": 2, "unique_operation_names": 120,
        "link_count_distribution": histogram, "operation_names": combined_names},
    "supporting_rows": rows, "combined_rows": combined_rows, "binding_chains": chains,
    "declared_only_aliases_or_absent_generic_result_branches_found": [],
    "qualifications": [
        "No configured runtime resource was executed or audited for installation. Preparation names are generated only for explicit supplied program/mode/software bindings; source routing rejects unbound selections.",
        "All 53 preparation mode templates have program dispatch and generic execution.results.collect/result projection paths in source. A mode label is not an extra algorithm or a fully verified deployment.",
        "The one Infernal sheet includes 15 statistics/build/calibration modes, 3 emission modes and 9 artifact-validation modes. Its validator calculates counts/bytes, but these are not scientific-confidence scores.",
        "Numerical components includes supporting counts and validation. It must not be relabeled numerically scored scientific tools.",
        "BV-BRC molecular sheet preserves native measurements and typed joins; it has no independent numerical calculator. Page/facet and feature-sequence calculations are separate from this typed sheet.",
        "BV-BRC query and result are linked pipeline operations; calculators are called during result publication, not by query launch itself.",
        "Legacy api.bvbrc.query and api.bvbrc.result use a separate raw-row path and are not extra links to the three v2 sheets. Generic execution.results.status/collect are not extra family-specific aliases.",
        "Preparation API/HPC bindings remain explicitly unfinished. Declared native formats can retain undecoded content; HMMER tool information explicitly qualifies HMMER2/binary and other subcase limitations.",
        "The 35/73/65 scientific baseline is supplied evidence, not re-audited here; its known duplicate Rfam authorities remain separately disclosed in that census.",
        "114 inventory rows, 45 shared sheet authorities, 132 links and 120 unique operation names are different units and must remain separate.",
    ],
    "verification": {"method": "Host Python standard-library AST/JSON/source/hash inspection only",
        "application_imports": False, "tests_run": False, "native_execution": False, "network_or_service_execution": False,
        "production_or_progress_mutations": False, "prior_evidence_mutations": False},
    "source_sha256": source_hashes,
    "input_evidence_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE_PATH, HISTORY_PATH)},
}
(OUT / "census.json").write_text(json.dumps(result, indent=2) + "\n")
lines = [
    "# Supporting grader/operation accounting",
    "",
    "The scientific-only census omitted 50 historical supporting rows: 17 preparation tools and 33 BV-BRC Data collection/query obligations. The historical total remains **114 inventory rows** (64 + 17 + 33).",
    "",
    "Across the supplied scientific baseline and these supporting paths there are **45 sheet authorities, 132 authority/operation links and 120 distinct operation names**. Of those authorities, **44 contain some numerical components** and one is typed extraction/validation only. Numerical supporting counts are not scientific-confidence scores. One scientific authority has no dedicated named alias, so 43 of the 44 numerically capable authorities have named links.",
    "",
    "| Authority | Historical preparation tools | Linked operation names | Meaning |",
    "|---|---:|---:|---|",
]
for row in rows:
    lines.append(f"| {row['label']} | {row.get('inventory_row_count', 'Shared 33 Data rows')} | {row['linked_name_count']} | {row['numerical_meaning']} |")
lines += ["", "Infernal's 27 links are **15 statistics/build/calibration + 3 generated-data + 9 artifact validation**. These are three branches of one sheet. The artifact branch computes counts and bytes as well as checks; it is not a scientific scoring path.",
    "", "BV-BRC Data's three sheets share the same two names, `api.bvbrc.data.query` and `api.bvbrc.data.result`. The query supplies the response; result publication applies the selected calculator/extractor. This contributes six links but only two unique names.",
    "", "| Linked names per authority | Number of authorities |", "|---:|---:|"]
lines += [f"| {links} | {count} |" for links, count in histogram.items()]
lines += ["", "The arithmetic is **65 scientific names + 26 HMMER preparation names + 27 Infernal preparation names + 2 Data names = 120**. Links are **73 + 26 + 27 + 6 = 132**; numerical-component authorities account for 130 links and the typed molecular sheet for two.",
    "", "Every supporting template has a source route into the appropriate result worker/reader/calculator or validator. Preparation exposure is conditional on explicit configured software bindings; installation, deployment, native execution and episode replay were not tested by this census. No production files, progress rows or earlier evidence were changed.",
    "", "Exact names, sheet/calculator authorities, AST binding references and source hashes are retained in `census.json`. Different modes remain different names, not new algorithms or new historical inventory rows."]
(OUT / "REPORT.md").write_text("\n".join(lines) + "\n")
print(json.dumps({"historical_rows": 114, "supporting_authorities": len(rows),
    "supporting_names": len(support_names), "combined_authorities": len(combined_rows),
    "combined_links": 132, "combined_unique_names": len(combined_names), "distribution": histogram}, indent=2))
