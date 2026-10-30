"""Synthetic boundary reproduction; no native search, acquisition or E claim."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.blast_sequence_database import (
    populate_blast_sequence_database_sheet,
    calculate_blast_sequence_database_components,
)
from gene_annotation_episode import native_blast_standard_database_calculators as standard
from gene_annotation_episode import native_blast_database_result_worker as native

ROOT = Path(__file__).resolve().parents[2]
OUT = Path.cwd()
source = ROOT / "verification/tool_graders_blast_fasta_record_public_associations_2026-10-26_339/check008/public_inputs_v2.json"
original = source.read_bytes()
arguments = json.loads(original)
# New explicitly synthetic supplied quality/function assertions for this test;
# original339 source records and archived results are never edited.
for ordinal, row in enumerate(arguments["reference_metadata"]):
    row["functions"][0]["function"] = "synthetic-same-function"
    row["assembly"] = dict(accession="synthetic-assembly-" + str(ordinal),
        completeness_fraction=(0.9, 0.6)[ordinal], contamination_fraction=None,
        contig_count=None, contig_n50=None, total_sequence_length=None,
        quality_method="synthetic-identity-counterexample", measurement_methods={})

sheet = populate_blast_sequence_database_sheet(**arguments)
components = calculate_blast_sequence_database_components(sheet)
key = deepcopy(arguments["search"]["search_key"])
item = dict(search_key=key, components=components)
collection = dict(invocation=dict(execution_program="blastp", query_kind="sequence"),
    searches=[deepcopy(arguments["search"])])
sheets = dict(collection=collection, sequence=[dict(search_key=key, sheet=sheet)])
calculations = dict(sequence=[item])
builder = standard._Builder(dict(synthetic_attempt=True), "a" * 64, sheets, calculations)
standard._sequence_rows(builder, 0, item)
quality = [row for row in builder.rows if row["family"] == "sequence_quality"]

class Recorder:
    def __init__(self):
        self.rows = []

    def add(self, family, identity, base, values, **kwargs):
        if family == "sequence_quality":
            self.rows.append(dict(family=family, identity=deepcopy(identity),
                component_base=base, values=deepcopy(values), context=deepcopy(kwargs)))

recorder = Recorder()
database = components["components"]["database_sheet"]
dbbase = "/sequence/0/components/components/database_sheet"
owners = [(None, database, dbbase)] + [(row["function"], row,
    dbbase + "/functions/" + str(i)) for i, row in enumerate(database["functions"])]
for function, owner, base in owners:
    native._sequence_taxonomy_quality(recorder, key, function, owner, base,
        database, dbbase, components["status"])

def grouped(rows, identity):
    out = {}
    for row in rows:
        out.setdefault(json.dumps(identity(row), sort_keys=True), []).append(row)
    return list(out.values())

standard_groups = grouped(quality, lambda row: row["record_key"])
native_groups = grouped(recorder.rows, lambda row: row["identity"])
assert len(quality) == len(recorder.rows) == 4
assert len(standard_groups) == len(native_groups) == 2
assert all(len(group) == 2 for group in standard_groups + native_groups)
for group in standard_groups:
    assert [next(c["value"] for c in row["measurements"] if c["name"] == "completeness_fraction")
            for row in group] == [0.9, 0.6]
for group in native_groups:
    assert [row["values"]["completeness_fraction"] for row in group] == [0.9, 0.6]

for name, value in (("synthetic_public_inputs.json", arguments), ("synthetic_public_sheet.json", sheet),
        ("synthetic_public_components.json", components), ("standard_rows.json", quality),
        ("native_quality_builder_calls.json", recorder.rows)):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
summary = dict(evidence="synthetic_supplied_quality_identity_counterexample",
    source_path=str(source.relative_to(ROOT)), source_sha256=hashlib.sha256(original).hexdigest(),
    distinct_original_record_ordinals=[row["record_locator"]["record_ordinal"] for row in arguments["reference_metadata"]],
    supplied_completeness=[0.9, 0.6], expected_quality_rows=4,
    standard_actual_rows=len(quality), standard_distinct_record_keys=len(standard_groups),
    native_actual_builder_calls=len(recorder.rows), native_distinct_identities=len(native_groups),
    collisions_include_overall_and_same_function=True,
    full_worker_or_episode_path_run=False, native_scientific_execution=False)
(OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
assert source.read_bytes() == original
print(json.dumps(summary, indent=2, sort_keys=True))
