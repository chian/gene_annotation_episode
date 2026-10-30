"""Run the real D -> N -> C boundary on explicitly synthetic retained inputs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.bvbrc_comparative_systems_data_inputs import extract_comparative_systems_data_inputs
from gene_annotation_episode.bvbrc_comparative_systems_native import parse_comparative_systems_document
from gene_annotation_episode.bvbrc_comparative_systems_sheet import build_comparative_systems_sheet
from gene_annotation_episode.bvbrc_comparative_systems_calculators import calculate_comparative_systems_components
from gene_annotation_episode.bvbrc_comparative_systems_handoff_contracts import canonical_sha256

HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parent / "candidate/tests/fixtures"
DATA = FIXTURES / "bvbrc_comparative_systems_data_inputs"
NATIVE = FIXTURES / "bvbrc_comparative_systems_native"
wrapper = json.loads((DATA / "qualified_data_wrapper.json").read_text())["value"]
selection = json.loads((DATA / "data_population_selection.json").read_text())["value"]
raw = (DATA / "SYNTHETIC_DATA_RESPONSE_001.json").read_bytes()
supplied = extract_comparative_systems_data_inputs((wrapper,),
    artifact_bytes={wrapper["raw_binding"]["bytes_key"]: raw}, selection=selection)

options = json.loads((NATIVE / "build_inputs.json").read_text())["pathway_subsystem_sheet"]
sources = options.pop("source_documents")
retained = {}
for path in (NATIVE / "source_executed_synthetic").rglob("*"):
    if path.is_file():
        content = path.read_bytes()
        retained[hashlib.sha256(content).hexdigest()] = content
documents = tuple(parse_comparative_systems_document(retained[source["sha256"]],
    document=source, format_profile=source["format_profile"],
    producer_evidence=tuple(options["producer_evidence"])) for source in sources)
options["supplied_record_sets"] = supplied
options["producer_evidence"] = tuple(options["producer_evidence"])
options["reference_memberships"] = tuple(options["reference_memberships"])
sheet = build_comparative_systems_sheet(documents, **options)
saved = json.loads((FIXTURES / "bvbrc_comparative_systems_calculators/saved_examples.json").read_text())["examples"]
parameters = deepcopy(saved["pathway_subsystem_components"]["parameters"])
parameters["requests"] = parameters["requests"][:2]
before = deepcopy(sheet)
components = calculate_comparative_systems_components(sheet, parameters=parameters)
assert sheet == before
native, later = components["components"]
assert native["value"]["value"] == 75
assert native["ratio"]["numerator"]["value"] == 3
assert native["ratio"]["denominator"]["value"] == 4
assert later["value"]["value"] == 100 * 4 / 9
assert later["ratio"]["numerator"]["value"] == 4
assert later["ratio"]["denominator"]["value"] == 9
record = supplied["record_sets"][0]
result = {
    "basis": "synthetic unit inputs and retained source-executed synthetic native outputs; no host admission or live service",
    "native_response_sha256": hashlib.sha256(raw).hexdigest(),
    "sheet_sha256": canonical_sha256(sheet),
    "native_percent": native["value"]["value"],
    "native_numerator_genome_ec_pairs": 3,
    "native_denominator_ec_genome_opportunities": 4,
    "native_genome_population_id": native["value"]["population_id"],
    "later_percent": later["value"]["value"],
    "later_numerator_genome_ec_pairs": 4,
    "later_denominator_ec_genome_opportunities": 9,
    "later_genome_population_id": later["value"]["population_id"],
    "native_query_record_count": record["original_query_record_count"],
    "raw_occurrence_count": record["population"]["raw_occurrence_count"],
    "locally_included_record_count": record["locally_included_record_count"],
    "distinct_valid_member_count": record["population"]["distinct_valid_member_count"],
    "page_coverage": record["page_coverage"],
    "snapshot_consistency": record["snapshot_consistency"],
    "population_completeness": record["population"]["completeness"],
    "relationship_to_original_task": record["population"]["relationship_to_original_task"],
}
for name, value in (("FILLED_SUPPLIED_RECORD_SETS_001.json", supplied),
                    ("FILLED_SHEET_COMPONENTS_001.json", {"sheet": sheet, "components": components}),
                    ("NUMERICAL_RESULT_001.json", result)):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({key: value for key, value in result.items() if not isinstance(value, dict)}, indent=2))
