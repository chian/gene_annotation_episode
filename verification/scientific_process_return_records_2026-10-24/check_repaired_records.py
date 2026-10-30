"""Retain concrete pure-parser examples; no runtime, model or scientific job."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PLAN = ROOT / "verification/scientific_process_return_boundary_plan_2026-10-24"
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
sys.dont_write_bytecode = True

import pytest

from gene_annotation_episode.communication import ReportBoundaryError, validate_closed_schema, validate_form
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_reports import project_process_result, validate_process_result
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from test_scientific_process_return_records import _full_row, _libraries, _resolver, _schema


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def hashes(paths):
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


inputs = [PLAN / name for name in ("current-row.json", "proposed-row.json", "current-generated-schema.json")]
inputs += list((PLAN / "current-library").rglob("*.json"))
inputs += list((PLAN / "current-tools").rglob("*.json"))
inputs += list((ROOT / "tests/fixtures/scientific_process_returns").glob("*.json"))
before = hashes(inputs)

# This retained planning specimen was already valid construction with the
# actual published A104/P01 frozen bodies when the bound reader raised KeyError.
library = ScientificProcessLibrary(PLAN / "current-library")
tools = ScientificToolLibrary(PLAN / "current-tools")
original = json.loads((PLAN / "current-row.json").read_bytes())
for bindings in ({}, {"library": library}, {"tool_library": tools}, {"library": library, "tool_library": tools}):
    assert validate_process_result(original, **bindings) == original
reported = project_process_result(original, library=library, tool_library=tools)
assert reported == json.loads((PLAN / "proposed-row.json").read_bytes())
schema = _schema(library, tools)
assert validate_closed_schema(schema) == schema
validate_form({"arbitrary_parent_field": [reported]}, schema, _resolver(library, reported))
try:
    validate_form({"chosen_name": [original]}, json.loads((PLAN / "current-generated-schema.json").read_bytes()),
                  _resolver(library, original))
except ReportBoundaryError as error:
    historical_hybrid_error = error.diagnostic
else:
    raise AssertionError("The retained hybrid historical schema must remain invalid")
write("published-current-v1.json", original)
write("published-current-v2.json", reported)
write("published-current-v2-schema.json", schema)

with pytest.MonkeyPatch.context() as patch:
    old_library, old_tools = _libraries(HERE / "synthetic-legacy", patch, legacy=True)
    legacy = _full_row(old_library, old_tools, legacy=True)
    literal_schema = json.loads((ROOT / "tests/fixtures/scientific_process_returns/literal-legacy-form-schema.json").read_bytes())
    validate_form({"chosen_name": [legacy]}, literal_schema, _resolver(old_library, legacy))
    assert validate_process_result(legacy, library=old_library, tool_library=old_tools) == legacy
    compact_legacy = project_process_result(legacy, library=old_library, tool_library=old_tools)
    validate_form({"arbitrary_parent_field": [compact_legacy]}, _schema(old_library, old_tools),
                  _resolver(old_library, compact_legacy))
    write("synthetic-legacy-v1.json", legacy)
    write("synthetic-legacy-v2.json", compact_legacy)

with pytest.MonkeyPatch.context() as patch:
    multi_library, multi_tools = _libraries(HERE / "synthetic-current", patch)
    multi = _full_row(multi_library, multi_tools)
    compact_multi = project_process_result(multi, library=multi_library, tool_library=multi_tools)
    validate_form({"arbitrary_parent_field": [compact_multi]}, _schema(multi_library, multi_tools),
                  _resolver(multi_library, compact_multi))
    write("synthetic-multiple-tools-v1.json", multi)
    write("synthetic-multiple-tools-v2.json", compact_multi)

assert hashes(inputs) == before
write("example-input-sha256.json", before)
checks = {
    "scope": "Pure parser/projection/schema only; synthetic quantities, no scientific execution or runtime integration.",
    "retained_current_full_row_accepted_without_bindings": True,
    "retained_current_full_row_accepted_process_only": True,
    "retained_current_full_row_accepted_tool_only": True,
    "retained_current_full_row_accepted_both": True,
    "projection_equals_independent_planning_proposed_row": True,
    "current_closed_form_accepted": True,
    "literal_legacy_form_and_bound_row_accepted": True,
    "original_inputs_unchanged": True,
    "historical_hybrid_rejection_preserved": historical_hybrid_error,
    "current_selected_tools": reported["selection"]["child_tool_info"],
    "legacy_selected_tools": compact_legacy["selection"]["child_tool_info"],
    "multiple_resource_choices": compact_multi["selection"]["child_tool_info"],
    "initial_credit": compact_multi["initial_credit"], "credit": compact_multi["credit"],
    "completed_actions": compact_multi["completed_actions"], "episode_yield": compact_multi["episode_yield"],
}
write("checks.json", checks)
print(json.dumps(checks, indent=2))
