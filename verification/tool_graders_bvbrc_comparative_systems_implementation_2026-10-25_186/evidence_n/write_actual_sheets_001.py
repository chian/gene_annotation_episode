"""Retain filled outputs from the actual N parser/builder; no service calls."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json

from gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts import canonical_sha256
from gene_annotation_episode.bvbrc_comparative_systems_native import parse_comparative_systems_document
from gene_annotation_episode.bvbrc_comparative_systems_sheet import build_comparative_systems_sheet

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parent / "candidate/tests/fixtures/bvbrc_comparative_systems_native"
files = {hashlib.sha256(path.read_bytes()).hexdigest(): path for path in (FIXTURES / "source_executed_synthetic").rglob("*") if path.is_file()}
results = []
for name, supplied in json.loads((FIXTURES / "build_inputs.json").read_text()).items():
    options = deepcopy(supplied)
    sources = options.pop("source_documents")
    natives = tuple(parse_comparative_systems_document(files[source["sha256"]].read_bytes(), document=source,
                    format_profile=source["format_profile"], producer_evidence=tuple(options["producer_evidence"])) for source in sources)
    sheet = build_comparative_systems_sheet(natives, **options)
    output = HERE / (name + "_actual.json")
    output.write_text(json.dumps(sheet, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    examples = {key: sheet[key] for key in ("family_rows", "pathway_rows", "pathway_ec_rows", "subsystem_rows", "overview_rows", "variant_rows")}
    record = {"example_id": name, "basis": "source_executed_synthetic_with_explicitly_labelled_supplied_fixture_records",
              "real_service_job": False, "file": output.name, "file_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
              "canonical_sheet_sha256": canonical_sha256(sheet), "analysis_id": sheet["analysis_id"],
              "populations": [{key: p[key] for key in ("population_id", "kind", "member_kind", "members", "raw_occurrence_count", "distinct_valid_member_count", "completeness", "qualification_codes")}
                              for p in sheet["populations"]], "filled_native_numerical_rows": examples}
    results.append(record)
    print(name, "rows", {key: len(value) for key, value in examples.items()}, "canonical", record["canonical_sheet_sha256"])
(HERE / "FILLED_ACTUAL_NUMERICAL_EXAMPLES_001.json").write_text(json.dumps({"classification": "actual_N_parser_and_builder_outputs_on_labelled_synthetic_evidence", "examples": results}, indent=2, ensure_ascii=False) + "\n")
