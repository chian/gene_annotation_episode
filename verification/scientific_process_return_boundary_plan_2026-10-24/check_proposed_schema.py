"""Check only whether the proposed wire shape fits the unchanged form guard.

This local planning example is not a production parser, source qualifier,
projection implementation, or runtime integration test.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from gene_annotation_episode.communication import validate_closed_schema, validate_form


def obj(fields):
    return {"type": "object", "properties": fields, "required": list(fields),
            "additionalProperties": False}


original = json.loads((HERE / "current-row.json").read_text())
schema = json.loads((HERE / "current-generated-schema.json").read_text())
row_schema = schema["properties"]["chosen_name"]["items"]["properties"]
old_selection_fields = row_schema["selection"]["properties"]
row_schema["version"]["const"] = "scientific_process_result_v2"
row_schema["selection"] = obj({
    "version": {"type": "string", "const": "scientific_process_selection_report_v1"},
    "source_version": {"type": "string", "enum": ["scientific_process_selection_v2", "scientific_process_selection_v3"]},
    "evidence_axis": old_selection_fields["annotation_ref"],
    "thought_pattern": old_selection_fields["thought_ref"],
    "child_tool_info": {"type": "array", "uniqueItems": True, "items": obj({
        "name": {"type": "string", "enum": ["fixture.inspect"]},
        "resources": {"type": ["string", "null"], "enum": ["api", "local", "hpc", None]}})},
})
reported = deepcopy(original)
reported["version"] = "scientific_process_result_v2"
reported["selection"] = {
    "version": "scientific_process_selection_report_v1",
    "source_version": original["selection"]["version"],
    "evidence_axis": original["selection"]["evidence_axis"],
    "thought_pattern": original["selection"]["thought_pattern"],
    "child_tool_info": [{key: row[key] for key in ("name", "resources")}
                        for row in original["selection"]["child_tool_info"]],
}
refs = {"scientific_invocation": {reported["invocation_ref"], reported["parent_invocation_ref"]},
        "scientific_credit_binding": {reported["credit_binding_ref"]},
        "scientific_preparation": set(), "scientific_process_library": set(), "scientific_option_digest": set()}
for key in ("evidence_axis", "thought_pattern"):
    ref = reported["selection"][key]
    refs["scientific_process_library"].add(ref["library_id"])
    refs["scientific_option_digest"].add(ref["entry_sha256"])
validate_closed_schema(schema)
assert validate_form({"chosen_name": [reported]}, schema,
                     lambda ref, namespace: ref in refs.get(namespace, set())) == {"chosen_name": [reported]}
legacy = json.loads((HERE / "legacy-row.json").read_text())
legacy_schema = json.loads((HERE / "literal-legacy-form-schema.json").read_text())
legacy_refs = {"scientific_invocation": {legacy["invocation_ref"], legacy["parent_invocation_ref"]},
    "scientific_credit_binding": {legacy["credit_binding_ref"]}, "scientific_preparation": set(),
    "scientific_process_library": set(), "scientific_option_digest": set()}
for key in ("annotation_ref", "thought_ref"):
    ref = legacy["selection"][key]
    legacy_refs["scientific_process_library"].add(ref["library_id"])
    legacy_refs["scientific_option_digest"].add(ref["entry_sha256"])
assert validate_form({"chosen_name": [legacy]}, legacy_schema,
    lambda ref, namespace: ref in legacy_refs.get(namespace, set())) == {"chosen_name": [legacy]}
numerical_fields = ("initial_credit", "credit", "credit_kind", "credit_binding_ref", "completed_actions", "episode_yield")
assert all(reported[key] == original[key] for key in numerical_fields)
for name, data in (("proposed-row.json", reported), ("proposed-schema.json", schema),
                   ("proposed-schema-check.json", {"closed_guard_accepted": True,
                    "form_accepted": True, "numerical_fields_copied_exactly": list(numerical_fields),
                    "literal_legacy_compatibility_schema_accepted": True,
                    "claim": "Wire-shape feasibility only; no production repair or episode integration."})):
    (HERE / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
print("Proposed shape accepted by unchanged closed-schema/form guards; all existing numerical fields copied exactly.")
